"""Observations API (Step 7_23).

Endpoints (all under /api/v1/observations/):
  GET  inbox/                      — recipient observations, not archived, by activity
  GET  unread-count/               — {count} for the nav badge
  GET  <id>/                       — thread view; updates the read receipt
  POST /                           — create (subjects + recipients + sensitivity gate)
  POST <id>/replies/               — reply (re-checks read access)
  POST <id>/amend/                 — author/admin amendment
  POST <id>/archive/ + /unarchive/ — per-user, idempotent
  GET  recipient-candidates/?sensitivity=<tier> — people taggable at a tier
  GET  subjects/?q=                — writeable-subject search

Read access is computed by ``observation_read`` (author OR recipient OR
hierarchy-covers-subject, intersected with the org sensitivity gate). The
authoring-time recipient gate (``recipients_clearing_sensitivity``) ensures a
sensitive observation can never out-run who it is sent to.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.notes_platform.common import viewer_or_403
from bunk_logs.core import audit as audit_trail
from bunk_logs.core.models import Person
from bunk_logs.core.permissions.observation_authoring import authorable_subject_queryset
from bunk_logs.core.permissions.observation_authoring import recipients_clearing_sensitivity
from bunk_logs.core.permissions.observation_read import filter_observations_readable
from bunk_logs.core.permissions.super_admin import is_super_admin
from bunk_logs.notes.models import Observation
from bunk_logs.notes.models import ObservationArchive
from bunk_logs.notes.models import ObservationReadReceipt
from bunk_logs.notes.models import ObservationRecipient
from bunk_logs.notes.models import ObservationReply
from bunk_logs.notes.models import ObservationSubject

from .serializers import ObservationCreateSerializer
from .serializers import ObservationListSerializer
from .serializers import ObservationReplyCreateSerializer
from .serializers import ObservationReplySerializer
from .serializers import ObservationThreadSerializer

User = get_user_model()

DEFAULT_SEARCH_LIMIT = 25
MAX_SEARCH_LIMIT = 100


class ObservationsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def update_read_receipt(obs: Observation, person: Person) -> None:
    now = timezone.now()
    last_reply = obs.replies.order_by("-created_at").first()
    entry_id = str(last_reply.id) if last_reply else str(obs.id)
    ObservationReadReceipt.objects.update_or_create(
        observation=obs,
        person=person,
        defaults={"last_read_at": now, "last_read_entry_id": entry_id},
    )


def has_unread_activity(obs: Observation, person: Person, *, is_author: bool) -> bool:
    receipt = next(
        (r for r in obs.read_receipts.all() if r.person_id == person.id),
        None,
    )
    replies = list(obs.replies.all())
    if receipt is None:
        if is_author:
            return any(r.author_id != person.id for r in replies)
        return True
    latest = receipt.last_read_at
    if any(r.created_at > latest for r in replies):
        return True
    return bool(not is_author and obs.created_at > latest)


def _readable_observation(ctx, obs_id: int) -> Observation | None:
    """Load an observation in the viewer's org that they are allowed to read."""
    base = Observation.all_objects.filter(organization=ctx.organization, pk=obs_id)
    visible = filter_observations_readable(base, ctx.person, ctx.organization, None)
    return (
        visible.select_related("author")
        .prefetch_related("subject_links__subject", "recipients__person", "replies__author", "read_receipts")
        .first()
    )


class ObservationsInboxView(APIView):
    def get(self, request):
        ctx = viewer_or_403(request)
        archived_ids = set(
            ObservationArchive.objects.filter(person=ctx.person).values_list("observation_id", flat=True),
        )
        qs = (
            Observation.all_objects.filter(
                organization=ctx.organization,
                recipients__person=ctx.person,
            )
            .exclude(pk__in=archived_ids)
            .distinct()
            .select_related("author")
            .prefetch_related("subject_links__subject", "replies", "read_receipts")
            .order_by("-created_at")
        )
        paginator = ObservationsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ObservationListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class ObservationsUnreadCountView(APIView):
    def get(self, request):
        ctx = viewer_or_403(request)
        archived_ids = set(
            ObservationArchive.objects.filter(person=ctx.person).values_list("observation_id", flat=True),
        )
        relevant = (
            Observation.all_objects.filter(organization=ctx.organization)
            .filter(Q(recipients__person=ctx.person) | Q(author=ctx.person))
            .exclude(pk__in=archived_ids)
            .distinct()
            .prefetch_related("replies", "read_receipts")
        )
        count = sum(
            1
            for obs in relevant
            if has_unread_activity(obs, ctx.person, is_author=obs.author_id == ctx.person.id)
        )
        return Response({"count": count})


class ObservationThreadView(APIView):
    def get(self, request, observation_id: int):
        ctx = viewer_or_403(request)
        obs = _readable_observation(ctx, observation_id)
        if obs is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        update_read_receipt(obs, ctx.person)
        return Response(ObservationThreadSerializer(obs, context={"request": request}).data)


class ObservationCreateView(APIView):
    def post(self, request):
        ctx = viewer_or_403(request)
        serializer = ObservationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data

        sensitivity = data["sensitivity"]

        # Validate subjects against the viewer's authoring scope.
        authorable_ids = set(
            authorable_subject_queryset(ctx.person, ctx.organization).values_list("id", flat=True),
        )
        subject_ids = list(dict.fromkeys(data["subject_ids"]))
        bad_subjects = [sid for sid in subject_ids if sid not in authorable_ids]
        if bad_subjects:
            return Response(
                {"subject_ids": f"Not allowed to write observations about: {bad_subjects}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate recipients against the sensitivity gate.
        recipient_ids = list(dict.fromkeys(data.get("recipient_ids") or []))
        if recipient_ids:
            cleared_ids = set(
                recipients_clearing_sensitivity(
                    ctx.person, ctx.organization, sensitivity,
                ).values_list("id", flat=True),
            )
            under_cleared = [rid for rid in recipient_ids if rid not in cleared_ids]
            if under_cleared:
                return Response(
                    {"recipient_ids": f"Recipients do not clear sensitivity '{sensitivity}': {under_cleared}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        obs = Observation.objects.create(
            organization=ctx.organization,
            program=ctx.program,
            author=ctx.person,
            author_role_at_write=ctx.membership.role,
            body=data["body"],
            context=data.get("context", ""),
            sensitivity=sensitivity,
            subject_visible=data.get("subject_visible", False),
            language=ctx.person.preferred_language or "en",
            source_content_type=data.get("source_content_type", ""),
            source_object_id=data.get("source_object_id", ""),
        )
        for sid in subject_ids:
            ObservationSubject.objects.create(observation=obs, subject_id=sid)
        for rid in recipient_ids:
            ObservationRecipient.objects.create(
                observation=obs, person_id=rid, option_key="specific_person",
            )

        audit_trail.created(actor=ctx.membership, content=obs, content_type="observation")

        obs = (
            Observation.all_objects.select_related("author")
            .prefetch_related("subject_links__subject", "recipients__person", "replies__author", "read_receipts")
            .get(pk=obs.pk)
        )
        return Response(
            ObservationThreadSerializer(obs, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ObservationReplyCreateView(APIView):
    def post(self, request, observation_id: int):
        ctx = viewer_or_403(request)
        obs = _readable_observation(ctx, observation_id)
        if obs is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ObservationReplyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        reply = ObservationReply.objects.create(
            observation=obs,
            author=ctx.person,
            author_role_at_write=ctx.membership.role,
            body=serializer.validated_data["body"],
        )
        audit_trail.created(
            actor=ctx.membership,
            content=obs,
            content_type="observation_reply",
            metadata={"reply_id": reply.id},
        )
        update_read_receipt(obs, ctx.person)
        return Response(ObservationReplySerializer(reply).data, status=status.HTTP_201_CREATED)


class ObservationAmendView(APIView):
    """Author or admin/program_lead amends an observation (creates a new linked row)."""

    def post(self, request, observation_id: int):
        ctx = viewer_or_403(request)
        original = Observation.all_objects.filter(
            organization=ctx.organization, pk=observation_id,
        ).first()
        if original is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        is_author = original.author_id == ctx.person.id
        if not (is_author or ctx.membership.capability in ("admin", "program_lead") or is_super_admin(request.user)):
            return Response(
                {"detail": "Only the author or an admin may amend an observation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ObservationReplyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amendment = Observation.objects.create(
            organization=original.organization,
            program=original.program,
            author=ctx.person,
            author_role_at_write=ctx.membership.role,
            body=serializer.validated_data["body"],
            context=original.context,
            sensitivity=original.sensitivity,
            subject_visible=original.subject_visible,
            language=ctx.person.preferred_language or "en",
            amendment_of=original,
        )
        for link in original.subject_links.all():
            ObservationSubject.objects.create(observation=amendment, subject_id=link.subject_id)
        for r in original.recipients.all():
            ObservationRecipient.objects.create(
                observation=amendment, person_id=r.person_id, option_key=r.option_key,
            )
        audit_trail.created(
            actor=ctx.membership,
            content=amendment,
            content_type="observation",
            metadata={"amendment_of": original.id},
        )
        amendment = (
            Observation.all_objects.select_related("author")
            .prefetch_related("subject_links__subject", "recipients__person", "replies__author", "read_receipts")
            .get(pk=amendment.pk)
        )
        return Response(
            ObservationThreadSerializer(amendment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ObservationArchiveView(APIView):
    def post(self, request, observation_id: int):
        ctx = viewer_or_403(request)
        obs = _readable_observation(ctx, observation_id)
        if obs is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        ObservationArchive.objects.get_or_create(observation=obs, person=ctx.person)
        audit_trail.state_changed(
            actor=ctx.membership,
            content=obs,
            before_state="active",
            after_state="archived",
            content_type="observation",
        )
        return Response({"archived": True})


class ObservationUnarchiveView(APIView):
    def post(self, request, observation_id: int):
        ctx = viewer_or_403(request)
        # Allow unarchive even though the row is archived: load via read filter
        # against the org-scoped queryset (archive does not affect read access).
        obs = _readable_observation(ctx, observation_id)
        if obs is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        ObservationArchive.objects.filter(observation=obs, person=ctx.person).delete()
        audit_trail.state_changed(
            actor=ctx.membership,
            content=obs,
            before_state="archived",
            after_state="active",
            content_type="observation",
        )
        return Response({"archived": False})


class ObservationRecipientCandidatesView(APIView):
    """GET recipient-candidates/?sensitivity=<tier> — people taggable at that tier."""

    def get(self, request):
        ctx = viewer_or_403(request)
        sensitivity = request.query_params.get("sensitivity") or Observation.Sensitivity.NORMAL
        if sensitivity not in Observation.Sensitivity.values:
            return Response(
                {"sensitivity": f"Unknown sensitivity '{sensitivity}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = recipients_clearing_sensitivity(ctx.person, ctx.organization, sensitivity).order_by(
            "last_name", "first_name",
        )
        persons = [{"id": p.id, "full_name": p.full_name} for p in qs[:500]]
        return Response({"persons": persons, "sensitivity": sensitivity})


class ObservationSubjectsView(APIView):
    """GET subjects/?q= — Persons the viewer may write observations about."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)
        q = (request.query_params.get("q") or "").strip()
        try:
            limit = int(request.query_params.get("limit", DEFAULT_SEARCH_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_SEARCH_LIMIT
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))

        viewer_person = Person.all_objects.filter(user=request.user).first()
        if is_super_admin(request.user):
            base = Person.all_objects.filter(organization=org)
        elif viewer_person is None:
            base = Person.all_objects.none()
        else:
            base = authorable_subject_queryset(viewer_person, org)
        if q:
            base = base.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(preferred_name__icontains=q),
            )
        persons = list(base.order_by("last_name", "first_name")[:limit])
        return Response({"subjects": [{"id": p.id, "full_name": p.full_name} for p in persons]})

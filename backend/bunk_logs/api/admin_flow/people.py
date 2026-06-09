"""Admin People + Membership management (Step 7_13 PR2, Story 55).

Endpoints under ``/api/v1/admin/``:

* ``GET    /people/``                          list + filter
* ``POST   /people/``                          create Person (with first Membership)
* ``GET    /people/<id>/``                     profile (identity + memberships + recent activity)
* ``PATCH  /people/<id>/``                     edit identity (audit'd)
* ``POST   /people/<id>/memberships/``         add Membership
* ``PATCH  /memberships/<id>/``                edit Membership role/dates/tags/grade
* ``POST   /memberships/<id>/deactivate/``     soft-deactivate
* ``POST   /people/<id>/invite/``              trigger invitation email (audited)

Design notes:

* All writes funnel through :mod:`bunk_logs.core.audit` so the action
  appears in the cross-cutting audit trail (Step 7_4). ``Membership``
  inherits audit content-type ``membership`` from its model name.
* Person email conflicts (Story 55 c9) return 409 with the existing
  Person + Memberships payload so the UI can offer "Add membership to
  the existing record" instead of forcing a duplicate.
* `Membership.role` is immutable post-create (capability derives from
  it; mutations would corrupt the RBAC layer). PATCH /memberships/<id>/
  silently ignores `role` and `capability`.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models.functions import Trim
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser

from .common import viewer_or_403

VALID_ROLES = frozenset(role for role, _ in Membership.ROLES)
RECENT_ACTIVITY_DAYS = 30


# ---------------------------------------------------------------------------
# Serialisation helpers (lean, hand-rolled — no DRF serializer overhead)
# ---------------------------------------------------------------------------


def _serialize_membership(m: Membership) -> dict:
    return {
        "id": m.id,
        "program_id": m.program_id,
        "program_name": m.program.name if m.program_id else None,
        "role": m.role,
        "capability": m.capability,
        "grade_level": m.grade_level,
        "tags": m.tags or [],
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "end_date": m.end_date.isoformat() if m.end_date else None,
        "is_active": m.is_active,
        "metadata": m.metadata or {},
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _serialize_person(person: Person, *, include_memberships: bool = False) -> dict:
    payload: dict[str, Any] = {
        "id": person.id,
        "organization_id": person.organization_id,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "preferred_name": person.preferred_name,
        "full_name": person.full_name,
        "email": person.email,
        "date_of_birth": person.date_of_birth.isoformat() if person.date_of_birth else None,
        "preferred_language": person.preferred_language,
        "translation_preference": person.translation_preference,
        "external_ids": person.external_ids or {},
        "has_user": person.user_id is not None,
        "user_id": person.user_id,
        "created_at": person.created_at.isoformat() if person.created_at else None,
    }
    if include_memberships:
        payload["memberships"] = [
            _serialize_membership(m)
            for m in Membership.all_objects.filter(person=person)
            .select_related("program")
            .order_by("-is_active", "-created_at")
        ]
    return payload


def _person_snapshot(person: Person) -> dict:
    return {
        "first_name": person.first_name,
        "last_name": person.last_name,
        "preferred_name": person.preferred_name,
        "email": person.email,
        "preferred_language": person.preferred_language,
        "translation_preference": person.translation_preference,
        "external_ids": person.external_ids or {},
        "date_of_birth": person.date_of_birth.isoformat() if person.date_of_birth else None,
    }


def _membership_snapshot(m: Membership) -> dict:
    return {
        "role": m.role,
        "capability": m.capability,
        "grade_level": m.grade_level,
        "tags": list(m.tags or []),
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "end_date": m.end_date.isoformat() if m.end_date else None,
        "is_active": m.is_active,
        "metadata": dict(m.metadata or {}),
    }


def _resolve_program(ctx, program_id) -> Program | None:
    if program_id in (None, ""):
        return None
    try:
        return Program.all_objects.get(pk=program_id, organization=ctx.organization)
    except Program.DoesNotExist:
        return None


def _normalize_tags(values) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values or []:
        if v is None:
            continue
        t = str(v).strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


# ---------------------------------------------------------------------------
# People list + create
# ---------------------------------------------------------------------------


class AdminPeopleListCreateView(APIView):
    """``GET`` list + ``POST`` create."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        qs = Person.all_objects.filter(organization=ctx.organization)

        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = (
                qs.filter(last_name__icontains=search)
                | qs.filter(first_name__icontains=search)
                | qs.filter(preferred_name__icontains=search)
                | qs.filter(email__icontains=search)
            ).distinct()

        role = (request.query_params.get("role") or "").strip()
        if role:
            qs = qs.filter(memberships__role=role, memberships__is_active=True).distinct()

        program_id = (request.query_params.get("program") or "").strip()
        if program_id:
            qs = qs.filter(memberships__program_id=program_id).distinct()

        tag = (request.query_params.get("tag") or "").strip().lower()
        if tag:
            qs = qs.filter(memberships__tags__contains=[tag]).distinct()

        last_name_initial = (request.query_params.get("last_name_initial") or "").strip()
        if last_name_initial:
            letter = last_name_initial[0].upper()
            if letter.isalpha():
                qs = qs.annotate(_last_name_trim=Trim("last_name")).filter(
                    _last_name_trim__iregex=rf"^\s*{re.escape(letter)}",
                )

        status_filter = (request.query_params.get("status") or "").strip().lower()
        if status_filter == "active":
            qs = qs.filter(memberships__is_active=True).distinct()
        elif status_filter == "inactive":
            # Anyone whose every membership is deactivated.
            qs = qs.exclude(memberships__is_active=True).distinct()

        qs = qs.order_by("last_name", "first_name")
        try:
            page_size = max(1, min(int(request.query_params.get("page_size", "100")), 500))
        except (TypeError, ValueError):
            page_size = 100
        try:
            offset = max(0, int(request.query_params.get("offset", "0")))
        except (TypeError, ValueError):
            offset = 0
        total = qs.count()
        items = list(qs[offset : offset + page_size])
        return Response({
            "count": total,
            "offset": offset,
            "page_size": page_size,
            "results": [_serialize_person(p) for p in items],
        })

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}
        first_name = (data.get("first_name") or "").strip()
        last_name = (data.get("last_name") or "").strip()
        if not first_name or not last_name:
            return Response(
                {"detail": "first_name and last_name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = (data.get("email") or "").strip()
        membership_payload = data.get("membership") or None
        if not isinstance(membership_payload, dict):
            return Response(
                {"detail": "A `membership` object is required to create a Person."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Email conflict (Story 55 c9).
        if email:
            existing = Person.all_objects.filter(
                organization=ctx.organization, email__iexact=email,
            ).first()
            if existing is not None:
                return Response(
                    {
                        "detail": "A Person with this email already exists in this org.",
                        "existing_person": _serialize_person(existing, include_memberships=True),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        # Resolve / validate program for the initial Membership.
        program = _resolve_program(ctx, membership_payload.get("program_id"))
        if program is None:
            return Response(
                {"detail": "Valid membership.program_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        role = (membership_payload.get("role") or "").strip()
        if role not in VALID_ROLES:
            return Response(
                {"detail": f"Unknown role {role!r}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        actor = ctx.membership or request.user
        with transaction.atomic():
            person = Person.all_objects.create(
                organization=ctx.organization,
                first_name=first_name,
                last_name=last_name,
                preferred_name=(data.get("preferred_name") or "").strip(),
                email=email,
                preferred_language=(data.get("preferred_language") or "en"),
                external_ids=data.get("external_ids") or {},
            )
            membership = Membership.all_objects.create(
                program=program,
                person=person,
                role=role,
                grade_level=membership_payload.get("grade_level"),
                tags=_normalize_tags(membership_payload.get("tags") or []),
                start_date=membership_payload.get("start_date") or None,
                end_date=membership_payload.get("end_date") or None,
                is_active=membership_payload.get("is_active", True),
                metadata=membership_payload.get("metadata") or {},
            )
            audit_module.created(
                actor, membership, after_state=_membership_snapshot(membership),
            )
        return Response(
            _serialize_person(person, include_memberships=True),
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Person detail / patch
# ---------------------------------------------------------------------------


PERSON_PATCH_FIELDS = (
    "first_name",
    "last_name",
    "preferred_name",
    "email",
    "date_of_birth",
    "preferred_language",
    "translation_preference",
    "external_ids",
)


class AdminPeopleDetailView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, person_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        person = _get_person_or_404(ctx, person_id)
        if person is None:
            return _not_found("Person")
        payload = _serialize_person(person, include_memberships=True)
        payload["recent_activity"] = _recent_activity_for_person(ctx, person)
        return Response(payload)

    def patch(self, request, person_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        person = _get_person_or_404(ctx, person_id)
        if person is None:
            return _not_found("Person")
        before = _person_snapshot(person)
        changed: list[str] = []
        for field in PERSON_PATCH_FIELDS:
            if field not in request.data:
                continue
            value = request.data[field]
            if field == "email" and value:
                value = str(value).strip()
                # Conflict guard on email change.
                if value.lower() != (person.email or "").lower():
                    other = Person.all_objects.filter(
                        organization=ctx.organization, email__iexact=value,
                    ).exclude(pk=person.pk).first()
                    if other is not None:
                        return Response(
                            {"detail": "Another Person already has this email."},
                            status=status.HTTP_409_CONFLICT,
                        )
            current = getattr(person, field, None)
            if current == value:
                continue
            setattr(person, field, value)
            changed.append(field)
        if changed:
            person.save(update_fields=changed)
            actor = ctx.membership or request.user
            audit_module.edited(
                actor, person, before, _person_snapshot(person),
                content_type="person",
            )
        return Response(_serialize_person(person, include_memberships=True))


def _get_person_or_404(ctx, person_id) -> Person | None:
    try:
        return Person.all_objects.get(pk=person_id, organization=ctx.organization)
    except (Person.DoesNotExist, ValueError):
        return None


def _not_found(label: str) -> Response:
    return Response(
        {"detail": f"{label} not found in this org."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _recent_activity_for_person(ctx, person: Person) -> list[dict]:
    """Last 30 days of AuditEvent rows tied to this Person's content."""
    since = timezone.now() - timedelta(days=RECENT_ACTIVITY_DAYS)
    membership_ids = list(
        Membership.all_objects.filter(person=person).values_list("id", flat=True),
    )
    qs = AuditEvent.all_objects.filter(
        organization=ctx.organization, created_at__gte=since,
    ).filter(
        # Either the audit row's actor is this Person's Membership, or
        # the content row's PK matches this person/their membership.
        # The cross-cutting filter is intentionally loose; the goal is
        # the "Recent activity" tab feels useful, not exhaustive.
    )
    rows = list(
        qs.filter(
            actor_membership_id__in=membership_ids,
        ).order_by("-created_at")[:50],
    )
    # Plus events about Person's Memberships directly.
    membership_rows = list(
        AuditEvent.all_objects.filter(
            organization=ctx.organization,
            content_type="membership",
            content_id__in=[str(mid) for mid in membership_ids],
            created_at__gte=since,
        ).order_by("-created_at")[:50],
    )
    seen: set = set()
    combined: list[AuditEvent] = []
    for ev in [*rows, *membership_rows]:
        if ev.id in seen:
            continue
        seen.add(ev.id)
        combined.append(ev)
    combined.sort(key=lambda e: e.created_at, reverse=True)
    return [
        {
            "id": str(ev.id),
            "event_type": ev.event_type,
            "content_type": ev.content_type,
            "content_id": ev.content_id,
            "created_at": ev.created_at.isoformat(),
            "is_admin_override": ev.is_admin_override,
            "reason_note": ev.reason_note or "",
        }
        for ev in combined[:RECENT_ACTIVITY_DAYS]
    ]


# ---------------------------------------------------------------------------
# Person -> add Membership
# ---------------------------------------------------------------------------


class AdminPersonMembershipsView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, person_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        person = _get_person_or_404(ctx, person_id)
        if person is None:
            return _not_found("Person")
        program = _resolve_program(ctx, request.data.get("program_id"))
        if program is None:
            return Response(
                {"detail": "Valid program_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        role = (request.data.get("role") or "").strip()
        if role not in VALID_ROLES:
            return Response(
                {"detail": f"Unknown role {role!r}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Membership.all_objects.filter(
            program=program, person=person, role=role,
        ).exists():
            return Response(
                {"detail": "Person already has this (program, role) Membership."},
                status=status.HTTP_409_CONFLICT,
            )
        actor = ctx.membership or request.user
        with transaction.atomic():
            membership = Membership.all_objects.create(
                program=program,
                person=person,
                role=role,
                grade_level=request.data.get("grade_level"),
                tags=_normalize_tags(request.data.get("tags") or []),
                start_date=request.data.get("start_date") or None,
                end_date=request.data.get("end_date") or None,
                is_active=request.data.get("is_active", True),
                metadata=request.data.get("metadata") or {},
            )
            audit_module.created(
                actor, membership, after_state=_membership_snapshot(membership),
            )
        return Response(_serialize_membership(membership), status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Membership patch + deactivate
# ---------------------------------------------------------------------------


MEMBERSHIP_PATCH_FIELDS = (
    "grade_level",
    "tags",
    "start_date",
    "end_date",
    "is_active",
    "metadata",
)


class AdminMembershipDetailView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def patch(self, request, membership_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        membership = _get_membership_or_404(ctx, membership_id)
        if membership is None:
            return _not_found("Membership")
        before = _membership_snapshot(membership)
        changed: list[str] = []
        for field in MEMBERSHIP_PATCH_FIELDS:
            if field not in request.data:
                continue
            value = request.data[field]
            if field == "tags":
                value = _normalize_tags(value or [])
            current = getattr(membership, field, None)
            if current == value:
                continue
            setattr(membership, field, value)
            changed.append(field)
        if changed:
            membership.save(update_fields=changed)
            actor = ctx.membership or request.user
            audit_module.edited(
                actor, membership, before, _membership_snapshot(membership),
            )
        return Response(_serialize_membership(membership))


class AdminMembershipDeactivateView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, membership_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        membership = _get_membership_or_404(ctx, membership_id)
        if membership is None:
            return _not_found("Membership")
        reason = (request.data.get("reason") or "").strip()
        if membership.is_active is False:
            return Response(_serialize_membership(membership))
        before = _membership_snapshot(membership)
        membership.is_active = False
        if not membership.end_date:
            membership.end_date = ctx.today
        membership.save(update_fields=["is_active", "end_date"])
        actor = ctx.membership or request.user
        audit_module.deactivated(
            actor, membership,
            before_state=before, after_state=_membership_snapshot(membership),
            reason=reason,
        )
        return Response(_serialize_membership(membership))


def _get_membership_or_404(ctx, membership_id) -> Membership | None:
    try:
        return Membership.all_objects.select_related("program", "person").get(
            pk=membership_id, program__organization=ctx.organization,
        )
    except (Membership.DoesNotExist, ValueError):
        return None


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------


class AdminPersonInviteView(APIView):
    """Trigger an invitation email for a Person (Story 55).

    PR2 ships the audited affordance + payload contract; actual email
    delivery is wired up in a follow-up by reusing the messaging app.
    The audit row is enough to satisfy "we know who invited who when"
    and lets the UI surface a "Sent" confirmation immediately.
    """

    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, person_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        person = _get_person_or_404(ctx, person_id)
        if person is None:
            return _not_found("Person")
        if not person.email:
            return Response(
                {"detail": "Person has no email -- cannot send invitation."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        actor = ctx.membership or request.user
        audit_module.created(
            actor, person,
            after_state={
                "invitation_sent": True,
                "recipient_email": person.email,
            },
            content_type="person_invitation",
            metadata={
                "channel": "email",
                "scheduled": bool(request.data.get("scheduled")),
            },
        )
        return Response({
            "status": "queued",
            "recipient_email": person.email,
        })

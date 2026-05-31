"""Notes platform API views (Step 7_19, Stories 66-70).

Endpoints:
  GET  /api/v1/notes/inbox/             — Story 67
  GET  /api/v1/notes/sent/              — Story 67
  GET  /api/v1/notes/archive/           — Story 67
  GET  /api/v1/notes/unread-count/      — Story 67 c10 / sidebar badge
  GET  /api/v1/notes/audience-options/  — Story 66 c2
  GET  /api/v1/notes/audience-candidates/ — composer autocomplete
  GET  /api/v1/notes/<id>/              — Story 68 thread view
  POST /api/v1/notes/                   — Story 66 compose
  POST /api/v1/notes/<id>/replies/      — Story 68 reply
  POST /api/v1/notes/<id>/archive/      — Story 67 c7
  POST /api/v1/notes/<id>/unarchive/    — Story 67 c7
  POST /api/v1/notes/from-bunk-concern/ — Story 69 draft prep
  POST /api/v1/notes/from-specialist-note/ — Story 70 draft prep
"""

from __future__ import annotations

from django.db.models import Max
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_trail
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.notes.audience import audience_options_for
from bunk_logs.notes.audience import resolve_audience
from bunk_logs.notes.models import Note
from bunk_logs.notes.models import NoteArchive
from bunk_logs.notes.models import NoteAudienceCapture
from bunk_logs.notes.models import NoteReadReceipt
from bunk_logs.notes.models import NoteReply

from .common import viewer_or_403
from .serializers import AudienceOptionSerializer
from .serializers import NoteCreateSerializer
from .serializers import NoteListSerializer
from .serializers import NoteReplyCreateSerializer
from .serializers import NoteThreadSerializer


class NotesPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _notes_last_activity(qs):
    """Annotate queryset with last_activity for sorting."""
    return qs.annotate(
        last_activity=Max("replies__created_at"),
    )


def _active_note_for(viewer, note_id: int) -> Note | None:
    """Fetch a note visible to the viewer (in audience or authored)."""
    person = viewer.person
    try:
        note = Note.all_objects.filter(
            organization=viewer.organization,
        ).get(pk=note_id)
    except Note.DoesNotExist:
        return None
    # Must be author or in captured audience
    is_author = note.author_id == person.id
    is_audience = note.audience_captures.filter(person=person).exists()
    if not is_author and not is_audience:
        return None
    return note


def _update_read_receipt(note: Note, person: Person) -> None:
    """Upsert a NoteReadReceipt after a person opens a thread."""
    now = timezone.now()
    last_reply = note.replies.order_by("-created_at").first()
    entry_id = str(last_reply.id) if last_reply else str(note.id)
    NoteReadReceipt.objects.update_or_create(
        note=note,
        person=person,
        defaults={"last_read_at": now, "last_read_entry_id": entry_id},
    )


class NotesInboxView(APIView):
    def get(self, request):
        ctx = viewer_or_403(request)
        archived_note_ids = set(
            NoteArchive.objects.filter(person=ctx.person).values_list("note_id", flat=True),
        )
        qs = (
            Note.all_objects.filter(
                organization=ctx.organization,
                audience_captures__person=ctx.person,
            )
            .exclude(pk__in=archived_note_ids)
            .distinct()
            .prefetch_related("audience_captures__person", "replies", "read_receipts")
            .select_related("author")
            .order_by("-created_at")
        )
        paginator = NotesPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = NoteListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class NotesSentView(APIView):
    def get(self, request):
        ctx = viewer_or_403(request)
        archived_note_ids = set(
            NoteArchive.objects.filter(person=ctx.person).values_list("note_id", flat=True),
        )
        qs = (
            Note.all_objects.filter(
                organization=ctx.organization,
                author=ctx.person,
            )
            .exclude(pk__in=archived_note_ids)
            .prefetch_related("audience_captures__person", "replies", "read_receipts")
            .select_related("author")
            .order_by("-created_at")
        )
        paginator = NotesPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = NoteListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class NotesArchiveView(APIView):
    def get(self, request):
        ctx = viewer_or_403(request)
        archived_note_ids = set(
            NoteArchive.objects.filter(person=ctx.person).values_list("note_id", flat=True),
        )
        qs = (
            Note.all_objects.filter(
                organization=ctx.organization,
                pk__in=archived_note_ids,
            )
            .prefetch_related("audience_captures__person", "replies", "read_receipts")
            .select_related("author")
            .order_by("-created_at")
        )
        paginator = NotesPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = NoteListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class NotesUnreadCountView(APIView):
    def get(self, request):
        ctx = viewer_or_403(request)
        archived_note_ids = set(
            NoteArchive.objects.filter(person=ctx.person).values_list("note_id", flat=True),
        )
        inbox_notes = Note.all_objects.filter(
            organization=ctx.organization,
            audience_captures__person=ctx.person,
        ).exclude(pk__in=archived_note_ids).distinct()

        unread_count = 0
        for note in inbox_notes.prefetch_related("replies", "read_receipts"):
            receipt = next(
                (r for r in note.read_receipts.all() if r.person_id == ctx.person.id),
                None,
            )
            if receipt is None:
                unread_count += 1
                continue
            last_reply = note.replies.order_by("-created_at").first()
            latest = last_reply.created_at if last_reply else note.created_at
            if latest > receipt.last_read_at:
                unread_count += 1

        return Response({"count": unread_count})


class NotesAudienceOptionsView(APIView):
    def get(self, request):
        ctx = viewer_or_403(request)
        options = audience_options_for(ctx.person, ctx.organization, ctx.program)
        serializer = AudienceOptionSerializer(options, many=True)
        return Response(serializer.data)


class NotesAudienceCandidatesView(APIView):
    """Return persons + bunks for the composer autocomplete dropdowns."""

    def get(self, request):
        from bunk_logs.core.models import AssignmentGroup
        from bunk_logs.core.models import AssignmentGroupMembership

        ctx = viewer_or_403(request)

        person_qs = (
            Person.all_objects.filter(
                organization=ctx.organization,
                memberships__is_active=True,
                memberships__program__organization=ctx.organization,
            )
            .exclude(id=ctx.person.id)
            .distinct()
            .order_by("last_name", "first_name")
        )
        persons = [
            {"id": p.id, "full_name": p.full_name}
            for p in person_qs[:500]
        ]

        bunk_qs = AssignmentGroup.all_objects.filter(
            organization=ctx.organization,
            group_type="bunk",
        )
        if ctx.membership.role in ("counselor", "junior_counselor"):
            bunk_ids = AssignmentGroupMembership.all_objects.filter(
                person=ctx.person,
                group__group_type="bunk",
                role_in_group="author",
            ).values_list("group_id", flat=True)
            bunk_qs = bunk_qs.filter(id__in=bunk_ids)
        elif ctx.membership.role == "unit_head":
            from bunk_logs.core.models import Supervision

            bunk_ids = Supervision.objects.bunks_for_uh(ctx.membership).values_list(
                "id",
                flat=True,
            )
            bunk_qs = bunk_qs.filter(id__in=bunk_ids)
        else:
            bunk_qs = bunk_qs.none()

        bunks = [{"id": b.id, "name": b.name} for b in bunk_qs.order_by("name")]
        return Response({"persons": persons, "bunks": bunks})


class NoteThreadView(APIView):
    def get(self, request, note_id: int):
        ctx = viewer_or_403(request)
        note = _active_note_for(ctx, note_id)
        if note is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        note = (
            Note.all_objects.prefetch_related(
                "audience_captures__person",
                "replies__author",
                "read_receipts",
            )
            .select_related("author")
            .get(pk=note.pk)
        )
        _update_read_receipt(note, ctx.person)
        serializer = NoteThreadSerializer(note, context={"request": request})
        return Response(serializer.data)


class NoteCreateView(APIView):
    def post(self, request):
        ctx = viewer_or_403(request)
        serializer = NoteCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        audience_rows = resolve_audience(
            author_person=ctx.person,
            author_membership=ctx.membership,
            organization=ctx.organization,
            program=ctx.program,
            audience_requests=data["audience"],
        )
        if not audience_rows:
            return Response(
                {"audience": "Resolved audience is empty after self-exclusion. "
                 "Notes to yourself are not supported (decision N1)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        camper_reference = None
        if data.get("camper_reference_id"):
            camper_reference = Person.all_objects.filter(
                id=data["camper_reference_id"],
                organization=ctx.organization,
            ).first()

        note = Note.objects.create(
            organization=ctx.organization,
            program=ctx.program,
            author=ctx.person,
            author_role_at_write=ctx.membership.role,
            subject=data["subject"],
            body=data["body"],
            camper_reference=camper_reference,
            source_content_type=data.get("source_content_type", ""),
            source_object_id=data.get("source_object_id", ""),
        )

        for row in audience_rows:
            NoteAudienceCapture.objects.create(
                note=note,
                person=row["person"],
                option_key=row["option_key"],
                bunk_id_at_capture=row.get("bunk_id_at_capture"),
            )

        audit_trail.created(
            actor=ctx.membership,
            content=note,
            content_type="note",
        )

        serializer = NoteThreadSerializer(note, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class NoteReplyCreateView(APIView):
    def post(self, request, note_id: int):
        ctx = viewer_or_403(request)
        note = _active_note_for(ctx, note_id)
        if note is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = NoteReplyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reply = NoteReply.objects.create(
            note=note,
            author=ctx.person,
            author_role_at_write=ctx.membership.role,
            body=serializer.validated_data["body"],
        )

        audit_trail.created(
            actor=ctx.membership,
            content=note,
            content_type="note_reply",
            metadata={"reply_id": reply.id},
        )
        _update_read_receipt(note, ctx.person)

        from .serializers import NoteReplySerializer
        return Response(
            NoteReplySerializer(reply).data,
            status=status.HTTP_201_CREATED,
        )


class NoteArchiveView(APIView):
    def post(self, request, note_id: int):
        ctx = viewer_or_403(request)
        note = _active_note_for(ctx, note_id)
        if note is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        NoteArchive.objects.get_or_create(note=note, person=ctx.person)
        audit_trail.state_changed(
            actor=ctx.membership,
            content=note,
            before_state="active",
            after_state="archived",
            content_type="note",
        )
        return Response({"archived": True})


class NoteUnarchiveView(APIView):
    def post(self, request, note_id: int):
        ctx = viewer_or_403(request)
        # For unarchive, allow access even if the note is currently archived
        try:
            note = Note.all_objects.filter(organization=ctx.organization).get(pk=note_id)
        except Note.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        # Check visibility
        is_author = note.author_id == ctx.person.id
        is_audience = note.audience_captures.filter(person=ctx.person).exists()
        if not is_author and not is_audience:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        NoteArchive.objects.filter(note=note, person=ctx.person).delete()
        audit_trail.state_changed(
            actor=ctx.membership,
            content=note,
            before_state="archived",
            after_state="active",
            content_type="note",
        )
        return Response({"archived": False})


class NoteFromBunkConcernView(APIView):
    """Story 69: Return a draft note pre-filled from a Bunk concern field."""

    def post(self, request):
        ctx = viewer_or_403(request)
        if ctx.membership.role not in ("unit_head", "leadership_team", "admin"):
            return Response(
                {"detail": "Only Unit Head, LT, or Admin can start a note from a Bunk concern."},
                status=status.HTTP_403_FORBIDDEN,
            )

        concern_reflection_id = request.data.get("concern_reflection_id")
        concern_field_key = request.data.get("concern_field_key")
        if not concern_reflection_id or not concern_field_key:
            return Response(
                {"detail": "concern_reflection_id and concern_field_key are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reflection = Reflection.all_objects.filter(
                organization=ctx.organization,
            ).select_related("author", "template").get(pk=concern_reflection_id)
        except Reflection.DoesNotExist:
            return Response({"detail": "Reflection not found."}, status=status.HTTP_404_NOT_FOUND)

        concern_text = _extract_field_value(reflection, concern_field_key)

        draft = {
            "subject": f"Re: concern from {reflection.author.full_name}",
            "body": concern_text or "",
            "source_content_type": "reflection_concern",
            "source_object_id": str(reflection.id),
            "audience": [
                {"option_key": "specific_counselor", "person_id": reflection.author_id},
            ],
        }
        return Response({"draft": draft})


class NoteFromSpecialistNoteView(APIView):
    """Story 70: Return a draft note pre-filled from a Specialist camper note."""

    def post(self, request):
        ctx = viewer_or_403(request)

        reflection_id = request.data.get("reflection_id")
        if not reflection_id:
            return Response(
                {"detail": "reflection_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reflection = Reflection.all_objects.filter(
                organization=ctx.organization,
            ).select_related("author", "template", "subject").get(pk=reflection_id)
        except Reflection.DoesNotExist:
            return Response({"detail": "Reflection not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validate: must be a specialist-role template
        template = reflection.template
        if not template or template.role != "specialist":
            return Response(
                {"detail": "Referenced reflection is not a specialist note."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate: requestor must be counselor on the camper's bunk OR the reflection author
        is_author = reflection.author_id == ctx.person.id
        is_counselor_on_bunk = False
        if not is_author and ctx.membership.role in ("counselor", "junior_counselor"):
            from bunk_logs.core.models import AssignmentGroupMembership
            # Check if the camper (subject) is on a bunk where viewer is an author
            if reflection.subject_id:
                bunk_ids_for_viewer = set(
                    AssignmentGroupMembership.all_objects.filter(
                        person=ctx.person,
                        group__group_type="bunk",
                        role_in_group="author",
                        is_active=True,
                    ).values_list("group_id", flat=True),
                )
                is_counselor_on_bunk = AssignmentGroupMembership.all_objects.filter(
                    person_id=reflection.subject_id,
                    group_id__in=bunk_ids_for_viewer,
                    role_in_group="subject",
                ).exists()

        if not is_author and not is_counselor_on_bunk:
            return Response(
                {"detail": "You are not authorized to reference this specialist note."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Reject sensitive notes (if the reflection has a sensitive flag)
        if getattr(reflection, "is_sensitive", False):
            return Response(
                {"detail": "Cannot reference a sensitive specialist note (Story 70 c9)."},
                status=status.HTTP_403_FORBIDDEN,
            )

        draft = {
            "subject": f"Re: {reflection.author.full_name}'s note",
            "body": "",
            "source_content_type": "specialist_note",
            "source_object_id": str(reflection.id),
            "camper_reference_id": reflection.subject_id,
            "audience": [
                {"option_key": "specific_person", "person_id": reflection.author_id},
            ],
        }
        return Response({"draft": draft})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_field_value(reflection, field_key: str) -> str | None:
    """Pull a specific field value from a reflection's answers JSON."""
    answers = getattr(reflection, "answers", {}) or {}
    val = answers.get(field_key)
    if isinstance(val, str):
        return val
    return None

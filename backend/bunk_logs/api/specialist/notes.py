"""Specialist note write endpoints — Stories 26-27.

Endpoints:

* ``POST  /api/v1/specialist/notes/``         — create a specialist note.
* ``PATCH /api/v1/specialist/notes/<id>/``    — edit within 24h window.
* ``GET   /api/v1/specialist/notes/audience/`` — AudienceDisclosure copy.

Category enum for specialist notes (Story 26 criterion 2):
  positive / concern / milestone / behavioral / other
These are stored in ``Note.category``; the values are short strings that
fit within the field's ``max_length`` and are validated in-endpoint rather
than against ``Note.Category`` (which retains CC-facing values).

Flag creation (Story 26 criterion 7 / Step 7_8 model):
  Submitting with ``flag_for_camper_care=True`` calls
  :func:`core.flags.raise_flag_from_specialist_note` which writes a Flag
  row with ``trigger_content_type='specialist_note'``.

Flag retraction (Story 27 criterion 5 / Decision S5):
  Once a flag is raised, the PATCH endpoint enforces that
  ``flag_for_camper_care`` cannot change back to ``False``.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.content_visibility import ContentType
from bunk_logs.core.content_visibility import audience_labels
from bunk_logs.core.flags import raise_flag_from_specialist_note
from bunk_logs.core.models import Flag
from bunk_logs.core.models import Note
from bunk_logs.core.models import Person
from bunk_logs.core.models import note_snapshot

from .common import viewer_or_403

EDIT_WINDOW = timedelta(hours=24)

SPECIALIST_CATEGORIES: frozenset[str] = frozenset({
    "positive", "concern", "milestone", "behavioral", "other",
})
EDIT_FIELDS: frozenset[str] = frozenset({"body", "is_sensitive", "category", "language"})


class SpecialistNoteCreateView(APIView):
    """``POST /api/v1/specialist/notes/``."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}

        subject_id = data.get("subject_id")
        body = (data.get("body") or "").strip()
        category = (data.get("category") or "").strip().lower()
        is_sensitive = bool(data.get("is_sensitive"))
        flag_for_camper_care = bool(data.get("flag_for_camper_care"))
        language = (data.get("language") or "en").strip()

        errors: dict[str, str] = {}
        if subject_id is None:
            errors["subject_id"] = "Required."
        if not body:
            errors["body"] = "Required."
        if category and category not in SPECIALIST_CATEGORIES:
            errors["category"] = (
                f"Must be one of: {', '.join(sorted(SPECIALIST_CATEGORIES))} or blank."
            )
        if errors:
            return Response(errors, status=http_status.HTTP_400_BAD_REQUEST)

        try:
            subject = Person.all_objects.get(pk=subject_id)
        except Person.DoesNotExist:
            return Response(
                {"subject_id": "Camper not found."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            note = Note(
                organization=ctx.organization,
                program=ctx.program,
                subject=subject,
                author=ctx.person,
                note_type=Note.NoteType.SPECIALIST,
                body=body,
                category=category,
                is_sensitive=is_sensitive,
                language=language,
            )
            try:
                note.full_clean(exclude=["category"])
            except DjangoValidationError as exc:
                return Response(
                    exc.message_dict if hasattr(exc, "message_dict") else {"detail": str(exc)},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            note.save()

            audit_module.created(
                ctx.membership,
                note,
                after_state=note_snapshot(note),
                content_type="note",
            )

            if flag_for_camper_care:
                raise_flag_from_specialist_note(note, raised_by=ctx.membership)

        return Response(
            _note_payload(note, flag_raised=flag_for_camper_care),
            status=http_status.HTTP_201_CREATED,
        )


class SpecialistNoteDetailView(APIView):
    """``PATCH /api/v1/specialist/notes/<id>/`` — edit within 24h window."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["patch", "head", "options"]

    def patch(self, request, note_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        note = (
            Note.objects.filter(
                pk=note_id,
                note_type=Note.NoteType.SPECIALIST,
                organization=ctx.organization,
            ).first()
        )
        if note is None:
            msg = "Note not found."
            raise NotFound(msg)

        if note.author_id != ctx.person.id:
            msg = "Only the original author may edit a specialist note."
            raise PermissionDenied(msg)

        if (timezone.now() - note.created_at) > EDIT_WINDOW:
            msg = "This note can no longer be edited (24h window has closed)."
            raise PermissionDenied(msg)

        data = request.data or {}
        unknown = set(data.keys()) - EDIT_FIELDS
        if unknown:
            return Response(
                {"detail": f"Unknown fields: {sorted(unknown)}."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        # S5: Specialist cannot retract a flag they raised.
        if "flag_for_camper_care" in data:
            return Response(
                {"flag_for_camper_care": "Flag state cannot be changed after submission."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        before = note_snapshot(note)

        if "body" in data:
            new_body = (data.get("body") or "").strip()
            if not new_body:
                return Response({"body": "Cannot be empty."}, status=http_status.HTTP_400_BAD_REQUEST)
            note.body = new_body
        if "is_sensitive" in data:
            note.is_sensitive = bool(data["is_sensitive"])
        if "category" in data:
            cat = (data.get("category") or "").strip().lower()
            if cat and cat not in SPECIALIST_CATEGORIES:
                return Response(
                    {"category": f"Must be one of: {', '.join(sorted(SPECIALIST_CATEGORIES))} or blank."},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            note.category = cat
        if "language" in data:
            note.language = (data.get("language") or "en").strip()

        with transaction.atomic():
            try:
                note.full_clean(exclude=["category"])
            except DjangoValidationError as exc:
                return Response(
                    exc.message_dict if hasattr(exc, "message_dict") else {"detail": str(exc)},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            note.save()
            after = note_snapshot(note)
            audit_module.edited(
                ctx.membership, note, before, after, content_type="note",
            )

        flag_raised = Flag.all_objects.filter(
            trigger_content_type="specialist_note",
            trigger_content_id=str(note.id),
        ).exists()
        return Response(_note_payload(note, flag_raised=flag_raised))


class SpecialistNoteAudienceView(APIView):
    """``GET /api/v1/specialist/notes/audience/?is_sensitive=<>`` — AudienceDisclosure."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        viewer_or_403(request)
        is_sensitive = (request.query_params.get("is_sensitive") or "").lower() in {"1", "true"}
        labels = audience_labels(ContentType.SPECIALIST_NOTE, is_sensitive=is_sensitive)
        return Response({"audience": labels, "is_sensitive": is_sensitive})


def _note_payload(note: Note, *, flag_raised: bool = False) -> dict:
    return {
        "id": note.id,
        "subject_id": note.subject_id,
        "author_id": note.author_id,
        "note_type": note.note_type,
        "body": note.body,
        "category": note.category,
        "is_sensitive": bool(note.is_sensitive),
        "flag_raised": flag_raised,
        "language": note.language,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
        "is_within_edit_window": (timezone.now() - note.created_at) <= EDIT_WINDOW,
    }

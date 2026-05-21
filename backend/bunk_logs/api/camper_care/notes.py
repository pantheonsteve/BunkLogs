"""Camper Care notes — submit + edit (Story 21).

Endpoints:

* ``POST  /api/v1/camper-care/notes/`` — submit a note
* ``PATCH /api/v1/camper-care/notes/<id>/`` — edit within 24h of original create

Visibility:

* Author always sees their own note.
* Other readers follow the visibility model (Step 7_1) -- see
  ``content_visibility.CAMPER_CARE_NOTE`` + the sensitive variant.
  CC5 specifically excludes Counselors and UH from non-sensitive
  Camper Care notes; a regression test in ``test_camper_care_notes``
  pins that contract.

Edit-window mechanics (Story 21 criterion 6):

* 24h from original submission (NOT from the last edit), measured in
  org-local time. After expiry, the row is read-only -- the author
  receives a 403 and the UI should hide the Edit affordance.
* Only the original author can edit; another Camper Care member must
  add a follow-up note (criterion 7).
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
from bunk_logs.core.filters import notes_visible_to
from bunk_logs.core.models import Note
from bunk_logs.core.models import Person
from bunk_logs.core.models import note_snapshot

from .common import viewer_or_403

EDIT_WINDOW = timedelta(hours=24)
VALID_CATEGORIES: frozenset[str] = frozenset(c.value for c in Note.Category)
EDIT_FIELDS: frozenset[str] = frozenset({"body", "is_sensitive", "category", "language"})


class CamperCareNoteCreateView(APIView):
    """``POST /api/v1/camper-care/notes/`` — create a Camper Care note."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}

        subject_id = data.get("subject_id")
        body = (data.get("body") or "").strip()
        category = (data.get("category") or "").strip().lower()
        is_sensitive = bool(data.get("is_sensitive"))
        language = (data.get("language") or "en").strip()

        errors: dict[str, str] = {}
        if subject_id is None:
            errors["subject_id"] = "Required."
        if not body:
            errors["body"] = "Required."
        if category not in VALID_CATEGORIES:
            errors["category"] = (
                f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}."
            )
        if errors:
            return Response(errors, status=http_status.HTTP_400_BAD_REQUEST)

        try:
            subject = Person.objects.get(pk=subject_id)
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
                note_type=Note.NoteType.CAMPER_CARE,
                body=body,
                category=category,
                is_sensitive=is_sensitive,
                language=language,
            )
            try:
                note.full_clean()
            except DjangoValidationError as e:
                return Response(
                    e.message_dict if hasattr(e, "message_dict") else {"detail": str(e)},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            note.save()

            audit_module.created(
                ctx.membership,
                note,
                after_state=note_snapshot(note),
                content_type="note",
            )

        return Response(_note_payload(note), status=http_status.HTTP_201_CREATED)


class CamperCareNoteDetailView(APIView):
    """``PATCH /api/v1/camper-care/notes/<id>/`` — edit within the 24h window."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["patch", "head", "options"]

    def patch(self, request, note_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        note = (
            Note.objects.filter(
                pk=note_id, note_type=Note.NoteType.CAMPER_CARE,
            ).first()
        )
        if note is None:
            msg = "Note not found."
            raise NotFound(msg)

        # Visibility check + author gate: the viewer must be able to read
        # the note AND be the original author. Other Camper Care members
        # must add a follow-up note (criterion 7).
        readable = notes_visible_to(request.user).filter(pk=note.pk).exists()
        if not readable:
            msg = "Note not found."
            raise NotFound(msg)
        if note.author_id != ctx.person.id:
            msg = "Only the original author may edit a Camper Care note."
            raise PermissionDenied(msg)

        # 24h edit window from ORIGINAL create -- not last edit.
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

        before = note_snapshot(note)
        if "body" in data:
            new_body = (data.get("body") or "").strip()
            if not new_body:
                return Response(
                    {"body": "Cannot be empty."},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            note.body = new_body
        if "is_sensitive" in data:
            note.is_sensitive = bool(data["is_sensitive"])
        if "category" in data:
            cat = (data.get("category") or "").strip().lower()
            if cat not in VALID_CATEGORIES:
                return Response(
                    {"category": f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}."},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            note.category = cat
        if "language" in data:
            note.language = (data.get("language") or "en").strip()

        with transaction.atomic():
            try:
                note.full_clean()
            except DjangoValidationError as e:
                return Response(
                    e.message_dict if hasattr(e, "message_dict") else {"detail": str(e)},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            note.save()
            after = note_snapshot(note)
            audit_module.edited(
                ctx.membership,
                note,
                before,
                after,
                content_type="note",
            )

        return Response(_note_payload(note))


# ---------------------------------------------------------------------------
# Audience disclosure helper for the form
# ---------------------------------------------------------------------------


class CamperCareNoteAudienceView(APIView):
    """``GET /api/v1/camper-care/notes/audience/?is_sensitive=<>`` — disclosure copy.

    Lets the form render the AudienceDisclosure with the canonical role
    labels resolved server-side (so toggling Sensitive on the client
    gets the authoritative list without re-encoding the audience table
    in JS).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        viewer_or_403(request)
        is_sensitive = (request.query_params.get("is_sensitive") or "").lower() in {
            "1", "true",
        }
        labels = audience_labels(
            ContentType.CAMPER_CARE_NOTE, is_sensitive=is_sensitive,
        )
        return Response({
            "audience": labels,
            "is_sensitive": is_sensitive,
        })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _note_payload(note: Note) -> dict:
    return {
        "id": note.id,
        "subject_id": note.subject_id,
        "author_id": note.author_id,
        "note_type": note.note_type,
        "body": note.body,
        "category": note.category,
        "is_sensitive": bool(note.is_sensitive),
        "language": note.language,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
        "is_within_edit_window": (
            (timezone.now() - note.created_at) <= EDIT_WINDOW
        ),
    }

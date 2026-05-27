"""Unified reply thread for camper notes (core.Note types specialist + camper_care).

Endpoints:
  GET  /api/v1/camper-notes/<note_id>/replies/  — list replies chronologically.
  POST /api/v1/camper-notes/<note_id>/replies/  — add a reply (body required).

Access gate: any authenticated staff member whose role is in the note's
visibility audience (per ``notes_visible_to``), plus the note's original
author. This covers both specialist and camper_care note types without
requiring a role-specific endpoint per type.
"""

from __future__ import annotations

from rest_framework import status as http_status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.filters import notes_visible_to
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Note
from bunk_logs.core.models import NoteReply
from bunk_logs.core.models import Person

_ALLOWED_TYPES = frozenset({Note.NoteType.SPECIALIST, Note.NoteType.CAMPER_CARE})


class CamperNoteRepliesView(APIView):
    """GET + POST replies for a camper note (specialist or camper_care)."""

    permission_classes = [IsAuthenticated]

    def _resolve(self, request, note_id: int):
        """Return (note, person, membership) or raise an appropriate DRF exception."""
        org = getattr(request, "organization", None)
        if org is None:
            raise PermissionDenied("Organization context required.")

        person = Person.objects.filter(user=request.user, organization=org).first()
        if person is None:
            raise PermissionDenied("Person profile required.")

        note = (
            Note.objects.filter(
                pk=note_id,
                note_type__in=_ALLOWED_TYPES,
                organization=org,
            )
            .prefetch_related("replies__author")
            .first()
        )
        if note is None:
            raise NotFound("Note not found.")

        # Author always has access; otherwise check role-based visibility.
        if note.author_id != person.id:
            if not notes_visible_to(request.user, Note.objects.filter(pk=note.pk)).exists():
                raise PermissionDenied("You do not have access to this note.")

        membership = (
            Membership.objects.filter(person=person, is_active=True)
            .order_by("-created_at")
            .first()
        )
        if membership is None:
            raise PermissionDenied("Active membership required.")

        return note, person, membership

    def get(self, request, note_id: int, *args, **kwargs):
        note, _person, _membership = self._resolve(request, note_id)
        return Response([_reply_payload(r) for r in note.replies.all()])

    def post(self, request, note_id: int, *args, **kwargs):
        note, person, membership = self._resolve(request, note_id)

        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"body": "Required."}, status=http_status.HTTP_400_BAD_REQUEST)
        if len(body) > 10_000:
            return Response(
                {"body": "Replies may not exceed 10 000 characters."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        reply = NoteReply.objects.create(
            note=note,
            author=person,
            author_role_at_write=membership.role,
            body=body,
        )
        return Response(_reply_payload(reply), status=http_status.HTTP_201_CREATED)


def _reply_payload(reply: NoteReply) -> dict:
    author = reply.author
    author_name = (
        " ".join(filter(None, [
            (author.preferred_name or author.first_name or "").strip(),
            (author.last_name or "").strip(),
        ]))
        if author else "Unknown"
    )
    return {
        "id": reply.id,
        "author_name": author_name,
        "author_role": reply.author_role_at_write,
        "body": reply.body,
        "created_at": reply.created_at.isoformat(),
    }

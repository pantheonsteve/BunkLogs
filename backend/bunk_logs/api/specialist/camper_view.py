"""``GET /api/v1/specialist/campers/<camper_id>/`` — Story 28.

Specialist-scoped camper dashboard variant. Intentionally minimal:

  * **Header** — camper name, bunk, age/grade.
  * **My notes about this camper** — only notes authored by the requesting
    Specialist; no other roles' content, no reflections, no flags.
    Date-range filter via ``date_from`` / ``date_to`` query params (criterion 6).

Visibility filtering is at the queryset level (criterion 4): the query itself
only returns the viewer's own notes. There is no client-side hiding.

Access gate: the camper must be rostered (active AssignmentGroupMembership as
"subject") in at least one program where the viewer has an active specialist
Membership. Direct URL access by non-specialists returns 403 (criterion 5).
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Note
from bunk_logs.core.models import Person
from bunk_logs.core.models import NoteReply

from .common import specialist_program_ids
from .common import viewer_or_403

EDIT_WINDOW = timedelta(hours=24)


class SpecialistCamperView(APIView):
    """Specialist-scoped per-camper view (Story 28)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, camper_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        program_ids = specialist_program_ids(ctx.person)

        camper = Person.all_objects.filter(
            id=camper_id, organization=ctx.organization,
        ).first()
        if camper is None:
            msg = "Camper not found."
            raise NotFound(msg)

        if not _viewer_shares_program(camper, program_ids):
            msg = "You don't have access to this view."
            raise PermissionDenied(msg)

        date_from = _parse_date_param(request.query_params.get("date_from"))
        date_to = _parse_date_param(request.query_params.get("date_to"))

        notes_qs = (
            Note.objects.filter(
                organization=ctx.organization,
                author=ctx.person,
                subject=camper,
                note_type=Note.NoteType.SPECIALIST,
            )
            .prefetch_related("replies__author")
            .order_by("-created_at")
        )
        if date_from:
            notes_qs = notes_qs.filter(created_at__date__gte=date_from)
        if date_to:
            notes_qs = notes_qs.filter(created_at__date__lte=date_to)

        now = timezone.now()
        bunk_info = _camper_bunk(camper, program_ids)

        return Response({
            "camper": {
                "id": camper.id,
                "display_name": _full_name(camper),
                "preferred_name": (camper.preferred_name or None),
                "first_name": camper.first_name,
                "last_name": camper.last_name,
                "bunk_name": bunk_info.get("bunk_name"),
                "unit_name": bunk_info.get("unit_name"),
            },
            "my_notes": [_note_payload(n, now) for n in notes_qs],
            "date_filter": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None,
            },
        })


def _viewer_shares_program(camper: Person, program_ids: list[int]) -> bool:
    """True iff the camper is an active subject in any of the viewer's programs."""
    return AssignmentGroupMembership.objects.filter(
        person=camper,
        group__program_id__in=program_ids,
        role_in_group="subject",
        is_active=True,
        group__group_type="bunk",
        group__is_active=True,
    ).exists()


def _camper_bunk(camper: Person, program_ids: list[int]) -> dict:
    agm = (
        AssignmentGroupMembership.objects.filter(
            person=camper,
            group__program_id__in=program_ids,
            role_in_group="subject",
            is_active=True,
            group__group_type="bunk",
            group__is_active=True,
        )
        .select_related("group__parent")
        .first()
    )
    if agm is None:
        return {}
    return {
        "bunk_name": agm.group.name,
        "unit_name": (agm.group.parent.name if agm.group.parent_id else None),
    }


def _full_name(person: Person) -> str:
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first} {last}".strip()


def _note_payload(note: Note, now) -> dict:
    replies = [_reply_payload(r) for r in note.replies.all()]
    return {
        "id": note.id,
        "body": note.body,
        "category": note.category or "",
        "is_sensitive": bool(note.is_sensitive),
        "language": note.language,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
        "is_within_edit_window": (now - note.created_at) <= EDIT_WINDOW,
        "replies": replies,
        "reply_count": len(replies),
    }


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


def _parse_date_param(raw: str | None):
    if not raw:
        return None
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid date; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed

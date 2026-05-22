"""``GET /api/v1/specialist/campers/?q=<query>`` — Story 25.

Camper picker with two sections:
  * **Recent** — campers the Specialist noted in the last 7 days (max 8),
    returned regardless of search query.
  * **results** — all campers matching the query, alphabetical by last name.
    Returns all when query is empty (the initial open state shows full roster).

Cross-program: the picker covers all programs where the viewer has an active
specialist Membership (Story 25 criterion 7). Server-side program-boundary
enforcement per criterion 7; long-term withdrawn campers excluded per
criterion 8 (``is_active=False`` AGM rows).

Performance: a single pass through AssignmentGroupMembership returns all
campers + their bunk group in one query. Bunk info is then attached via a
dict lookup so N+1 on subjects is avoided (Story 25 criterion 4).
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Note
from bunk_logs.core.models import Person

from .common import specialist_program_ids
from .common import viewer_or_403

RECENT_DAYS = 7
RECENT_MAX = 8
ZERO_RESULTS_MSG = (
    "No campers match {q}. Try searching by first name, last name, or bunk."
)


class SpecialistCamperPickerView(APIView):
    """Camper picker for Specialist note form (Story 25)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        q = (request.query_params.get("q") or "").strip()
        program_ids = specialist_program_ids(ctx.person)
        if not program_ids:
            return Response({"recent": [], "results": [], "zero_results_message": None})

        camper_rows = list(
            AssignmentGroupMembership.objects.filter(
                group__program_id__in=program_ids,
                role_in_group="subject",
                is_active=True,
                group__group_type="bunk",
                group__is_active=True,
            )
            .select_related("person", "group")
            .order_by("person__last_name", "person__first_name"),
        )

        person_to_bunk: dict[int, str] = {}
        all_persons: dict[int, Person] = {}
        for agm in camper_rows:
            if agm.person_id and agm.person_id not in person_to_bunk:
                person_to_bunk[agm.person_id] = agm.group.name or ""
                all_persons[agm.person_id] = agm.person

        recent_subject_ids = _recent_subject_ids(ctx.person, program_ids)

        if q:
            bunk_match_ids = set(
                AssignmentGroupMembership.objects.filter(
                    group__program_id__in=program_ids,
                    role_in_group="subject",
                    is_active=True,
                    group__group_type="bunk",
                    group__is_active=True,
                    group__name__icontains=q,
                ).values_list("person_id", flat=True),
            )
            matched_ids = {
                pid
                for pid, person in all_persons.items()
                if (
                    q.lower() in (person.first_name or "").lower()
                    or q.lower() in (person.last_name or "").lower()
                    or q.lower() in (person.preferred_name or "").lower()
                    or pid in bunk_match_ids
                )
            }
        else:
            matched_ids = set(all_persons.keys())

        results = [
            _camper_row(all_persons[pid], person_to_bunk.get(pid, ""))
            for pid in sorted(
                matched_ids,
                key=lambda pid: (
                    (all_persons[pid].last_name or "").lower(),
                    (all_persons[pid].first_name or "").lower(),
                ),
            )
        ]

        recent = [
            _camper_row(all_persons[pid], person_to_bunk.get(pid, ""))
            for pid in recent_subject_ids
            if pid in all_persons
        ][:RECENT_MAX]

        zero_results_message = (
            ZERO_RESULTS_MSG.format(q=q) if (q and not results) else None
        )

        return Response({
            "recent": recent,
            "results": results,
            "zero_results_message": zero_results_message,
        })


def _recent_subject_ids(viewer: Person, program_ids: list[int]) -> list[int]:
    """Person IDs of campers the viewer noted in the last RECENT_DAYS days."""
    since = timezone.now() - timedelta(days=RECENT_DAYS)
    rows = (
        Note.objects.filter(
            program_id__in=program_ids,
            author=viewer,
            note_type=Note.NoteType.SPECIALIST,
            created_at__gte=since,
            subject__isnull=False,
        )
        .order_by("-created_at")
        .values("subject_id")
    )
    seen: list[int] = []
    seen_set: set[int] = set()
    for row in rows:
        sid = row["subject_id"]
        if sid and sid not in seen_set:
            seen.append(sid)
            seen_set.add(sid)
        if len(seen) >= RECENT_MAX:
            break
    return seen


def _camper_row(person: Person, bunk_name: str) -> dict:
    preferred = (person.preferred_name or "").strip()
    first = (person.first_name or "").strip()
    last = (person.last_name or "").strip()
    display_name = f"{preferred or first} {last}".strip()
    return {
        "id": person.id,
        "display_name": display_name,
        "first_name": first,
        "last_name": last,
        "preferred_name": preferred or None,
        "bunk_name": bunk_name or None,
    }

"""``GET /api/v1/specialist/campers/?q=<query>&bunk_id=<id>`` — Story 25.

Camper picker with two sections:
  * **Recent** — campers the Specialist noted in the last 7 days (max 8),
    returned regardless of search query.
  * **results** — all campers matching the query, alphabetical by last name.
    Returns all when query is empty (the initial open state shows full roster).

The response also includes a ``bunks`` list — ``[{id, name}]`` sorted by name
— so the frontend bunk-first dropdown can be populated without a separate
round-trip.  Passing ``bunk_id=<id>`` restricts results to campers in that
bunk; the bunk must belong to one of the viewer's programs.

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

from bunk_logs.core.models import AssignmentGroup
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
        bunk_id_raw = request.query_params.get("bunk_id")
        bunk_id: int | None = None
        if bunk_id_raw:
            try:
                bunk_id = int(bunk_id_raw)
            except (ValueError, TypeError):
                return Response(
                    {"bunk_id": "Must be an integer."},
                    status=400,
                )

        program_ids = specialist_program_ids(ctx.person)
        if not program_ids:
            return Response({"recent": [], "results": [], "bunks": [], "zero_results_message": None})

        agm_filter: dict = {
            "group__program_id__in": program_ids,
            "role_in_group": "subject",
            "is_active": True,
            "group__group_type": "bunk",
            "group__is_active": True,
        }
        if bunk_id is not None:
            agm_filter["group_id"] = bunk_id

        camper_rows = list(
            AssignmentGroupMembership.objects.filter(**agm_filter)
            .select_related("person", "group")
            .order_by("person__last_name", "person__first_name"),
        )

        person_to_bunk: dict[int, str] = {}
        person_to_bunk_id: dict[int, int] = {}
        all_persons: dict[int, Person] = {}
        for agm in camper_rows:
            if agm.person_id and agm.person_id not in person_to_bunk:
                person_to_bunk[agm.person_id] = agm.group.name or ""
                person_to_bunk_id[agm.person_id] = agm.group_id
                all_persons[agm.person_id] = agm.person

        recent_subject_ids = _recent_subject_ids(ctx.person, program_ids)

        if q:
            q_lower = q.lower()
            matched_ids = {
                pid
                for pid, person in all_persons.items()
                if (
                    q_lower in (person.first_name or "").lower()
                    or q_lower in (person.last_name or "").lower()
                    or q_lower in (person.preferred_name or "").lower()
                    or q_lower in person_to_bunk.get(pid, "").lower()
                )
            }
        else:
            matched_ids = set(all_persons.keys())

        results = [
            _camper_row(all_persons[pid], person_to_bunk.get(pid, ""), person_to_bunk_id.get(pid))
            for pid in sorted(
                matched_ids,
                key=lambda pid: (
                    (all_persons[pid].last_name or "").lower(),
                    (all_persons[pid].first_name or "").lower(),
                ),
            )
        ]

        recent = [
            _camper_row(all_persons[pid], person_to_bunk.get(pid, ""), person_to_bunk_id.get(pid))
            for pid in recent_subject_ids
            if pid in all_persons
        ][:RECENT_MAX]

        zero_results_message = (
            ZERO_RESULTS_MSG.format(q=q) if (q and not results) else None
        )

        # Build bunk list from the *unfiltered* set so the dropdown is always
        # complete regardless of the current bunk_id selection.
        bunks = _bunk_list(program_ids)

        return Response({
            "recent": recent,
            "results": results,
            "bunks": bunks,
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


def _camper_row(person: Person, bunk_name: str, bunk_id: int | None = None) -> dict:
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
        "bunk_id": bunk_id,
    }


def _bunk_list(program_ids: list[int]) -> list[dict]:
    """Sorted list of active bunks for the dropdown."""
    rows = (
        AssignmentGroup.all_objects.filter(
            program_id__in=program_ids,
            group_type="bunk",
            is_active=True,
        )
        .order_by("name")
        .values("id", "name")
    )
    return [{"id": r["id"], "name": r["name"]} for r in rows]

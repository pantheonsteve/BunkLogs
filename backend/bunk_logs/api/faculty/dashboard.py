"""``GET /api/v1/faculty/dashboard/`` — Step 7_24.

Faculty home: the classrooms this person authors, each with the three
signals they act on — weekly 3-2-1 completion, upcoming Sunday
availability, and open challenges. Every card links to the classroom's
full dashboard at ``/dashboards/group/<id>/``.

Counts are computed across all of the viewer's classrooms at once (see
:mod:`.classroom_signals`) so a faculty member teaching several rooms
still costs a fixed number of queries. Holding no classrooms is a valid
state and returns an empty list, not a 403.

Step 4_9 adds ``response_queue``: reflection entries routed to faculty and
still open, oldest first, with an escalation tier so a question that has
been waiting three weeks reads differently from yesterday's.
"""

from __future__ import annotations

from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.classroom_challenges.common import classroom_group_ids_for_role
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import ClassroomChallenge
from bunk_logs.core.time_utils import get_current_period

from .classroom_signals import build_availability_window
from .classroom_signals import build_weekly_completion
from .classroom_signals import classroom_subject_memberships
from .common import viewer_or_403
from .roster import response_queue

WEEKLY = "weekly"


def _open_challenge_counts(group_ids: list[int]) -> dict[int, int]:
    rows = (
        ClassroomChallenge.objects.filter(
            assignment_group_id__in=group_ids,
            status=ClassroomChallenge.STATUS_OPEN,
        )
        .values("assignment_group_id")
        .annotate(total=Count("id"))
    )
    return {r["assignment_group_id"]: r["total"] for r in rows}


class FacultyDashboardView(APIView):
    """Faculty home — classrooms I author, with their live signals."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        org = ctx.organization
        program = ctx.program
        today = ctx.today

        group_ids = classroom_group_ids_for_role(
            ctx.person, program, role_in_group="author",
        )
        groups = list(
            AssignmentGroup.objects.filter(id__in=group_ids).order_by("name"),
        )
        memberships_by_group = classroom_subject_memberships(
            program=program, group_ids=group_ids,
        )
        all_memberships = [
            m for rows in memberships_by_group.values() for m in rows
        ]

        completion = build_weekly_completion(
            organization=org,
            program=program,
            person_ids={m.person_id for m in all_memberships},
            as_of=today,
        )
        window = build_availability_window(
            program=program, memberships=all_memberships, today=today,
        )
        open_counts = _open_challenge_counts(group_ids)
        period_start, period_end = get_current_period(
            WEEKLY, org=org, program=program, anchor=today,
        )

        classrooms = []
        for group in groups:
            memberships = memberships_by_group.get(group.id, [])
            reflections = None
            if completion is not None:
                summary = completion.summarize(memberships)
                reflections = {
                    "submitted": summary["submitted_count"],
                    "expected": summary["expected_count"],
                    "template_name": summary["template_name"],
                }
            classrooms.append({
                "id": group.id,
                "name": group.name,
                "slug": group.slug,
                "url": f"/dashboards/group/{group.id}",
                "subject_count": len(memberships),
                "reflections": reflections,
                "availability": (
                    window.summarize(memberships)["next_session"]
                    if window is not None
                    else None
                ),
                "open_challenge_count": open_counts.get(group.id, 0),
            })

        return Response({
            "today": today.isoformat(),
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "cadence": WEEKLY,
            },
            "header": {
                "name": _display_name(ctx.person),
                "role_label": "Faculty",
                "program_name": program.name,
                "preferred_language": ctx.person.preferred_language or "en",
            },
            "classrooms": classrooms,
            "challenges_url": "/faculty/challenges",
            "response_queue": response_queue(ctx),
        })


def _display_name(person) -> str:
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first} {last}".strip() if (first or last) else ""

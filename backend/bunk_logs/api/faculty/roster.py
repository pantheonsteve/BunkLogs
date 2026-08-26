"""Faculty response queue and Madrich roster — Step 4_9 §5.

GET /api/v1/faculty/queue/                     — routed entries, oldest first
GET /api/v1/faculty/roster/                    — supervised Madrichim
GET /api/v1/faculty/roster/<person_id>/        — one Madrich, drill-in

Escalation tiers exist because "oldest first" alone does not tell a faculty
member that something has gone wrong. A tier boundary makes a three-week-old
question look different from yesterday's without needing a second surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Count
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.classroom_challenges.common import classroom_group_ids_for_role
from bunk_logs.api.threads.common import FACULTY
from bunk_logs.api.threads.common import display_name
from bunk_logs.api.threads.common import routed_queue_qs
from bunk_logs.api.threads.common import supervised_subject_ids
from bunk_logs.api.threads.common import thread_list_item
from bunk_logs.api.threads.common import viewer_from_role_ctx
from bunk_logs.core.models import ClassroomChallenge
from bunk_logs.core.models import EntryThread
from bunk_logs.core.models import Person
from bunk_logs.core.reflection_threads import unread_thread_ids

from .classroom_signals import build_availability_window
from .classroom_signals import build_weekly_completion
from .classroom_signals import classroom_subject_memberships
from .common import viewer_or_403

if TYPE_CHECKING:
    from .common import ViewerContext

# Age bands, in days, for the queue's escalation tier. Tuned to the TBE
# weekly cadence: "fresh" is inside the current week, "aging" means a full
# week has passed without an answer, "overdue" means two.
AGING_AFTER_DAYS = 7
OVERDUE_AFTER_DAYS = 14

QUEUE_PREVIEW_LIMIT = 5


class FacultyQueuePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def escalation_tier(age_days: int | None) -> str:
    if age_days is None:
        return "fresh"
    if age_days >= OVERDUE_AFTER_DAYS:
        return "overdue"
    if age_days >= AGING_AFTER_DAYS:
        return "aging"
    return "fresh"


def _queue_rows(ctx: ViewerContext, limit: int | None = None) -> tuple[list[dict], int]:
    """Routed rows plus the total, so the card can show "3 of 12"."""
    viewer = viewer_from_role_ctx(ctx, FACULTY)
    qs = routed_queue_qs(viewer, EntryThread.ROUTES_TO_FACULTY).annotate(
        message_count=Count("messages", distinct=True),
    )
    total = qs.count()
    threads = list(qs[:limit] if limit else qs)
    unread = unread_thread_ids(ctx.person, [t.id for t in threads])
    rows = []
    for thread in threads:
        row = thread_list_item(
            thread,
            unread=thread.id in unread,
            message_count=thread.message_count,
            today=ctx.today,
            org=ctx.organization,
        )
        row["escalation"] = escalation_tier(row["age_days"])
        rows.append(row)
    return rows, total


def response_queue(ctx: ViewerContext) -> dict:
    """Queue summary for the faculty homepage card."""
    rows, total = _queue_rows(ctx, limit=QUEUE_PREVIEW_LIMIT)
    return {
        "total": total,
        "overdue_count": sum(1 for r in rows if r["escalation"] == "overdue"),
        "items": rows,
        "url": "/faculty/queue",
    }


class FacultyQueueView(APIView):
    """Full routed-entry queue, oldest first."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = viewer_from_role_ctx(ctx, FACULTY)
        qs = routed_queue_qs(viewer, EntryThread.ROUTES_TO_FACULTY).annotate(
            message_count=Count("messages", distinct=True),
        )
        paginator = FacultyQueuePagination()
        page = list(paginator.paginate_queryset(qs, request, view=self))
        unread = unread_thread_ids(ctx.person, [t.id for t in page])
        items = []
        for thread in page:
            row = thread_list_item(
                thread,
                unread=thread.id in unread,
                message_count=thread.message_count,
                today=ctx.today,
                org=ctx.organization,
            )
            row["escalation"] = escalation_tier(row["age_days"])
            items.append(row)
        return paginator.get_paginated_response(items)


class FacultyRosterView(APIView):
    """Madrichim in the classrooms this faculty member authors.

    One row per person with the signals faculty act on: this week's
    reflection state, next-session availability, unread thread count, and
    open challenges. Fixed query cost regardless of roster size.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        group_ids = classroom_group_ids_for_role(
            ctx.person, ctx.program, role_in_group="author",
        )
        if not group_ids:
            return Response({"results": [], "classrooms": []})

        memberships_by_group = classroom_subject_memberships(
            program=ctx.program, group_ids=group_ids,
        )
        all_memberships = [m for rows in memberships_by_group.values() for m in rows]
        person_ids = {m.person_id for m in all_memberships}

        completion = build_weekly_completion(
            organization=ctx.organization,
            program=ctx.program,
            person_ids=person_ids,
            as_of=ctx.today,
        )
        window = build_availability_window(
            program=ctx.program, memberships=all_memberships, today=ctx.today,
        )

        viewer = viewer_from_role_ctx(ctx, FACULTY)
        open_threads = list(
            routed_queue_qs(viewer, EntryThread.ROUTES_TO_FACULTY).values_list("id", "subject_person_id"),
        )
        unread = unread_thread_ids(ctx.person, [tid for tid, _ in open_threads])
        open_by_person: dict[int, int] = {}
        unread_by_person: dict[int, int] = {}
        for thread_id, person_id in open_threads:
            open_by_person[person_id] = open_by_person.get(person_id, 0) + 1
            if thread_id in unread:
                unread_by_person[person_id] = unread_by_person.get(person_id, 0) + 1

        challenges_by_person = dict(
            ClassroomChallenge.objects.filter(
                assignment_group_id__in=group_ids,
                status=ClassroomChallenge.STATUS_OPEN,
            )
            .values_list("author_id")
            .annotate(total=Count("id")),
        )

        results = []
        for group_id, memberships in memberships_by_group.items():
            for membership in memberships:
                pid = membership.person_id
                state = None
                reflection_id = None
                if completion is not None:
                    reflection_id = completion.submitted.get(pid)
                    state = "complete" if reflection_id else "missing"
                availability = None
                if window is not None:
                    row = window.rows_by_person.get(pid)
                    if row is not None:
                        availability = _next_session_status(row, window)
                results.append({
                    "person_id": pid,
                    "display_name": display_name(membership.person),
                    "grade_level": membership.grade_level,
                    "classroom_id": group_id,
                    "reflection_state": state,
                    "reflection_id": reflection_id,
                    "next_session_availability": availability,
                    "open_thread_count": open_by_person.get(pid, 0),
                    "unread_thread_count": unread_by_person.get(pid, 0),
                    "open_challenge_count": challenges_by_person.get(pid, 0),
                })
        results.sort(
            key=lambda r: (
                r["grade_level"] is None,
                r["grade_level"] or 0,
                r["display_name"].casefold(),
            ),
        )
        return Response({
            "results": results,
            "period": (
                {
                    "start": completion.period_start.isoformat(),
                    "end": completion.period_end.isoformat(),
                }
                if completion is not None
                else None
            ),
            "next_session": (
                window.session_dates[0].isoformat() if window is not None else None
            ),
        })


def _next_session_status(row: dict, window) -> str | None:
    """The person's status for the nearest upcoming session, or None if unset."""
    next_date = window.session_dates[0].isoformat()
    for cell in row.get("cells") or []:
        if cell.get("session_date") == next_date:
            return cell.get("status")
    return None


class FacultyRosterDetailView(APIView):
    """One supervised Madrich: their threads, reflection state, availability.

    A faculty member who does not supervise this person gets a 403 rather
    than an empty page, so the boundary is explicit rather than implied by
    absent data.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, person_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        supervised = supervised_subject_ids(ctx.person, ctx.program)
        if person_id not in supervised:
            msg = "You do not supervise this person."
            raise PermissionDenied(msg)
        subject = Person.objects.filter(id=person_id).first()
        if subject is None:
            msg = "Person not found."
            raise PermissionDenied(msg)

        viewer = viewer_from_role_ctx(ctx, FACULTY)
        threads = list(
            EntryThread.objects.filter(
                subject_person_id=person_id, reflection__isnull=False,
            )
            .exclude(routes_to=EntryThread.ROUTES_TO_DIRECTOR)
            .select_related("reflection", "reflection__template")
            .annotate(message_count=Count("messages", distinct=True))
            .order_by("-reflection__period_start", "field_key", "item_index"),
        )
        unread = unread_thread_ids(ctx.person, [t.id for t in threads])
        items = []
        for thread in threads:
            row = thread_list_item(
                thread,
                unread=thread.id in unread,
                message_count=thread.message_count,
                today=ctx.today,
                org=ctx.organization,
            )
            row["escalation"] = escalation_tier(row["age_days"])
            items.append(row)

        completion = build_weekly_completion(
            organization=ctx.organization,
            program=ctx.program,
            person_ids={person_id},
            as_of=ctx.today,
        )
        return Response({
            "person": {
                "id": subject.id,
                "display_name": display_name(subject),
            },
            "reflection_state": (
                ("complete" if completion.submitted.get(person_id) else "missing")
                if completion is not None
                else None
            ),
            "entries": items,
            "can_post": viewer.is_faculty,
        })

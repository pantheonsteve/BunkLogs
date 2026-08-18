"""Director homepage endpoints — Step 4_9 §6.

GET reflections/pulse/            — completion this period plus prior periods
GET reflections/queue/            — entries routed to the Director, oldest first
GET reflections/coverage/         — upcoming Sundays x classrooms
GET reflections/faculty-activity/ — per-faculty responsiveness
GET reflections/themes/           — anonymized themes, small groups suppressed
GET reflections/madrichim/        — roster
GET reflections/madrichim/export/ — the same roster as CSV

"Director" is the ``admin`` capability in a religious-school program, not a
new role, so everything here runs behind the admin_flow viewer context.

The availability vocabulary is Step 4_7's ``available`` / ``tentative`` /
``unavailable`` plus unset. There is no required-headcount target in the
system, so a coverage gap is flagged on unset and tentative rather than on
a shortfall against a number nobody has configured.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import TYPE_CHECKING
from typing import Any

from django.db.models import Count
from django.http import HttpResponse
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.faculty.classroom_signals import build_weekly_completion
from bunk_logs.api.faculty.roster import escalation_tier
from bunk_logs.api.threads.common import ADMIN
from bunk_logs.api.threads.common import display_name
from bunk_logs.api.threads.common import routed_queue_qs
from bunk_logs.api.threads.common import thread_list_item
from bunk_logs.api.threads.common import viewer_from_role_ctx
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import EntryThread
from bunk_logs.core.models import MadrichAvailability
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionThemeTag
from bunk_logs.core.models import ThreadMessage
from bunk_logs.core.scheduling.availability_matrix import resolve_session_window
from bunk_logs.core.theme_tagging.taxonomy import theme_label
from bunk_logs.core.time_utils import get_current_period

from .common import resolve_current_program_for_role
from .common import viewer_or_403

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Program

MADRICH = "madrich"
FACULTY = "faculty"
WEEKLY = "weekly"
SUBJECT = "subject"
AUTHOR = "author"
CLASSROOM = "classroom"
RELIGIOUS_SCHOOL = "religious_school"

# §6.1: enough history to read a direction, not so much it stops fitting.
PULSE_PERIODS = 8
# §6.3: six Sundays is roughly the planning horizon a Director works to.
COVERAGE_SESSIONS = 6
# §6.6: below this many distinct contributors an aggregate is re-identifying.
MIN_THEME_CONTRIBUTORS = 5

QUEUE_PREVIEW_LIMIT = 5


def _program(ctx) -> Program | None:
    """The religious-school program this Director's homepage is about."""
    if ctx.membership is not None and ctx.membership.program_id:
        program = ctx.membership.program
        if program.program_type == RELIGIOUS_SCHOOL:
            return program
    return resolve_current_program_for_role(
        ctx.organization, MADRICH, ctx.today, program_type=RELIGIOUS_SCHOOL,
    )


def _madrich_memberships(program: Program) -> list[Membership]:
    return list(
        Membership.objects.filter(
            program=program, role=MADRICH, is_active=True,
        ).select_related("person"),
    )


def _prior_periods(program, org, today: date, count: int) -> list[tuple[date, date]]:
    """The current period plus ``count - 1`` before it, oldest first."""
    from datetime import timedelta

    start, end = get_current_period(WEEKLY, org=org, program=program, anchor=today)
    periods = [(start, end)]
    for _ in range(count - 1):
        start = start - timedelta(days=7)
        periods.append((start, start + timedelta(days=6)))
    return list(reversed(periods))


class DirectorPulseView(APIView):
    """Completion rate this period and over the preceding weeks.

    One reflection query covers the whole window rather than one per
    period, so the history length does not change the query count.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _program(ctx)
        if program is None:
            return Response({"available": False, "periods": [], "current": None})

        memberships = _madrich_memberships(program)
        person_ids = {m.person_id for m in memberships}
        completion = build_weekly_completion(
            organization=ctx.organization,
            program=program,
            person_ids=person_ids,
            as_of=ctx.today,
        )
        if completion is None:
            return Response({
                "available": False,
                "reason": "no_template",
                "periods": [],
                "current": None,
                "active_madrichim": len(memberships),
            })

        periods = _prior_periods(program, ctx.organization, ctx.today, PULSE_PERIODS)
        rows = (
            Reflection.objects.filter(
                template=completion.template,
                is_complete=True,
                period_start__gte=periods[0][0],
                period_end__lte=periods[-1][1],
                author_id__in=person_ids,
            ).values_list("period_start", "author_id", "subject_id")
            if person_ids
            else []
        )
        by_period: dict[date, set[int]] = {}
        for period_start, author_id, subject_id in rows:
            if author_id == subject_id:
                by_period.setdefault(period_start, set()).add(author_id)

        expected = len(memberships)
        series = [
            {
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "submitted": len(by_period.get(start, ())),
                "expected": expected,
                "rate": (
                    round(len(by_period.get(start, ())) / expected, 3)
                    if expected
                    else None
                ),
            }
            for start, end in periods
        ]

        viewer = viewer_from_role_ctx(_ctx_shim(ctx, program), ADMIN)
        open_queue = routed_queue_qs(viewer, EntryThread.ROUTES_TO_DIRECTOR).count()

        return Response({
            "available": True,
            "template_name": completion.template.name,
            "active_madrichim": expected,
            "periods": series,
            "current": series[-1] if series else None,
            "open_question_count": open_queue,
        })


def _ctx_shim(ctx, program):
    """Adapt an :class:`AdminContext` to what ``viewer_from_role_ctx`` reads.

    The admin context has no ``program``, because most admin surfaces are
    org-wide; the thread helpers need one to scope by.
    """
    from types import SimpleNamespace

    return SimpleNamespace(
        person=ctx.person,
        organization=ctx.organization,
        program=program,
        today=ctx.today,
        membership=ctx.membership,
    )


class DirectorQueuePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class DirectorQueueView(APIView):
    """Entries routed to the Director, oldest first with escalation tiers."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _program(ctx)
        if program is None:
            paginator = DirectorQueuePagination()
            paginator.paginate_queryset(EntryThread.objects.none(), request, view=self)
            return paginator.get_paginated_response([])

        viewer = viewer_from_role_ctx(_ctx_shim(ctx, program), ADMIN)
        qs = routed_queue_qs(viewer, EntryThread.ROUTES_TO_DIRECTOR).annotate(
            message_count=Count("messages", distinct=True),
        )
        paginator = DirectorQueuePagination()
        page = list(paginator.paginate_queryset(qs, request, view=self))
        items = []
        for thread in page:
            row = thread_list_item(
                thread, unread=False, message_count=thread.message_count, today=ctx.today,
            )
            row["escalation"] = escalation_tier(row["age_days"])
            items.append(row)
        return paginator.get_paginated_response(items)


class DirectorCoverageView(APIView):
    """Upcoming Sundays x classrooms, with per-cell status counts.

    A cell is flagged when anybody is unset or tentative -- those are the
    two states a Director can act on. There is no required-headcount
    target to compare against.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _program(ctx)
        if program is None:
            return Response({"sessions": [], "classrooms": []})

        sessions = resolve_session_window(program, today=ctx.today)[:COVERAGE_SESSIONS]
        groups = list(
            AssignmentGroup.objects.filter(
                program=program, group_type=CLASSROOM, is_active=True,
            ).order_by("name"),
        )
        if not sessions or not groups:
            return Response({
                "sessions": [s.isoformat() for s in sessions],
                "classrooms": [
                    {"id": g.id, "name": g.name, "cells": []} for g in groups
                ],
            })

        roster = list(
            AssignmentGroupMembership.objects.filter(
                group_id__in=[g.id for g in groups],
                role_in_group=SUBJECT,
                is_active=True,
            ).values_list("group_id", "person_id"),
        )
        person_ids = {pid for _, pid in roster if pid}
        statuses: dict[tuple[int, str], str] = {}
        if person_ids:
            for person_id, session_date, status_value in MadrichAvailability.objects.filter(
                program=program, person_id__in=person_ids, session_date__in=sessions,
            ).values_list("person_id", "session_date", "status"):
                statuses[(person_id, session_date.isoformat())] = status_value

        people_by_group: dict[int, list[int]] = {g.id: [] for g in groups}
        for group_id, person_id in roster:
            if person_id:
                people_by_group[group_id].append(person_id)

        classrooms = []
        for group in groups:
            members = people_by_group.get(group.id, [])
            cells = []
            for session in sessions:
                key = session.isoformat()
                counts = {
                    MadrichAvailability.STATUS_AVAILABLE: 0,
                    MadrichAvailability.STATUS_TENTATIVE: 0,
                    MadrichAvailability.STATUS_UNAVAILABLE: 0,
                    "unset": 0,
                }
                for person_id in members:
                    status_value = statuses.get((person_id, key))
                    counts[status_value if status_value in counts else "unset"] += 1
                cells.append({
                    "session_date": key,
                    "available": counts[MadrichAvailability.STATUS_AVAILABLE],
                    "tentative": counts[MadrichAvailability.STATUS_TENTATIVE],
                    "unavailable": counts[MadrichAvailability.STATUS_UNAVAILABLE],
                    "unset": counts["unset"],
                    "roster_size": len(members),
                    "flagged": counts["unset"] > 0
                    or counts[MadrichAvailability.STATUS_TENTATIVE] > 0,
                })
            classrooms.append({
                "id": group.id,
                "name": group.name,
                "roster_size": len(members),
                "cells": cells,
            })

        return Response({
            "sessions": [s.isoformat() for s in sessions],
            "classrooms": classrooms,
        })


class DirectorFacultyActivityView(APIView):
    """Per-faculty responsiveness: open threads, latency, oldest unanswered.

    Latency is the median gap between an entry being created and the first
    faculty message on it. A faculty member with no answered entries yet
    reports ``null`` rather than 0, which would read as instant.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _program(ctx)
        if program is None:
            return Response({"results": []})

        faculty = list(
            Membership.objects.filter(
                program=program, role=FACULTY, is_active=True,
            ).select_related("person"),
        )
        if not faculty:
            return Response({"results": []})

        faculty_person_ids = {m.person_id for m in faculty}
        classroom_rows = list(
            AssignmentGroupMembership.objects.filter(
                group__program=program,
                group__group_type=CLASSROOM,
                group__is_active=True,
                is_active=True,
                role_in_group__in=[AUTHOR, SUBJECT],
            ).values_list("group_id", "person_id", "role_in_group"),
        )
        authors_by_group: dict[int, list[int]] = {}
        subjects_by_group: dict[int, list[int]] = {}
        for group_id, person_id, role in classroom_rows:
            target = authors_by_group if role == AUTHOR else subjects_by_group
            target.setdefault(group_id, []).append(person_id)

        # faculty person -> the Madrichim they supervise
        supervised: dict[int, set[int]] = {pid: set() for pid in faculty_person_ids}
        for group_id, authors in authors_by_group.items():
            for author_id in authors:
                if author_id in supervised:
                    supervised[author_id].update(subjects_by_group.get(group_id, []))

        all_subjects = {pid for ids in supervised.values() for pid in ids}
        threads = list(
            EntryThread.objects.filter(
                program=program,
                subject_person_id__in=all_subjects or [0],
                reflection__isnull=False,
            )
            .exclude(routes_to=EntryThread.ROUTES_TO_DIRECTOR)
            .values_list("id", "subject_person_id", "created_at", "resolved_at"),
        )
        thread_ids = [tid for tid, *_ in threads]
        first_reply: dict[int, Any] = {}
        for thread_id, created_at in (
            ThreadMessage.objects.filter(
                thread_id__in=thread_ids or [0], author_id__in=faculty_person_ids,
            )
            .order_by("thread_id", "created_at")
            .values_list("thread_id", "created_at")
        ):
            first_reply.setdefault(thread_id, created_at)

        results = []
        for membership in faculty:
            pid = membership.person_id
            subjects = supervised.get(pid, set())
            mine = [t for t in threads if t[1] in subjects]
            open_threads = [t for t in mine if t[3] is None and t[0] not in first_reply]
            latencies = [
                (first_reply[t[0]] - t[2]).total_seconds() / 3600
                for t in mine
                if t[0] in first_reply
            ]
            oldest = min((t[2] for t in open_threads), default=None)
            results.append({
                "person_id": pid,
                "display_name": display_name(membership.person),
                "assigned_madrich_count": len(subjects),
                "open_thread_count": len(open_threads),
                "median_response_hours": (
                    round(_median(latencies), 1) if latencies else None
                ),
                "oldest_unanswered_days": (
                    (ctx.today - oldest.date()).days if oldest else None
                ),
            })
        results.sort(key=lambda r: (-r["open_thread_count"], r["display_name"].casefold()))
        return Response({"results": results})


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


class DirectorThemesView(APIView):
    """Anonymized reflection themes, with small groups suppressed.

    §6.6: a theme carried by fewer than five distinct Madrichim is
    re-identifying, so it is withheld and reported as a suppressed count
    rather than silently dropped -- the Director should know something is
    being held back.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _program(ctx)
        if program is None:
            return Response({"themes": [], "suppressed_count": 0})

        rows = (
            ReflectionThemeTag.objects.filter(program=program)
            .values("theme_key")
            .annotate(
                contributors=Count("reflection__author_id", distinct=True),
                mentions=Count("id"),
            )
            .order_by("-mentions")
        )
        themes = []
        suppressed = 0
        for row in rows:
            if row["contributors"] < MIN_THEME_CONTRIBUTORS:
                suppressed += 1
                continue
            themes.append({
                "theme_key": row["theme_key"],
                "label": theme_label(row["theme_key"]),
                "contributors": row["contributors"],
                "mentions": row["mentions"],
            })
        return Response({
            "themes": themes,
            "suppressed_count": suppressed,
            "min_contributors": MIN_THEME_CONTRIBUTORS,
            "growth_dashboard_url": "/admin/reflections/growth",
        })


def _roster_rows(ctx, program) -> tuple[list[dict], dict]:
    """Roster rows plus the period they describe, shared by JSON and CSV."""
    memberships = _madrich_memberships(program)
    person_ids = {m.person_id for m in memberships}
    completion = build_weekly_completion(
        organization=ctx.organization,
        program=program,
        person_ids=person_ids,
        as_of=ctx.today,
    )
    classrooms = dict(
        AssignmentGroupMembership.objects.filter(
            person_id__in=person_ids or [0],
            role_in_group=SUBJECT,
            is_active=True,
            group__group_type=CLASSROOM,
            group__program=program,
        ).values_list("person_id", "group__name"),
    )
    open_counts = dict(
        EntryThread.objects.filter(
            program=program,
            subject_person_id__in=person_ids or [0],
            resolved_at__isnull=True,
            reflection__isnull=False,
        )
        .values_list("subject_person_id")
        .annotate(total=Count("id")),
    )

    rows = [
        {
            "person_id": m.person_id,
            "display_name": display_name(m.person),
            "grade_level": m.grade_level,
            "classroom": classrooms.get(m.person_id),
            "reflection_state": (
                ("complete" if completion.submitted.get(m.person_id) else "missing")
                if completion is not None
                else None
            ),
            "open_thread_count": open_counts.get(m.person_id, 0),
        }
        for m in memberships
    ]
    rows.sort(
        key=lambda r: (
            r["grade_level"] is None,
            r["grade_level"] or 0,
            r["display_name"].casefold(),
        ),
    )
    period = (
        {
            "start": completion.period_start.isoformat(),
            "end": completion.period_end.isoformat(),
        }
        if completion is not None
        else None
    )
    return rows, period


class DirectorMadrichimView(APIView):
    """Full Madrich roster with this period's reflection state."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _program(ctx)
        if program is None:
            return Response({"results": [], "period": None})
        rows, period = _roster_rows(ctx, program)
        return Response({"results": rows, "period": period})


class DirectorMadrichimExportView(APIView):
    """The roster as CSV, for the "export" affordance on the roster card."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _program(ctx)
        if program is None:
            return _csv_response([], header=[], filename="madrichim.csv")
        rows, period = _roster_rows(ctx, program)
        header = [
            "Name", "Grade", "Classroom", "Reflection this period", "Open threads",
        ]
        body = [
            [
                r["display_name"],
                r["grade_level"] if r["grade_level"] is not None else "",
                r["classroom"] or "",
                r["reflection_state"] or "not configured",
                r["open_thread_count"],
            ]
            for r in rows
        ]
        stamp = period["start"] if period else ctx.today.isoformat()
        return _csv_response(
            body, header=header, filename=f"madrichim-{stamp}.csv",
        )


def _csv_response(rows: list[list[Any]], *, header: list[str], filename: str) -> HttpResponse:
    buf = StringIO()
    writer = csv.writer(buf)
    if header:
        writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

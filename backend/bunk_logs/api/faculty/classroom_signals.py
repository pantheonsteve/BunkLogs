"""Classroom signals faculty see about their Madrichim — Step 7_24.

Two computations shared by the faculty home dashboard (``dashboard.py``)
and the classroom block of the unified group dashboard
(``api/dashboards/group_payloads.py``) so the numbers on the two
surfaces can't drift.

Both are faculty-only reads. A Madrich can legitimately hold
``role_in_group="author"`` on a classroom, so callers must gate on a
faculty Membership check rather than on the ``classroom_author``
dashboard role -- Story 61 criterion 4 forbids showing a Madrich any
peer's completion state or availability.

Each builder resolves once and is then summarized per classroom, so a
faculty member teaching several classrooms still costs one template
resolve, one reflection query, and one availability query.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bunk_logs.core.assignment_resolution import resolve_template_for
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.scheduling.availability_matrix import build_matrix_rows
from bunk_logs.core.scheduling.availability_matrix import resolve_session_window
from bunk_logs.core.scheduling.availability_matrix import summarize_counts
from bunk_logs.core.time_utils import get_current_period

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Person
    from bunk_logs.core.models import Program
    from bunk_logs.core.models import ReflectionTemplate

__all__ = [
    "AvailabilityWindow",
    "WeeklyCompletion",
    "build_availability_window",
    "build_weekly_completion",
    "classroom_subject_memberships",
]


MADRICH_ROLE = "madrich"
WEEKLY = "weekly"
SUBJECT = "subject"

# The classroom dashboard is a glance, not the staffing matrix: four
# sessions is roughly a month of Sundays. The full eight-session window
# stays on ``faculty/classrooms/<id>/availability/``.
DEFAULT_SESSION_LIMIT = 4


def _display_name(person: Person | None) -> str:
    """Match ``availability_matrix`` row naming so both blocks agree."""
    if person is None:
        return ""
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first} {last}".strip()


def classroom_subject_memberships(
    *, program: Program, group_ids: list[int],
) -> dict[int, list[Membership]]:
    """Active Madrich Memberships per classroom id, keyed by group.

    Students in a TBE classroom are the Madrichim holding a ``subject``
    roster row. Every requested group id gets a key so callers can
    render an empty classroom without a lookup guard.
    """
    by_group: dict[int, list[Membership]] = {gid: [] for gid in group_ids}
    if not group_ids:
        return by_group

    roster = list(
        AssignmentGroupMembership.objects.filter(
            group_id__in=group_ids, role_in_group=SUBJECT, is_active=True,
        ).values_list("group_id", "person_id"),
    )
    person_ids = {pid for _, pid in roster if pid}
    if not person_ids:
        return by_group

    memberships = {
        m.person_id: m
        for m in Membership.objects.filter(
            person_id__in=person_ids,
            program=program,
            role=MADRICH_ROLE,
            is_active=True,
        ).select_related("person")
    }
    for group_id, person_id in roster:
        membership = memberships.get(person_id)
        if membership is not None:
            by_group[group_id].append(membership)
    return by_group


# ---------------------------------------------------------------------------
# Weekly 3-2-1 completion
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeeklyCompletion:
    """Who submitted the weekly self-reflection, resolved for one period."""

    template: ReflectionTemplate
    period_start: date
    period_end: date
    submitted: dict[int, int]  # person_id -> reflection id

    def summarize(self, memberships: list[Membership]) -> dict:
        students = []
        submitted_count = 0
        for membership in memberships:
            reflection_id = self.submitted.get(membership.person_id)
            if reflection_id is not None:
                submitted_count += 1
            students.append({
                "person_id": membership.person_id,
                "name": _display_name(membership.person),
                "grade_level": membership.grade_level,
                "state": "complete" if reflection_id else "missing",
                "reflection_id": reflection_id,
            })
        students.sort(
            key=lambda s: (
                s["grade_level"] is None,
                s["grade_level"] or 0,
                s["name"].casefold(),
            ),
        )
        return {
            "template_name": self.template.name,
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
                "cadence": WEEKLY,
            },
            "submitted_count": submitted_count,
            "expected_count": len(memberships),
            "students": students,
        }


def build_weekly_completion(
    *,
    organization: Organization,
    program: Program,
    person_ids: set[int],
    as_of: date,
) -> WeeklyCompletion | None:
    """Resolve the weekly Madrich self-reflection and who has filed it.

    Returns ``None`` when no weekly template is assigned to the program,
    so the UI can say "not configured yet" instead of a misleading 0/N.

    Deliberately keys off ``author == subject`` rather than
    ``assignment_group``: Madrich self-reflections are filed with
    ``assignment_group=None`` (see :mod:`bunk_logs.api.madrich.reflection`),
    so the classroom is joined through the roster, not the reflection.
    """
    template = resolve_template_for(
        organization=organization,
        program=program,
        as_of=as_of,
        role=MADRICH_ROLE,
        subject_mode="self",
        cadence=WEEKLY,
        exclude_cadences=["on_demand"],
    )
    if template is None:
        return None

    period_start, period_end = get_current_period(
        WEEKLY, org=organization, program=program, anchor=as_of,
    )
    submitted: dict[int, int] = {}
    if person_ids:
        rows = Reflection.all_objects.filter(
            template=template,
            period_start=period_start,
            period_end=period_end,
            author_id__in=person_ids,
            subject_id__in=person_ids,
            is_complete=True,
        ).values_list("author_id", "subject_id", "id")
        for author_id, subject_id, reflection_id in rows:
            # Two ``__in`` filters would also match a cross pair (A about
            # B) if one ever existed; a self-reflection is the diagonal.
            if author_id == subject_id:
                submitted.setdefault(author_id, reflection_id)

    return WeeklyCompletion(
        template=template,
        period_start=period_start,
        period_end=period_end,
        submitted=submitted,
    )


# ---------------------------------------------------------------------------
# Sunday availability
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AvailabilityWindow:
    """Availability cells for the next few sessions, indexed by person."""

    session_dates: list[date]
    rows_by_person: dict[int, dict]

    def summarize(self, memberships: list[Membership]) -> dict:
        # ``build_matrix_rows`` already ordered every row by grade then
        # name, so filtering preserves that order within a classroom.
        rows = [
            self.rows_by_person[m.person_id]
            for m in memberships
            if m.person_id in self.rows_by_person
        ]
        counts = summarize_counts(rows, self.session_dates)
        next_session = self.session_dates[0].isoformat()
        return {
            "sessions": [d.isoformat() for d in self.session_dates],
            "rows": rows,
            "available_counts": counts["available_counts"],
            "unset_counts": counts["unset_counts"],
            "next_session": {
                "date": next_session,
                "available": counts["available_counts"][next_session],
                "unset": counts["unset_counts"][next_session],
            },
        }


def build_availability_window(
    *,
    program: Program,
    memberships: list[Membership],
    today: date,
    session_limit: int = DEFAULT_SESSION_LIMIT,
) -> AvailabilityWindow | None:
    """Next few session dates plus each Madrich's cells.

    Returns ``None`` when the program has no upcoming sessions
    configured (``Program.settings['session_dates']`` empty or in the
    past), which is the off-season state.
    """
    session_dates = resolve_session_window(program, today=today)[:session_limit]
    if not session_dates:
        return None
    rows = build_matrix_rows(program, memberships, session_dates)
    return AvailabilityWindow(
        session_dates=session_dates,
        rows_by_person={r["person_id"]: r for r in rows if r["person_id"]},
    )

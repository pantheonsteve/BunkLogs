"""Shared helpers for Madrich (TBE) endpoints — Step 7_14, Stories 61-65.

Key invariants
--------------
* A Madrich viewer must have an active ``madrich`` Membership in a
  ``religious_school`` Program.
* A Madrich can owe several templates at once (Story 63) —
  ``assigned_reflections`` lists them, one per active assignment.
  ``madrich_template`` still resolves just the recurring weekly
  self-reflection (TBE 3-2-1 seeded in migration 0037).
* Period is weekly Monday-Sunday per MA1, overridable by
  ``Program.settings['week_boundary_day']`` per Story 61 criterion 6.
* Edit window is the current period per Story 62 criteria 5-6: editable
  while ``period_start <= today <= period_end``; locked once the week
  closes.
* No day-off shortcut per Story 62 criterion 3 — weekly cadence treats
  a missing submission as a gap, not a "day off" state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rest_framework.exceptions import PermissionDenied

from bunk_logs.core.assignment_resolution import assignment_cadence
from bunk_logs.core.assignment_resolution import list_required_assignments_for
from bunk_logs.core.assignment_resolution import resolve_template_for
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.program_scope import operational_memberships_qs
from bunk_logs.core.time_utils import get_current_period
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program
    from bunk_logs.core.models import Reflection
    from bunk_logs.core.models import ReflectionTemplate
    from bunk_logs.core.models import TemplateAssignment


__all__ = [
    "AssignedReflection",
    "ViewerContext",
    "assigned_reflections",
    "current_week_period",
    "enforce_period_edit_window",
    "is_within_current_period",
    "madrich_template",
    "viewer_or_403",
]


ROLE = "madrich"
WEEKLY = "weekly"
ON_DEMAND = "on_demand"


@dataclass(frozen=True)
class ViewerContext:
    """Resolved request context for a Madrich endpoint."""

    person: Person
    organization: Organization
    membership: Membership
    program: Program
    today: date


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org + active Madrich Membership, or raise 403."""
    org = getattr(request, "organization", None)
    if org is None:
        msg = "Organization context required."
        raise PermissionDenied(msg)
    if not request.user.is_authenticated:
        msg = "Authentication required."
        raise PermissionDenied(msg)
    person = Person.objects.filter(user=request.user).first()
    if person is None:
        msg = "Person profile required."
        raise PermissionDenied(msg)
    membership = (
        operational_memberships_qs(
            person, today=get_today(org), role="madrich",
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        msg = "Madrich role required."
        raise PermissionDenied(msg)
    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
        today=get_today(org),
    )


def madrich_template(
    organization: Organization,
    program: Program,
    *,
    viewer: Person | None = None,
    as_of: date | None = None,
) -> ReflectionTemplate | None:
    """Active weekly madrich self-reflection template for the program.

    Resolves via :func:`resolve_template_for` (Step 7_21): returns the
    template bound by an active ``TemplateAssignment`` for the
    (org, program, ``madrich``, ``self``, ``weekly``) tuple, or
    ``None`` when no assignment is active.
    """
    return resolve_template_for(
        organization=organization,
        program=program,
        as_of=as_of or get_today(organization),
        role=ROLE,
        subject_mode="self",
        cadence=WEEKLY,
        viewer=viewer,
    )


@dataclass(frozen=True)
class AssignedReflection:
    """One template a Madrich currently owes, resolved to its live period."""

    assignment: TemplateAssignment
    template: ReflectionTemplate
    cadence: str
    period_start: date
    period_end: date

    @property
    def is_recurring(self) -> bool:
        """False for on-demand forms, which are framed "available to submit"."""
        return self.cadence != ON_DEMAND


def _targets_madrich(template: ReflectionTemplate) -> bool:
    """Same author-role match ``resolve_template_for`` applies.

    Keeps a Director's kitchen-staff or counselor assignment on the same
    program from surfacing on a Madrich's dashboard.
    """
    return template.role == ROLE or ROLE in (template.author_role_filter or [])


def assigned_reflections(ctx: ViewerContext) -> list[AssignedReflection]:
    """Every self-reflection the Madrich currently owes — Story 63.

    One entry per active, required ``TemplateAssignment`` the viewer is in
    the audience for, each carrying the period *its own* cadence puts us
    in. That lets a one-time mid-year form and the recurring weekly 3-2-1
    be open side by side. Ordered weekly-first, then by assignment start
    date, per Story 63 criterion 6.
    """
    entries: list[AssignedReflection] = []
    seen: set[tuple[int, date]] = set()
    for assignment in list_required_assignments_for(
        ctx.person, ctx.organization, ctx.program, ctx.today,
    ):
        template = assignment.template
        if template.subject_mode != "self" or not template.is_active:
            continue
        if not _targets_madrich(template):
            continue
        cadence = assignment_cadence(assignment)
        period_start, period_end = get_current_period(
            cadence, org=ctx.organization, program=ctx.program, anchor=ctx.today,
        )
        # A Director can reach the same person through both a role and an
        # individuals assignment; that's one card, not two.
        key = (template.id, period_start)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            AssignedReflection(
                assignment=assignment,
                template=template,
                cadence=cadence,
                period_start=period_start,
                period_end=period_end,
            ),
        )
    entries.sort(
        key=lambda e: (
            0 if e.cadence == WEEKLY else 1,
            e.assignment.start_date,
            e.template.id,
        ),
    )
    return entries


def current_week_period(
    program: Program, organization: Organization, *, today: date | None = None,
) -> tuple[date, date]:
    """Return the current Monday-Sunday week containing ``today`` (MA1)."""
    return get_current_period(
        "weekly", org=organization, program=program, anchor=today,
    )


def is_within_current_period(reflection: Reflection, today: date) -> bool:
    """Story 62 c5: edit only while the week is still open."""
    return reflection.period_start <= today <= reflection.period_end


def enforce_period_edit_window(reflection: Reflection, today: date) -> None:
    """Raise 403 once the reflection's week has closed (Story 62 c6)."""
    if is_within_current_period(reflection, today):
        return
    msg = "This reflection can no longer be edited (the week has closed)."
    raise PermissionDenied(msg)

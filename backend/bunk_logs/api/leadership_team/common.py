"""Shared helpers for Leadership Team endpoints (Step 7_12).

Mirrors the structure of ``api/unit_head/common.py`` and
``api/camper_care/common.py``: viewer resolution + supervision-driven
team helpers + a thin period resolver for the biweekly LT self
template.

Key invariants
--------------
* Viewer must have an active ``leadership_team`` Membership AND the
  ``program_lead`` capability (the latter is derived in ``Membership.save()``
  via ``ROLE_TO_CAPABILITY`` — checking it here keeps the gate consistent
  if the mapping changes).
* "Teams I supervise" = ``Supervision.target_type='role_in_program'`` rows.
* Period boundaries for non-daily cadences are anchored on the program
  start_date so weekly / biweekly windows stay deterministic across
  re-deploys and DST shifts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from bunk_logs.api.counselor.common import _resolve_template
from bunk_logs.api.counselor.common import enforce_edit_window  # noqa: F401 (re-export)
from bunk_logs.api.counselor.common import is_day_off_answer  # noqa: F401 (re-export)
from bunk_logs.api.counselor.common import is_editable_today  # noqa: F401 (re-export)
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program


__all__ = [
    "LT_SELF_TEMPLATE_SLUG",
    "ViewerContext",
    "assignment_viewer_or_403",
    "leadership_team_self_template",
    "resolve_period",
    "supervised_role_supervisions",
    "supervised_roles",
    "team_membership_ids",
    "team_memberships",
    "viewer_or_403",
]


LT_SELF_TEMPLATE_SLUG = "leadership-team-self-reflection"


@dataclass(frozen=True)
class ViewerContext:
    """Resolved request context for a Leadership Team endpoint."""

    person: Person
    organization: Organization
    membership: Membership
    program: Program
    today: date


def assignment_viewer_or_403(request) -> ViewerContext:
    """Like ``viewer_or_403`` but also accepts ``admin`` capability (decision FA7).

    Used exclusively by the assignments endpoints so the wider gate doesn't
    silently apply to other LT surfaces.
    """
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
        Membership.objects.filter(
            person=person,
            capability__in=["program_lead", "admin"],
            is_active=True,
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        msg = "Leadership Team or Admin role required."
        raise PermissionDenied(msg)
    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
        today=get_today(org),
    )


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org + active LT Membership, or raise 403.

    LT endpoints require all of: organization context, an authenticated
    user, a Person profile in that org, and at least one active
    ``leadership_team`` Membership. We also defensively assert the
    derived ``program_lead`` capability so a mis-seeded Membership row
    that lost its mapping doesn't quietly grant LT access.
    """
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
        Membership.objects.filter(
            person=person, role="leadership_team", is_active=True,
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    if membership is None or membership.capability != "program_lead":
        msg = "Leadership Team role required."
        raise PermissionDenied(msg)
    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
        today=get_today(org),
    )


# ---------------------------------------------------------------------------
# Supervised teams (Stories 45 / 46 — LT2 explicit-supervision visibility)
# ---------------------------------------------------------------------------


def supervised_role_supervisions(
    membership: Membership, *, today: date | None = None,
) -> list[Supervision]:
    """Active ``ROLE_IN_PROGRAM`` Supervision rows for the LT viewer.

    Each row maps the LT to one (role, program) pair; multiple rows
    cover multiple teams. We order by target_role so the per-team list
    on the dashboard has a deterministic sort tie-breaker (after the
    badge-priority sort that the dashboard applies).
    """
    return list(
        Supervision.objects.active(today=today)
        .for_supervisor(membership)
        .filter(target_type=Supervision.TargetType.ROLE_IN_PROGRAM)
        .select_related("target_program")
        .order_by("target_role"),
    )


def supervised_roles(
    membership: Membership, *, today: date | None = None,
) -> list[tuple[str, int]]:
    """List of ``(target_role, target_program_id)`` pairs."""
    return [
        (s.target_role, s.target_program_id)
        for s in supervised_role_supervisions(membership, today=today)
    ]


def team_memberships(
    membership: Membership, target_role: str, *, today: date | None = None,
):
    """Memberships forming the team for ``target_role`` (Story 46 c1)."""
    return (
        Supervision.objects.team_members(membership, target_role=target_role, today=today)
        .select_related("person", "program")
        .order_by("person__last_name", "person__first_name")
    )


def team_membership_ids(
    membership: Membership, target_role: str, *, today: date | None = None,
) -> set[int]:
    return set(
        team_memberships(membership, target_role, today=today).values_list("id", flat=True),
    )


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


def leadership_team_self_template(
    organization: Organization, program: Program,
) -> ReflectionTemplate | None:
    """Active LT self-reflection template, org-shadowing-global.

    Picks the template targeting role=``leadership_team`` with
    ``subject_mode='self'``. The cadence is whatever the org/program has
    configured — default biweekly (see seed migration 0034) but
    overridable per program (Story 50 c2). The org-shadow resolver
    inherits the highest-version active row.
    """
    qs = ReflectionTemplate.all_objects.filter(
        Q(role="leadership_team") | Q(author_role_filter__contains=["leadership_team"]),
        subject_mode="self",
    )
    return _resolve_template(
        qs, organization=organization, program_type=program.program_type,
    )


# ---------------------------------------------------------------------------
# Period resolution (Story 50 — cadence-driven period boundaries)
# ---------------------------------------------------------------------------


def resolve_period(
    template: ReflectionTemplate, *, anchor: date, program: Program,
) -> tuple[date, date]:
    """Return ``(period_start, period_end)`` for ``anchor`` under a cadence.

    * ``daily``: a single day.
    * ``weekly``: Monday-anchored week containing ``anchor``.
    * ``biweekly``: 14-day chunks anchored on ``program.start_date``;
      falls back to a Monday-anchored fortnight if no program start.
    * ``monthly``: calendar month containing ``anchor``.
    * ``on_demand``: degenerate single-day window.

    Deliberately deterministic so the edit-window check
    (``period_start <= today <= period_end``) is consistent for any
    viewer reading the same template at the same moment.
    """
    cadence = (template.cadence or "daily").lower()
    if cadence in ("daily", "on_demand"):
        return anchor, anchor
    if cadence == "weekly":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if cadence == "biweekly":
        ref = program.start_date if (program and program.start_date) else (
            anchor - timedelta(days=anchor.weekday())
        )
        delta_days = (anchor - ref).days
        # Integer-floor toward the prior fortnight boundary even when
        # anchor predates ref (negative delta).
        period_index = delta_days // 14
        start = ref + timedelta(days=period_index * 14)
        return start, start + timedelta(days=13)
    if cadence == "monthly":
        start = anchor.replace(day=1)
        # Last day = first of next month minus 1.
        if start.month == 12:
            next_first = start.replace(year=start.year + 1, month=1)
        else:
            next_first = start.replace(month=start.month + 1)
        return start, next_first - timedelta(days=1)
    # Unknown cadence — fail safe to single-day window.
    return anchor, anchor


def is_within_period(reflection_period_start: date, reflection_period_end: date,
                     today: date) -> bool:
    """Convenience: whether ``today`` falls within the reflection's period."""
    return reflection_period_start <= today <= reflection_period_end

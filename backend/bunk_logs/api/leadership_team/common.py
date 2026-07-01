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

from rest_framework.exceptions import PermissionDenied

from bunk_logs.api.counselor.common import enforce_edit_window  # noqa: F401 (re-export)
from bunk_logs.api.counselor.common import is_day_off_answer  # noqa: F401 (re-export)
from bunk_logs.api.counselor.common import is_editable_today  # noqa: F401 (re-export)
from bunk_logs.core.assignment_resolution import resolve_template_for
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
from bunk_logs.core.permissions.super_admin import is_super_admin
from bunk_logs.core.program_scope import operational_memberships_qs
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program


__all__ = [
    "LT_SELF_TEMPLATE_SLUG",
    "ViewerContext",
    "admin_only_or_403",
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
    """Resolved request context for a Leadership Team endpoint.

    ``person`` / ``membership`` / ``program`` may be ``None`` on the
    admin-only surfaces when the caller is a Django super admin
    (``is_staff`` / ``is_superuser``) with no admin ``Membership`` — those
    surfaces only need ``organization``. The personal LT surfaces
    (``viewer_or_403``) always resolve a real ``membership``.
    """

    person: Person | None
    organization: Organization
    membership: Membership | None
    program: Program | None
    today: date


def admin_only_or_403(request) -> ViewerContext:
    """Resolve viewer context, requiring an active ``admin`` Membership.

    Gate for the template-builder + assignment surfaces. Per the
    consolidation decision, only org admins create and manage templates
    and assignments; Leadership Team members no longer have write access
    to that surface (they keep their own dashboards, team views, and
    self-reflection, which continue to use ``viewer_or_403``).
    """
    org = getattr(request, "organization", None)
    if org is None:
        msg = "Organization context required."
        raise PermissionDenied(msg)
    if not request.user.is_authenticated:
        msg = "Authentication required."
        raise PermissionDenied(msg)
    person = Person.objects.filter(user=request.user).first()
    membership = None
    if person is not None:
        membership = (
            Membership.objects.filter(
                person=person,
                capability="admin",
                is_active=True,
            )
            .select_related("program", "program__organization")
            .order_by("-created_at")
            .first()
        )
    # Django staff / superusers always have org-admin access, even without an
    # active admin Membership (mirrors ``is_super_admin`` used across the rest
    # of the RBAC — e.g. ``is_org_admin`` and ``reflections_visible_for_user``).
    # These admin-only surfaces only read ``ctx.organization``; the personal LT
    # surfaces keep requiring a real membership via ``viewer_or_403``.
    if membership is None and is_super_admin(request.user):
        return ViewerContext(
            person=person,
            organization=org,
            membership=None,
            program=None,
            today=get_today(org),
        )
    if person is None:
        msg = "Person profile required."
        raise PermissionDenied(msg)
    if membership is None:
        msg = "Admin role required."
        raise PermissionDenied(msg)
    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
        today=get_today(org),
    )


def assignment_viewer_or_403(request) -> ViewerContext:
    """Admin-only gate for the assignments surface.

    Previously accepted ``program_lead`` (Leadership Team) as well, but the
    builder surface is now admin-only (consolidation decision). Retained as a
    thin alias of :func:`admin_only_or_403` so existing import sites keep
    working.
    """
    return admin_only_or_403(request)


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org + active Membership, or raise 403.

    Accepts either a ``leadership_team`` member (``program_lead``
    capability) or an ``admin`` member. The broader admin gate applies
    to all LT surfaces — templates, responses, dashboard, exports, etc.
    — consistent with the same widening already in place for
    ``assignment_viewer_or_403`` (decision FA7).
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
        operational_memberships_qs(
            person,
            today=get_today(org),
            capability__in=["program_lead", "admin"],
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    # Super admins whose only admin/program_lead membership sits in a
    # non-operational (e.g. ended-session) program still get in — admin is an
    # org-wide role, not session-scoped. We keep a real membership so the
    # personal LT surfaces that read ``ctx.membership`` / ``ctx.program``
    # continue to work.
    if membership is None and is_super_admin(request.user):
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
    organization: Organization,
    program: Program,
    *,
    viewer: Person | None = None,
    as_of: date | None = None,
) -> ReflectionTemplate | None:
    """Active LT self-reflection template.

    Resolves via :func:`resolve_template_for` (Step 7_21): returns the
    template bound by an active ``TemplateAssignment`` for the
    (org, program, ``leadership_team``, ``self``) tuple. Cadence is
    deliberately NOT constrained here — LT cadence is per-program
    (Story 50 c2), default biweekly, but the assignment's
    ``cadence_override`` may surface a weekly/monthly variant without
    requiring a different template.
    """
    return resolve_template_for(
        organization=organization,
        program=program,
        as_of=as_of or get_today(organization),
        role="leadership_team",
        subject_mode="self",
        viewer=viewer,
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

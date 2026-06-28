"""Shared helpers for Camper Care endpoints (Step 7_8).

Mirrors the structure of ``api/unit_head/common.py`` so reading either
module reveals the same shape: viewer resolution + caseload helpers +
small projections shared across endpoints. Camper Care's caseload is
``Supervision.target_type='bunk'`` rather than the UH's per-counselor
target, so we reuse :func:`Supervision.objects.caseload_campers` and
add a thin ``caseload_bunks`` wrapper for the dashboard tree.

Per CC7 (Story 22 decision), Camper Care orders are team-shared across
the program -- *not* caseload-scoped -- so the order helper here scopes
by program rather than by supervised bunks.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from operator import or_
from typing import TYPE_CHECKING
from typing import Literal

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from bunk_logs.api.counselor.common import enforce_edit_window  # noqa: F401 (re-export)
from bunk_logs.api.counselor.common import is_day_off_answer  # noqa: F401 (re-export)
from bunk_logs.api.counselor.common import is_editable_today  # noqa: F401 (re-export)
from bunk_logs.core.assignment_resolution import resolve_template_for
from bunk_logs.core.managers import _caseload_bunk_ids_for_membership
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Person
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
from bunk_logs.core.permissions import is_super_admin
from bunk_logs.core.program_scope import operational_memberships_qs
from bunk_logs.core.program_scope import operational_program_q
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program


CC_SELF_TEMPLATE_SLUGS = (
    "camper-care-self-reflection",
    "wellness-self-reflection",
)


__all__ = [
    "CC_SELF_TEMPLATE_SLUGS",
    "OrdersScope",
    "OrdersViewerContext",
    "ViewerContext",
    "camper_care_self_template",
    "caseload_bunk_ids",
    "caseload_bunks",
    "caseload_bunks_with_unit",
    "caseload_camper_ids",
    "caseload_campers",
    "orders_base_queryset",
    "orders_viewer_or_403",
    "resolve_orders_viewer",
    "viewer_or_403",
]

OrdersScope = Literal["team", "unit", "viewer"]


@dataclass(frozen=True)
class ViewerContext:
    """Resolved request context for a Camper Care endpoint."""

    person: Person
    organization: Organization
    membership: Membership
    program: Program
    today: date


@dataclass(frozen=True)
class OrdersViewerContext(ViewerContext):
    """Viewer context plus the orders-workspace visibility scope."""

    scope: OrdersScope


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org + active Camper Care Membership, or 403.

    Camper Care endpoints require all of: organization context, an
    authenticated user, a Person profile in that org, and at least one
    active ``camper_care`` Membership. When a user has CC memberships in
    multiple programs we pick the newest by ``created_at`` -- a
    program-picker UI is out of scope for Tier 1.
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
            person, today=get_today(org), role="camper_care",
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        msg = "Camper Care role required."
        raise PermissionDenied(msg)
    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
        today=get_today(org),
    )


def resolve_orders_viewer(request) -> OrdersViewerContext:
    """Resolve viewer + scope for the Camper Care orders workspace.

    * ``team`` — Camper Care staff and org admins see the full queue and
      may transition orders. Admins are org-wide; Camper Care is program-wide.
    * ``unit`` — Unit Heads see orders for campers / counselors on bunks they
      supervise (read-only).
    * ``viewer`` — Counselors see only orders they submitted (read-only).
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

    memberships = Membership.objects.filter(
        person=person, is_active=True, program__organization=org,
    ).select_related("program", "program__organization")

    team_qs = memberships
    if not is_super_admin(request.user):
        team_qs = memberships.filter(role__in=("camper_care", "admin"))
    team_membership = team_qs.filter(role="camper_care").order_by("-created_at").first()
    if team_membership is None:
        team_membership = team_qs.filter(role="admin").order_by("-created_at").first()
    if team_membership is None and is_super_admin(request.user):
        team_membership = memberships.order_by("-created_at").first()
    if team_membership is not None:
        return OrdersViewerContext(
            person=person,
            organization=org,
            membership=team_membership,
            program=team_membership.program,
            today=get_today(org),
            scope="team",
        )

    uh_membership = memberships.filter(role="unit_head").order_by("-created_at").first()
    if uh_membership is not None:
        return OrdersViewerContext(
            person=person,
            organization=org,
            membership=uh_membership,
            program=uh_membership.program,
            today=get_today(org),
            scope="unit",
        )

    counselor_membership = memberships.filter(role="counselor").order_by("-created_at").first()
    if counselor_membership is not None:
        return OrdersViewerContext(
            person=person,
            organization=org,
            membership=counselor_membership,
            program=counselor_membership.program,
            today=get_today(org),
            scope="viewer",
        )

    msg = "Active membership required."
    raise PermissionDenied(msg)


def orders_viewer_or_403(request) -> OrdersViewerContext:
    """Backward-compatible alias for :func:`resolve_orders_viewer`."""
    return resolve_orders_viewer(request)


def orders_base_queryset(ctx: OrdersViewerContext):
    """Base queryset of orders visible in the workspace for ``ctx``."""
    if ctx.scope == "team":
        if ctx.membership.role == "admin":
            return Order.objects.filter(organization=ctx.organization)
        return Order.objects.filter(program=ctx.program)
    if ctx.scope == "unit":
        return Order.objects.filter(program=ctx.program).filter(
            _unit_head_orders_q(ctx.membership, today=ctx.today),
        )
    return Order.objects.filter(
        program=ctx.program,
        submitted_by=ctx.membership,
    )


def _unit_head_orders_q(membership: Membership, *, today: date | None) -> Q:
    """Orders tied to bunks a Unit Head supervises."""
    from bunk_logs.api.unit_head.bunk_dashboard import _counselor_membership_ids_for_bunk
    from bunk_logs.api.unit_head.common import supervised_bunk_ids

    bunk_ids = supervised_bunk_ids(membership, today=today)
    if not bunk_ids:
        return Q(pk__in=[])

    camper_ids: set[int] = set()
    counselor_membership_ids: set[int] = set()
    for bunk in AssignmentGroup.all_objects.filter(pk__in=bunk_ids, is_active=True):
        camper_ids.update(bunk_camper_ids(bunk))
        counselor_membership_ids.update(_counselor_membership_ids_for_bunk(bunk))

    parts: list[Q] = [Q(submitted_from_bunk_id__in=bunk_ids)]
    if camper_ids:
        parts.append(Q(subject_id__in=camper_ids))
    if counselor_membership_ids:
        parts.append(Q(submitted_by_id__in=counselor_membership_ids))
    return reduce(or_, parts)


# ---------------------------------------------------------------------------
# Caseload (Story 18 + CC1)
# ---------------------------------------------------------------------------


def caseload_bunks(
    membership: Membership, *, today: date | None = None,
) -> list[AssignmentGroup]:
    """Active bunk AssignmentGroups on the Camper Care member's caseload.

    Combines direct BUNK supervisions and expanded ASSIGNMENT_GROUP
    supervisions (unit/division targets resolved to child bunks) so that
    a CC member assigned to a unit sees all bunks within that unit.
    Ordered alphabetically for a stable tie-breaker after badge sort.
    """
    bunk_ids = _caseload_bunk_ids_for_membership(
        Supervision.objects, membership, today=today,
    )
    if not bunk_ids:
        return []
    if today is None:
        today = get_today(membership.program.organization)
    return list(
        AssignmentGroup.objects.filter(id__in=bunk_ids, is_active=True)
        .filter(operational_program_q(today=today, prefix="program"))
        .select_related("parent", "organization")
        .order_by("name"),
    )


def caseload_bunks_with_unit(
    membership: Membership, *, today: date | None = None,
) -> dict[int | None, list[AssignmentGroup]]:
    """Group caseload bunks by their parent ``unit`` AssignmentGroup id.

    Story 18 wants the caseload rendered as Unit -> Bunks. Bunks with
    no parent unit fall under ``None``; the dashboard view treats that
    bucket as an "Unassigned" section so they still render.
    """
    out: dict[int | None, list[AssignmentGroup]] = {}
    for bunk in caseload_bunks(membership, today=today):
        out.setdefault(bunk.parent_id, []).append(bunk)
    return out


def caseload_campers(
    membership: Membership, *, today: date | None = None,
):
    """Pass-through to the shipped Supervision.caseload_campers helper.

    Re-exposed under the api/camper_care namespace so callers don't
    need to import from ``core.managers`` directly.
    """
    return Supervision.objects.caseload_campers(membership, today=today)


def caseload_camper_ids(
    membership: Membership, *, today: date | None = None,
) -> set[int]:
    """Person IDs of campers on the viewer's caseload (today)."""
    return set(caseload_campers(membership, today=today).values_list("id", flat=True))


def bunk_camper_ids(bunk: AssignmentGroup) -> list[int]:
    """Active camper Person IDs assigned to a bunk as ``subject``.

    Mirrors :func:`api.unit_head.common.bunk_camper_ids` so the
    dashboard payload shape stays consistent across UH and CC.
    """
    return list(
        AssignmentGroupMembership.objects.filter(
            group=bunk, role_in_group="subject", is_active=True,
        )
        .order_by("person__last_name", "person__first_name")
        .values_list("person_id", flat=True),
    )


def caseload_bunk_ids(
    membership: Membership, *, today: date | None = None,
) -> set[int]:
    """Bunk IDs on the Camper Care member's caseload (today).

    Equivalent to ``supervised_bunk_ids`` for UH — used by write
    endpoints that need to validate user-supplied bunk IDs against the
    viewer's authority (e.g. ``bunk_concerns_bunks`` in a CC
    self-reflection answer payload).
    """
    return {b.id for b in caseload_bunks(membership, today=today)}


def camper_care_self_template(
    organization: Organization,
    program: Program,
    *,
    viewer: Person | None = None,
    as_of: date | None = None,
) -> ReflectionTemplate | None:
    """Daily Camper Care self-reflection template.

    Resolves via :func:`resolve_template_for` (Step 7_21): returns the
    template bound by an active ``TemplateAssignment`` for the
    (org, program, ``camper_care``, ``self``, ``daily``) tuple, or
    ``None`` when no assignment is active (dashboard placeholder).
    """
    return resolve_template_for(
        organization=organization,
        program=program,
        as_of=as_of or get_today(organization),
        role="camper_care",
        subject_mode="self",
        cadence="daily",
        viewer=viewer,
    )

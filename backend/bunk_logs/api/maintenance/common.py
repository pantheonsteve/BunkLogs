"""Shared helpers for Maintenance staff endpoints (Step 7_10)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.permissions import is_super_admin
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

# Queue audiences. ``team`` = maintenance/admin with the full program queue and
# transition actions; ``viewer`` = any other org member, who sees the same full
# program queue but read-only (no transition actions).
QueueScope = Literal["team", "viewer"]


@dataclass(frozen=True)
class ViewerContext:
    """Resolved request context for a Maintenance endpoint."""

    person: Person
    organization: Organization
    membership: Membership
    program: Program
    today: date


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org + active Maintenance/Admin Membership, or 403.

    Maintenance endpoints require all of: organization context, authenticated
    user, a Person profile, and at least one active ``maintenance`` or ``admin``
    Membership. Super admins bypass the role gate but still need a Person and
    an organization context.
    """
    org = getattr(request, "organization", None)
    if org is None:
        msg = "Organization context required."
        raise PermissionDenied(msg)
    if not request.user.is_authenticated:
        msg = "Authentication required."
        raise PermissionDenied(msg)
    person = Person.all_objects.filter(user=request.user).first()
    if person is None:
        msg = "Person profile required."
        raise PermissionDenied(msg)

    qs = Membership.objects.filter(
        person=person, is_active=True,
    ).select_related("program", "program__organization")

    if not is_super_admin(request.user):
        qs = qs.filter(role__in=("maintenance", "admin"))

    membership = qs.order_by("-created_at").first()
    if membership is None:
        msg = "Maintenance role required."
        raise PermissionDenied(msg)

    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
        today=get_today(org),
    )


def resolve_queue_viewer(request) -> tuple[ViewerContext, QueueScope]:
    """Resolve the queue viewer and their scope.

    Maintenance/admin/super-admin members get ``team`` scope (the full program
    queue with actions). Any other authenticated org member with an active
    Membership gets ``viewer`` scope — the same full program queue, but
    read-only. Transition/note/detail endpoints stay team-only via
    :func:`viewer_or_403`.
    """
    org = getattr(request, "organization", None)
    if org is None:
        msg = "Organization context required."
        raise PermissionDenied(msg)
    if not request.user.is_authenticated:
        msg = "Authentication required."
        raise PermissionDenied(msg)
    person = Person.all_objects.filter(user=request.user).first()
    if person is None:
        msg = "Person profile required."
        raise PermissionDenied(msg)

    memberships = Membership.objects.filter(
        person=person, is_active=True,
    ).select_related("program", "program__organization")

    team_qs = memberships
    if not is_super_admin(request.user):
        team_qs = memberships.filter(role__in=("maintenance", "admin"))
    team_membership = team_qs.order_by("-created_at").first()
    if team_membership is not None:
        return ViewerContext(
            person=person,
            organization=org,
            membership=team_membership,
            program=team_membership.program,
            today=get_today(org),
        ), "team"

    viewer_membership = memberships.order_by("-created_at").first()
    if viewer_membership is None:
        msg = "Active membership required."
        raise PermissionDenied(msg)
    return ViewerContext(
        person=person,
        organization=org,
        membership=viewer_membership,
        program=viewer_membership.program,
        today=get_today(org),
    ), "viewer"


def is_org_admin_membership(membership: Membership) -> bool:
    """True when ``membership`` is an active org-admin role (not maintenance)."""
    return membership.role == "admin"


def ticket_scope_q(ctx: ViewerContext) -> Q:
    """Q filter for maintenance tickets visible to ``ctx``.

    Maintenance staff see their program queue. Org admins see every ticket in
    the organization (they may hold admin Memberships on older programs while
    counselors submit to the current one). Everyone else is program-scoped.
    """
    if is_org_admin_membership(ctx.membership):
        return Q(organization=ctx.organization)
    return Q(program=ctx.program)


def tickets_for_viewer(ctx: ViewerContext):
    """Base queryset of tickets in scope for queue/detail/notes."""
    return MaintenanceTicket.objects.filter(ticket_scope_q(ctx))

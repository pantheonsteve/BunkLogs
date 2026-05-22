"""Shared helpers for Maintenance staff endpoints (Step 7_10)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rest_framework.exceptions import PermissionDenied

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.permissions import is_super_admin
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date


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

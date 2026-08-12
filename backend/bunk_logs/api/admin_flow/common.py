"""Shared helpers for Admin Flow endpoints (Step 7_13).

Mirrors the structure of the per-role ``common.py`` modules. The viewer
context resolves the requesting user to an active admin Membership in
the request's organization context, or raises 403. Super Admins
(``is_staff`` or ``is_superuser``) are also accepted; in that case
``membership`` is ``None`` so dashboard helpers know not to scope by it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rest_framework.exceptions import PermissionDenied

from bunk_logs.core.identity import person_for_user
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.permissions import is_super_admin
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization


@dataclass(frozen=True)
class AdminContext:
    """Resolved request context for any admin-namespace endpoint."""

    person: Person | None
    organization: Organization
    membership: Membership | None
    today: date
    is_super_admin: bool


def viewer_or_403(request) -> AdminContext:
    """Resolve admin-context for ``request`` or raise 403.

    Order of checks:

    1. Organization context must be set by ``OrganizationMiddleware`` --
       missing header / unknown subdomain bails out immediately.
    2. User must be authenticated.
    3. Either Super Admin OR an active ``role='admin'`` Membership in
       the active organization grants access. Super Admins get a
       ``None`` membership in the returned context; tenant Admins get
       their actual Membership row so audit helpers can record it.
    """
    org = getattr(request, "organization", None)
    if org is None:
        msg = "Organization context required."
        raise PermissionDenied(msg)
    if not request.user.is_authenticated:
        msg = "Authentication required."
        raise PermissionDenied(msg)
    super_admin = is_super_admin(request.user)
    person = person_for_user(request.user, organization=org)
    membership = None
    if person is not None:
        membership = (
            Membership.objects.filter(
                person=person, role="admin", is_active=True,
            )
            .select_related("program")
            .order_by("-created_at")
            .first()
        )
    if not super_admin and membership is None:
        msg = "Admin role required."
        raise PermissionDenied(msg)
    return AdminContext(
        person=person,
        organization=org,
        membership=membership,
        today=get_today(org),
        is_super_admin=super_admin,
    )


def resolve_current_program_for_role(
    organization: Organization,
    role: str,
    today: date,
    *,
    program_type: str | None = None,
) -> Program | None:
    """Pick the one program that's the current home for a role's roster.

    Orgs can end up with more than one ``is_active`` program of the same
    type at once (e.g. next year's cohort created ahead of this year's
    end date, or a scratch/dev program left lying around) -- picking
    "whichever started most recently" then silently shows an empty or
    wrong roster. Instead: prefer whichever active program's date range
    actually contains ``today``, and among those, the one with the most
    active ``role`` memberships (the one people are actually using).
    Falls back to the latest-starting program when none have started
    yet (e.g. a roster imported ahead of the program's start date).
    """
    programs = Program.all_objects.filter(organization=organization, is_active=True)
    if program_type:
        programs = programs.filter(program_type=program_type)
    programs = list(programs)
    if not programs:
        return None

    def _member_count(program: Program) -> int:
        return Membership.all_objects.filter(
            program=program, role=role, is_active=True,
        ).count()

    live = [p for p in programs if p.start_date <= today <= p.end_date]
    pool = live or programs
    return max(pool, key=lambda p: (_member_count(p), p.start_date))

"""Role resolution for the unified bunk dashboard.

A single endpoint (``GET /api/v1/dashboards/bunks/<bunk_id>/``) serves
Counselor, Camper Care, Unit Head, Leadership Team, and Org Admin
viewers. Per-role gating lives here so the view stays focused on
payload assembly. Precedence (first match wins) is admin >
leadership_team > unit_head > camper_care > counselor.

The resolver loads the target ``AssignmentGroup`` (bunk) up front
because the access check needs to know its ``program`` — Supervision
rows are program-scoped, so a UH/CC/counselor Membership only counts
when it belongs to the bunk's own program.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rest_framework.exceptions import PermissionDenied

from bunk_logs.api.camper_care.common import caseload_bunks
from bunk_logs.api.counselor.common import COUNSELOR_ROLES
from bunk_logs.api.unit_head.common import supervised_bunk_ids
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program


# Precedence order for role resolution. The first matching role wins.
ROLE_PRECEDENCE: tuple[str, ...] = (
    "admin",
    "leadership_team",
    "unit_head",
    "camper_care",
    "counselor",
)

_ACCESS_DENIED_MESSAGE = "You do not have access to this bunk."


@dataclass(frozen=True)
class BunkViewerContext:
    """Resolved request context for the unified bunk dashboard."""

    role: str
    person: Person | None
    organization: Organization
    program: Program
    today: date
    bunk: AssignmentGroup
    membership: Membership | None


def resolve_bunk_dashboard_context(request, bunk_id: int) -> BunkViewerContext:
    """Resolve viewer + role for ``bunk_id`` or raise ``PermissionDenied``.

    Roles are evaluated in :data:`ROLE_PRECEDENCE`. Admin and Leadership
    Team grant org-wide access (any active Membership in the org); UH,
    CC, and Counselor each require an active program-scoped Membership
    plus a supervision/authorship link to the specific bunk.

    Superusers without a ``Person`` profile resolve as admin so Django
    superadmins can hit the endpoint for debugging without a tenant
    profile. Visibility filters inside
    :func:`build_bunk_dashboard_payload` already handle the ``None``
    case via ``request.user``.

    On any failure (missing org context, no Person, bunk not found,
    no qualifying role) we raise the same generic 403 to avoid leaking
    bunk existence across orgs.
    """
    organization = getattr(request, "organization", None)
    if organization is None:
        msg = "Organization context required."
        raise PermissionDenied(msg)
    if not request.user.is_authenticated:
        msg = "Authentication required."
        raise PermissionDenied(msg)

    person = Person.objects.filter(user=request.user).first()
    if person is None and not request.user.is_superuser:
        raise PermissionDenied(_ACCESS_DENIED_MESSAGE)

    bunk = (
        AssignmentGroup.all_objects.filter(
            id=bunk_id,
            group_type="bunk",
            is_active=True,
            organization=organization,
        )
        .select_related("parent", "program")
        .first()
    )
    if bunk is None:
        raise PermissionDenied(_ACCESS_DENIED_MESSAGE)

    today = get_today(organization)
    program = bunk.program

    # 1. Admin — superuser OR active admin Membership anywhere in this org.
    if request.user.is_superuser or (
        person is not None
        and Membership.objects.filter(
            person=person, role="admin", is_active=True,
        ).exists()
    ):
        return BunkViewerContext(
            role="admin",
            person=person,
            organization=organization,
            program=program,
            today=today,
            bunk=bunk,
            membership=None,
        )

    # Below here every role requires a Person profile.
    if person is None:
        raise PermissionDenied(_ACCESS_DENIED_MESSAGE)

    # 2. Leadership Team — any active LT Membership in the org grants
    # read access to every bunk (org-wide reviewer role).
    lt_membership = (
        Membership.objects.filter(
            person=person, role="leadership_team", is_active=True,
        )
        .select_related("program")
        .first()
    )
    if lt_membership is not None:
        return BunkViewerContext(
            role="leadership_team",
            person=person,
            organization=organization,
            program=program,
            today=today,
            bunk=bunk,
            membership=lt_membership,
        )

    # 3. Unit Head — active UH Membership in the bunk's program that
    # supervises this bunk via the Supervision tree.
    for uh_membership in Membership.objects.filter(
        person=person, role="unit_head", is_active=True, program=program,
    ):
        if bunk.id in supervised_bunk_ids(uh_membership, today=today):
            return BunkViewerContext(
                role="unit_head",
                person=person,
                organization=organization,
                program=program,
                today=today,
                bunk=bunk,
                membership=uh_membership,
            )

    # 4. Camper Care — bunk must be on the caseload (direct BUNK
    # supervision or expanded ASSIGNMENT_GROUP supervision).
    for cc_membership in Membership.objects.filter(
        person=person, role="camper_care", is_active=True, program=program,
    ):
        caseload_ids = {b.id for b in caseload_bunks(cc_membership, today=today)}
        if bunk.id in caseload_ids:
            return BunkViewerContext(
                role="camper_care",
                person=person,
                organization=organization,
                program=program,
                today=today,
                bunk=bunk,
                membership=cc_membership,
            )

    # 5. Counselor / Junior Counselor — must be an active author on the
    # bunk's AssignmentGroup AND hold a counselor/JC Membership in the
    # bunk's program (the AGM by itself doesn't pin the program).
    if AssignmentGroupMembership.objects.filter(
        person=person, group=bunk, role_in_group="author", is_active=True,
    ).exists():
        counselor_membership = (
            Membership.objects.filter(
                person=person,
                role__in=tuple(COUNSELOR_ROLES),
                is_active=True,
                program=program,
            )
            .first()
        )
        if counselor_membership is not None:
            return BunkViewerContext(
                role="counselor",
                person=person,
                organization=organization,
                program=program,
                today=today,
                bunk=bunk,
                membership=counselor_membership,
            )

    raise PermissionDenied(_ACCESS_DENIED_MESSAGE)

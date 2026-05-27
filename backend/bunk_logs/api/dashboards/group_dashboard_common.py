"""Role resolution for the unified per-group dashboard.

A single endpoint (``GET /api/v1/dashboards/group/<group_id>/``)
serves Counselor, Camper Care, Unit Head, Leadership Team, Org Admin,
and TBE Madrich/Faculty viewers across every ``AssignmentGroup``
type (bunk, unit, division, classroom). Per-role gating lives here so
the view stays focused on payload assembly. Precedence (first match
wins) is admin > leadership_team > unit_head > camper_care >
counselor > classroom_author.

The resolver loads the target ``AssignmentGroup`` up front because
the access check needs to know its ``program`` (Supervision rows are
program-scoped) and its ``group_type`` (counselor access is bunk-only;
classroom access is faculty/madrich-only).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rest_framework.exceptions import PermissionDenied

from bunk_logs.api.camper_care.common import caseload_bunk_ids
from bunk_logs.api.counselor.common import COUNSELOR_ROLES
from bunk_logs.api.unit_head.common import supervised_bunk_ids
from bunk_logs.core.managers import _expand_group_to_bunk_ids
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
# ``classroom_author`` (faculty / madrich AGM author on a classroom)
# is a derived role: there is no single Membership role that owns
# classroom-level access. See the classroom branch in
# :func:`resolve_group_dashboard_context` for the lookup rules.
ROLE_PRECEDENCE: tuple[str, ...] = (
    "admin",
    "leadership_team",
    "unit_head",
    "camper_care",
    "counselor",
    "classroom_author",
)

# Membership roles that, when paired with an AGM ``author`` row on a
# classroom group, grant read access to that classroom's dashboard.
# Faculty + madrich are the TBE counterparts to the camp-side
# counselor role.
CLASSROOM_AUTHOR_ROLES: frozenset[str] = frozenset({"faculty", "madrich"})

_ACCESS_DENIED_MESSAGE = "You do not have access to this group."


@dataclass(frozen=True)
class GroupViewerContext:
    """Resolved request context for the unified group dashboard."""

    role: str
    person: Person | None
    organization: Organization
    program: Program
    today: date
    group: AssignmentGroup
    membership: Membership | None


def resolve_group_dashboard_context(
    request, group_id: int,
) -> GroupViewerContext:
    """Resolve viewer + role for ``group_id`` or raise ``PermissionDenied``.

    Roles are evaluated in :data:`ROLE_PRECEDENCE`. Admin and Leadership
    Team grant org-wide access. UH and CC each require an active
    program-scoped Membership plus a supervision link to at least one
    leaf bunk under the group (``_expand_group_to_bunk_ids``). Counselor
    is bunk-only (no group-level views). Classroom is faculty/madrich
    AGM-author only.

    Superusers without a ``Person`` profile resolve as admin so Django
    superadmins can hit the endpoint for debugging without a tenant
    profile. Per-payload visibility filters (``reflections_visible_for_user``,
    ``notes_visible_to``) already handle ``request.user`` without a Person.

    On any failure (missing org context, no Person, group not found,
    no qualifying role) we raise the same generic 403 so cross-org
    callers can't probe for group existence.
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

    group = (
        AssignmentGroup.all_objects.filter(
            id=group_id,
            is_active=True,
            organization=organization,
        )
        .select_related("parent", "program")
        .first()
    )
    if group is None:
        raise PermissionDenied(_ACCESS_DENIED_MESSAGE)

    today = get_today(organization)
    program = group.program

    # 1. Admin — superuser OR active admin Membership anywhere in this org.
    if request.user.is_superuser or (
        person is not None
        and Membership.objects.filter(
            person=person, role="admin", is_active=True,
        ).exists()
    ):
        return GroupViewerContext(
            role="admin",
            person=person,
            organization=organization,
            program=program,
            today=today,
            group=group,
            membership=None,
        )

    # Below here every role requires a Person profile.
    if person is None:
        raise PermissionDenied(_ACCESS_DENIED_MESSAGE)

    # 2. Leadership Team — any active LT Membership in the org grants
    # read access to every group (org-wide reviewer role).
    lt_membership = (
        Membership.objects.filter(
            person=person, role="leadership_team", is_active=True,
        )
        .select_related("program")
        .first()
    )
    if lt_membership is not None:
        return GroupViewerContext(
            role="leadership_team",
            person=person,
            organization=organization,
            program=program,
            today=today,
            group=group,
            membership=lt_membership,
        )

    # For UH and CC, expand the requested group to its descendant bunks
    # once and intersect that with the viewer's supervised/caseload set.
    # An empty intersection means no access regardless of group_type.
    group_leaf_bunk_ids = _expand_group_to_bunk_ids(group)

    # 3. Unit Head — active UH Membership in the group's program whose
    # supervised bunks overlap with this group's leaves.
    for uh_membership in Membership.objects.filter(
        person=person, role="unit_head", is_active=True, program=program,
    ):
        if supervised_bunk_ids(uh_membership, today=today) & group_leaf_bunk_ids:
            return GroupViewerContext(
                role="unit_head",
                person=person,
                organization=organization,
                program=program,
                today=today,
                group=group,
                membership=uh_membership,
            )

    # 4. Camper Care — caseload bunks overlap with the group's leaves.
    for cc_membership in Membership.objects.filter(
        person=person, role="camper_care", is_active=True, program=program,
    ):
        if caseload_bunk_ids(cc_membership, today=today) & group_leaf_bunk_ids:
            return GroupViewerContext(
                role="camper_care",
                person=person,
                organization=organization,
                program=program,
                today=today,
                group=group,
                membership=cc_membership,
            )

    # 5. Counselor / Junior Counselor — bunk-only. Counselors don't get
    # rollup access to a parent unit/division (would expose peers'
    # bunks they don't author).
    if group.group_type == "bunk" and AssignmentGroupMembership.objects.filter(
        person=person, group=group, role_in_group="author", is_active=True,
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
            return GroupViewerContext(
                role="counselor",
                person=person,
                organization=organization,
                program=program,
                today=today,
                group=group,
                membership=counselor_membership,
            )

    # 6. Classroom author (TBE) — faculty or madrich AGM ``author`` on
    # the classroom plus any active Membership in the classroom's
    # program. There is no parallel for camp groups; counselors are
    # handled above.
    if group.group_type == "classroom" and AssignmentGroupMembership.objects.filter(
        person=person, group=group, role_in_group="author", is_active=True,
    ).exists():
        classroom_membership = (
            Membership.objects.filter(
                person=person,
                role__in=tuple(CLASSROOM_AUTHOR_ROLES),
                is_active=True,
                program=program,
            )
            .first()
        )
        if classroom_membership is not None:
            return GroupViewerContext(
                role="classroom_author",
                person=person,
                organization=organization,
                program=program,
                today=today,
                group=group,
                membership=classroom_membership,
            )

    raise PermissionDenied(_ACCESS_DENIED_MESSAGE)

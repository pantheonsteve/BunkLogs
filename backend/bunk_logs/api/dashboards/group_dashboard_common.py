"""Role resolution for the unified per-group dashboard.

A single endpoint (``GET /api/v1/dashboards/group/<group_id>/``)
serves Counselor, Camper Care, Unit Head, Leadership Team, Org Admin,
and TBE Madrich/Faculty viewers across every ``AssignmentGroup``
type (bunk, unit, division, classroom). Per-role gating lives here so
the view stays focused on payload assembly. Precedence (first match
wins) is admin > leadership_team > unit_head > camper_care >
group author. Author access is whoever the org's group-type config
lists as an author for that group, and only on the group they author.
Counselors still get no rollup to a parent unit or division.

The resolver loads the target ``AssignmentGroup`` up front because
the access check needs to know its ``program`` (Supervision rows are
program-scoped) and its ``group_type``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rest_framework.exceptions import PermissionDenied

from bunk_logs.api.camper_care.common import caseload_bunk_ids
from bunk_logs.api.unit_head.common import supervised_bunk_ids
from bunk_logs.core.managers import _expand_group_to_bunk_ids
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.org_config import author_roles_for
from bunk_logs.core.org_config import group_type_config
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program


# Precedence order for role resolution. The first matching role wins.
# ``counselor`` and ``classroom_author`` are the viewer-role strings the
# bunk and classroom payloads already branch on. Which membership roles
# earn them comes from the org's group-type config, not a hardcoded list.
ROLE_PRECEDENCE: tuple[str, ...] = (
    "admin",
    "leadership_team",
    "unit_head",
    "camper_care",
    "counselor",
    "classroom_author",
)

_ACCESS_DENIED_MESSAGE = "You do not have access to this group."


def _author_viewer_role(group_type: str, membership_role: str) -> str:
    """Viewer-role string for an author grant. Bunk and classroom stay stable."""
    if group_type == "classroom":
        return "classroom_author"
    if group_type == "bunk":
        return "counselor"
    return membership_role


def _configured_author_membership(person, group, program, organization):
    """Active author on this group whose role is an author for the group type.

    The authorship row has to be on ``group`` itself. A counselor who
    authors a child bunk does not get the parent.
    """
    if not AssignmentGroupMembership.objects.filter(
        person=person, group=group, role_in_group="author", is_active=True,
    ).exists():
        return None
    author_roles = author_roles_for(organization, group.group_type)
    if not author_roles:
        return None
    return Membership.objects.filter(
        person=person,
        role__in=tuple(author_roles),
        is_active=True,
        program=program,
    ).first()


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
    leaf bunk under the group (``_expand_group_to_bunk_ids``). After
    that, an active author whose membership role is configured as an
    author for this group type may open the group. They do not roll up
    to a parent.

    Superusers without a ``Person`` profile resolve as admin so Django
    superadmins can hit the endpoint for debugging without a tenant
    profile. Per-payload visibility filters (``reflections_visible_for_user``,
    ``reflections_visible_for_user``) already handle ``request.user`` without a Person.

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

    # 5. Configured author — active author on this group whose membership
    # role is an author for the group type. No rollup to parent groups.
    author_membership = _configured_author_membership(
        person, group, program, organization,
    )
    if author_membership is not None:
        return GroupViewerContext(
            role=_author_viewer_role(group.group_type, author_membership.role),
            person=person,
            organization=organization,
            program=program,
            today=today,
            group=group,
            membership=author_membership,
        )

    raise PermissionDenied(_ACCESS_DENIED_MESSAGE)


def groups_visible_to_viewer(
    *,
    person: Person,
    organization: Organization,
    program: Program,
    today: date,
) -> set[int]:
    """Return group IDs the viewer may see on list dashboards (performance, coverage).

    Mirrors :func:`resolve_group_dashboard_context` rules without probing a
    single group: LT sees all program groups; UH/CC see groups whose leaf
    bunks overlap supervision/caseload; configured authors see the groups
    they author and nothing above them.
    """
    program_groups = list(
        AssignmentGroup.objects.filter(
            organization=organization,
            program=program,
            is_active=True,
        ).select_related("parent", "parent__parent", "parent__parent__parent"),
    )
    if not program_groups:
        return set()

    if Membership.objects.filter(
        person=person, role="leadership_team", is_active=True,
    ).exists():
        return {g.id for g in program_groups}

    visible: set[int] = set()

    membership_roles = set(
        Membership.objects.filter(
            person=person, is_active=True, program=program,
        ).values_list("role", flat=True),
    )
    if membership_roles:
        config = group_type_config(organization)
        authored = AssignmentGroupMembership.objects.filter(
            person=person,
            role_in_group="author",
            is_active=True,
            group__program=program,
            group__is_active=True,
        ).select_related("group")
        for agm in authored:
            type_cfg = config.get(agm.group.group_type) or {}
            if not type_cfg.get("enabled", True):
                continue
            author_roles = {
                member["role"]
                for member in type_cfg.get("members") or []
                if member.get("placed_as") == "author"
            }
            if membership_roles & author_roles:
                visible.add(agm.group_id)

    supervised_leaf_ids: set[int] = set()
    for uh_membership in Membership.objects.filter(
        person=person, role="unit_head", is_active=True, program=program,
    ):
        supervised_leaf_ids |= supervised_bunk_ids(uh_membership, today=today)

    for cc_membership in Membership.objects.filter(
        person=person, role="camper_care", is_active=True, program=program,
    ):
        supervised_leaf_ids |= caseload_bunk_ids(cc_membership, today=today)

    if supervised_leaf_ids:
        for group in program_groups:
            if _expand_group_to_bunk_ids(group) & supervised_leaf_ids:
                visible.add(group.id)

    return visible

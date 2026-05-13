"""Visibility helpers for Reflection querysets.

The single source of truth for "which reflections is this user allowed to see?"
Combines author / subject / admin / unit-scoped supervisor / wellness paths
into one composable Q-builder so that every list / dashboard / export endpoint
applies the same rules.
"""

from __future__ import annotations

from functools import reduce
from operator import or_

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.models import QuerySet

from bunk_logs.core.context import get_current_organization
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection

User = get_user_model()

# Roles whose reflection visibility is scoped to a set of units via
# ``Membership.metadata.assigned_unit_slugs`` (with ``metadata.unit_slugs`` as a
# legacy alias). ``unit_head`` is intentionally NOT in this set -- unit heads
# get their cross-bunk visibility through the AssignmentGroup descendant walk
# in ``_author_group_ids_with_descendants``, which is a finer-grained mechanism
# than slug matching. After step 3.21 ``camper_care`` is treated as one of
# these supervisors: senior pastoral/clinical leads for the units they're
# assigned to, not a cross-program wellness specialist.
UNIT_SCOPED_SUPERVISOR_ROLES = frozenset({"faculty", "leadership_team", "camper_care"})

# Memberships in these roles get the wellness-template visibility shortcut:
# they see any reflection whose template carries a role in
# ``WELLNESS_TEMPLATE_ROLES``. Reserved for roles whose work is cross-unit by
# nature (nurses, dietitians). ``camper_care`` is intentionally NOT here -- it
# moved to the unit-scoped supervisor capability in step 3.21.
WELLNESS_ROLES = frozenset({"health_center", "special_diets"})

# Template.role values that the wellness team can read collectively. Includes
# ``camper_care`` so a nurse / dietitian still has visibility into pastoral
# notes about a camper they're co-caring for, even though camper-care staff
# themselves no longer get this shortcut.
WELLNESS_TEMPLATE_ROLES = frozenset({"camper_care", "health_center", "special_diets"})


def _person_for_user(user) -> Person | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return Person.all_objects.filter(user=user).first()


def _has_org_admin_membership(person: Person, organization_id: int | None) -> bool:
    qs = Membership.all_objects.filter(person=person, role="admin", is_active=True)
    if organization_id is not None:
        qs = qs.filter(program__organization_id=organization_id)
    return qs.exists()


def _unit_scoped_supervisor_q(person: Person, organization_id: int | None) -> Q | None:
    """Q filter scoping reflections to the unit slugs a supervisor is assigned to.

    Applies to memberships in ``UNIT_SCOPED_SUPERVISOR_ROLES`` (faculty,
    leadership_team, camper_care). Empty / missing ``assigned_unit_slugs`` is
    interpreted as "no unit restriction" -- the supervisor sees every
    reflection in the program. Otherwise we resolve each slug to the set of
    Persons whose Membership in that program declares ``metadata.unit_slug``
    matching one of those slugs, and scope visibility to reflections about
    those subjects.
    """
    qs = Membership.all_objects.filter(
        person=person,
        role__in=UNIT_SCOPED_SUPERVISOR_ROLES,
        is_active=True,
    )
    if organization_id is not None:
        qs = qs.filter(program__organization_id=organization_id)
    memberships = list(qs)
    if not memberships:
        return None

    program_specs: dict[int, dict] = {}
    for m in memberships:
        pid = m.program_id
        raw = m.metadata.get("assigned_unit_slugs")
        if raw is None:
            raw = m.metadata.get("unit_slugs")
        entry = program_specs.setdefault(pid, {"unrestricted": False, "units": set()})
        if not raw:
            entry["unrestricted"] = True
        else:
            entry["units"].update(str(x) for x in raw)

    parts: list[Q] = []
    for pid, spec in program_specs.items():
        if spec["unrestricted"]:
            parts.append(Q(program_id=pid))
            continue
        unit_slugs = spec["units"]
        if not unit_slugs:
            continue
        person_ids = [
            mem.person_id
            for mem in Membership.all_objects.filter(program_id=pid, is_active=True)
            if str(mem.metadata.get("unit_slug") or "") in unit_slugs
        ]
        if person_ids:
            parts.append(Q(program_id=pid, subject_id__in=person_ids))

    if not parts:
        return None
    return reduce(or_, parts)


def _wellness_q(person: Person) -> Q | None:
    has_wellness = Membership.all_objects.filter(
        person=person,
        role__in=WELLNESS_ROLES,
        is_active=True,
    ).exists()
    if not has_wellness:
        return None
    return Q(template__role__in=WELLNESS_TEMPLATE_ROLES)


def _author_group_ids_with_descendants(person: Person) -> set[int]:
    """Return the set of AssignmentGroup ids the person is an author of, plus all
    descendants (children, grandchildren, ...) of those groups.

    Resolved with two bulk queries followed by an in-memory BFS over a parent
    map, so total queries stay constant regardless of group tree depth/size.
    """
    direct_ids = set(
        AssignmentGroupMembership.all_objects.filter(
            person=person,
            role_in_group="author",
            is_active=True,
        ).values_list("group_id", flat=True),
    )
    if not direct_ids:
        return direct_ids

    # Build parent_id -> [child_id, ...] for ALL active groups in the person's org once.
    children_map: dict[int, list[int]] = {}
    rows = AssignmentGroup.all_objects.filter(
        organization_id=person.organization_id,
        is_active=True,
        parent_id__isnull=False,
    ).values_list("parent_id", "id")
    for parent_id, child_id in rows:
        children_map.setdefault(parent_id, []).append(child_id)

    visited = set(direct_ids)
    queue: list[int] = list(direct_ids)
    while queue:
        node = queue.pop()
        for child_id in children_map.get(node, ()):
            if child_id not in visited:
                visited.add(child_id)
                queue.append(child_id)
    return visited


def reflections_visible_to(
    user,
    queryset: QuerySet[Reflection] | None = None,
) -> QuerySet[Reflection]:
    """Return the set of reflections this user is permitted to see.

    Visibility paths (combined with OR):

    1. Superuser or active org-admin Membership -> everything in current org.
    2. Author of the reflection -> always.
    3. Subject of the reflection AND template.subject_visible=True -> always.
    4. Author in the reflection's AssignmentGroup, or in any ancestor group
       (unit heads see their bunks via the descendant walk).
    5. Unit-scoped supervisor membership (faculty / leadership_team /
       camper_care) -> reflections about subjects whose Membership.metadata
       declares one of the assigned unit slugs; or the whole program when
       ``assigned_unit_slugs`` is empty.
    6. Wellness membership (health_center / special_diets) -> reflections
       whose template carries one of the wellness roles.

    All paths are scoped to ``request.organization`` (or whatever the current
    org context is). Cross-tenant rows are unreachable because the base queryset
    uses ``Reflection.objects`` (org-scoped manager).
    """
    if queryset is None:
        queryset = Reflection.objects.all()

    if user is None or not getattr(user, "is_authenticated", False):
        return queryset.none()

    person = _person_for_user(user)
    if person is None:
        # Superuser without a Person profile still gets full org visibility
        if getattr(user, "is_superuser", False):
            org = get_current_organization()
            if org is None:
                return queryset.none()
            return queryset.filter(organization=org)
        return queryset.none()

    org_id = person.organization_id

    if getattr(user, "is_superuser", False) or _has_org_admin_membership(person, org_id):
        return queryset.filter(organization_id=org_id)

    parts: list[Q] = [Q(author=person), Q(subject=person, template__subject_visible=True)]

    author_group_ids = _author_group_ids_with_descendants(person)
    if author_group_ids:
        parts.append(Q(assignment_group_id__in=author_group_ids))

    sq = _unit_scoped_supervisor_q(person, org_id)
    if sq is not None:
        parts.append(sq)

    wq = _wellness_q(person)
    if wq is not None:
        parts.append(wq)

    expr = reduce(or_, parts)
    return queryset.filter(organization_id=org_id).filter(expr).distinct()


def is_org_admin(user) -> bool:
    """Helper: True if user is superuser or has an active admin Membership in their org."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    person = _person_for_user(user)
    if person is None:
        return False
    return _has_org_admin_membership(person, person.organization_id)


def author_group_ids_with_descendants(person: Person) -> set[int]:
    """Public alias for the descendant-aware author-group set; used by dashboards."""
    return _author_group_ids_with_descendants(person)


def has_supervisor_role(user) -> bool:
    """True if user has any path that lets them see beyond their own self-reflections.

    Used by author-attribution view to lock that view down to supervisors only.
    Specifically: org admin, OR author of a group with at least one descendant
    (parent of a child group), OR any unit-scoped supervisor role
    (faculty / leadership_team / camper_care).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    person = _person_for_user(user)
    if person is None:
        return False
    if _has_org_admin_membership(person, person.organization_id):
        return True
    if _unit_scoped_supervisor_q(person, person.organization_id) is not None:
        return True

    direct_ids = list(
        AssignmentGroupMembership.all_objects.filter(
            person=person,
            role_in_group="author",
            is_active=True,
        ).values_list("group_id", flat=True),
    )
    if not direct_ids:
        return False
    return AssignmentGroup.all_objects.filter(
        parent_id__in=direct_ids,
        is_active=True,
    ).exists()

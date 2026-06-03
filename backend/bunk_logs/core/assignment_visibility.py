"""Visibility scoping for the Reflections Dashboard assignment selector.

Answers "which TemplateAssignments may this user see on the dashboard?" using
the same Supervision backbone as ``reflections_visible_for_user`` plus the
admin-only ``AssignmentDashboardGrant`` override. Admins see every assignment
in their org; everyone else sees assignments whose audience they supervise
(by role or by group) or that an admin has explicitly granted them. Grants
only ever widen access — they never hide an assignment a supervisor could
otherwise see.
"""

from __future__ import annotations

from datetime import date
from functools import reduce
from operator import or_
from typing import TYPE_CHECKING

from django.db.models import Q

from bunk_logs.core.models import AssignmentDashboardGrant
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Supervision
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.permissions.visibility import author_group_ids_with_descendants
from bunk_logs.core.permissions.visibility import is_org_admin

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from bunk_logs.core.models import Organization


def _person_for_user(user) -> Person | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return Person.all_objects.filter(user=user).first()


def _active_supervisions(person: Person, organization_id: int):
    today = date.today()
    return Supervision.all_objects.filter(
        supervisor_membership__person=person,
        supervisor_membership__is_active=True,
        supervisor_membership__program__organization_id=organization_id,
        start_date__lte=today,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))


def _supervised_group_ids(person: Person, organization_id: int) -> set[int]:
    """Group ids the person supervises.

    Combines Supervision BUNK / ASSIGNMENT_GROUP targets (expanding the latter
    to descendants) with the authoring pipe (a unit head who authors the unit
    group sees its descendant bunks) from ``author_group_ids_with_descendants``.
    """
    group_ids: set[int] = set()
    sups = _active_supervisions(person, organization_id).select_related(
        "target_group",
    ).only("id", "target_type", "target_bunk_id", "target_group_id")
    for sup in sups:
        if sup.target_type == Supervision.TargetType.BUNK and sup.target_bunk_id:
            group_ids.add(sup.target_bunk_id)
        elif (
            sup.target_type == Supervision.TargetType.ASSIGNMENT_GROUP
            and sup.target_group_id
        ):
            group_ids.add(sup.target_group_id)
            group_ids.update(d.id for d in sup.target_group.get_descendants())
    group_ids |= author_group_ids_with_descendants(person)
    return group_ids


def _supervised_role_pairs(person: Person, organization_id: int) -> set[tuple[int, str]]:
    """``(program_id, role)`` pairs the person supervises via role_in_program."""
    pairs: set[tuple[int, str]] = set()
    sups = _active_supervisions(person, organization_id).filter(
        target_type=Supervision.TargetType.ROLE_IN_PROGRAM,
    ).only("id", "target_program_id", "target_role")
    for sup in sups:
        if sup.target_program_id and sup.target_role:
            pairs.add((sup.target_program_id, sup.target_role))
    return pairs


def _own_assignment_parts(person: Person, organization_id: int) -> list[Q]:
    """Assignments whose audience includes ``person`` (for self-reflection dashboards).

    Lets counselors see their own self-reflection templates without widening
    supervisor-scoped Log Entries access.
    """
    parts: list[Q] = []
    memberships = Membership.all_objects.filter(
        person=person,
        is_active=True,
        program__organization_id=organization_id,
    )
    for mb in memberships:
        parts.append(
            Q(
                target_type=TemplateAssignment.TargetType.ROLE,
                program_id=mb.program_id,
                target_payload__role=mb.role,
            ),
        )
        parts.append(
            Q(
                target_type=TemplateAssignment.TargetType.INDIVIDUALS,
                program_id=mb.program_id,
                target_payload__membership_ids__contains=mb.id,
            ),
        )
        tags = mb.tags if isinstance(mb.tags, list) else []
        for tag in tags:
            if tag:
                parts.append(
                    Q(
                        target_type=TemplateAssignment.TargetType.TAG_GROUP,
                        program_id=mb.program_id,
                        target_payload__tag=tag,
                    ),
                )

    author_group_ids = AssignmentGroupMembership.all_objects.filter(
        person=person,
        role_in_group="author",
        is_active=True,
        group__organization_id=organization_id,
    ).values_list("group_id", flat=True)
    if author_group_ids:
        parts.append(
            Q(
                target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
                assignment_group_id__in=list(author_group_ids),
            ),
        )
    return parts


def assignments_visible_for_user(
    user,
    organization: Organization,
    *,
    scope: str | None = None,
) -> QuerySet[TemplateAssignment]:
    """TemplateAssignment queryset the ``user`` may see on the dashboard.

    Admin / super-admin -> every assignment in the org. Otherwise the union of:
      * assignments targeting a role in a program the viewer supervises,
      * assignments targeting an AssignmentGroup the viewer supervises,
      * assignments explicitly granted to one of the viewer's memberships.

    When ``scope`` is ``"reflections"``, also include assignments whose audience
    includes the viewer (so counselors can open their own self-reflection forms).
    """
    base = TemplateAssignment.all_objects.filter(organization=organization)
    if user is None or not getattr(user, "is_authenticated", False):
        return base.none()
    if is_org_admin(user):
        return base
    person = _person_for_user(user)
    if person is None:
        return base.none()

    org_id = organization.id
    parts: list[Q] = []

    for program_id, role in _supervised_role_pairs(person, org_id):
        parts.append(
            Q(
                target_type=TemplateAssignment.TargetType.ROLE,
                program_id=program_id,
                target_payload__role=role,
            ),
        )

    group_ids = _supervised_group_ids(person, org_id)
    if group_ids:
        parts.append(
            Q(
                target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
                assignment_group_id__in=group_ids,
            ),
        )

    grant_ids = set(
        AssignmentDashboardGrant.objects.filter(
            organization=organization,
            membership__person=person,
            membership__is_active=True,
        ).values_list("assignment_id", flat=True),
    )
    if grant_ids:
        parts.append(Q(id__in=grant_ids))

    if scope == "reflections":
        parts.extend(_own_assignment_parts(person, org_id))

    if not parts:
        return base.none()
    return base.filter(reduce(or_, parts))

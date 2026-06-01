"""Member roster for the unified group dashboard.

Lists everyone with an active ``AssignmentGroupMembership`` in the group
(authors + subjects) alongside their active program ``Membership`` role,
so any group dashboard can answer "who is in this group and in what role".
Authors are listed before subjects, then alphabetically by name.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership

if TYPE_CHECKING:
    from bunk_logs.core.models import AssignmentGroup
    from bunk_logs.core.models import Program

# Authors first, then subjects; secondary sort is alphabetical by name.
_ROLE_IN_GROUP_ORDER = {"author": 0, "subject": 1}


def build_group_roster(
    *, group: AssignmentGroup, program: Program,
) -> list[dict[str, Any]]:
    """Return the active members of ``group`` with their program role.

    ``role_in_group`` is the group-membership role (``author`` / ``subject``);
    ``membership_role`` is the person's first active program Membership role
    (e.g. ``counselor``, ``camper``, ``unit_head``) or ``None`` if they have
    no active membership in the group's program.
    """
    agms = list(
        AssignmentGroupMembership.all_objects.filter(group=group, is_active=True)
        .select_related("person")
        .order_by("person__last_name", "person__first_name", "person_id"),
    )
    if not agms:
        return []

    person_ids = [a.person_id for a in agms]
    membership_role_by_person: dict[int, str] = {}
    for m in Membership.all_objects.filter(
        person_id__in=person_ids, program=program, is_active=True,
    ).order_by("person_id", "id"):
        membership_role_by_person.setdefault(m.person_id, m.role)

    roster = [
        {
            "person_id": a.person_id,
            "name": a.person.full_name if a.person else "Unknown",
            "role_in_group": a.role_in_group,
            "membership_role": membership_role_by_person.get(a.person_id),
        }
        for a in agms
    ]
    roster.sort(key=lambda m: (_ROLE_IN_GROUP_ORDER.get(m["role_in_group"], 9), m["name"]))
    return roster

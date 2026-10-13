"""School screens that follow seats once group_types is saved.

None from these helpers means the org has not saved group_types, and the
caller keeps today's subject-of-classroom behavior. A saved key switches
challenges, faculty rosters, coverage, and the faculty queue onto writer
and supervisor seats.
"""

from __future__ import annotations

from bunk_logs.core.group_audience import supervising_group_ids
from bunk_logs.core.group_audience import writer_ids_by_group
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.org_config import saved_group_type_config
from bunk_logs.core.permissions.visibility import descendant_group_ids

CLASSROOM = "classroom"
AUTHOR = "author"


def roster_term_key(org) -> str:
    """Canonical noun for the faculty roster column.

    Saved settings name the writers with ``counselor``. Until then the
    column keeps ``camper``, which is what live tenants show today.
    """
    if saved_group_type_config(org) is None:
        return "camper"
    return "counselor"


def counted_seat(org) -> str:
    """Seat a madrich must hold to count as grouped.

    Saved settings: the author seat. Otherwise the subject seat.
    """
    if saved_group_type_config(org) is None:
        return "subject"
    return AUTHOR


def supervised_classroom_ids(person, program) -> list[int] | None:
    """Classrooms ``person`` supervises, including descendant classrooms.

    None when the org has not saved group_types.
    """
    org = program.organization
    roots = supervising_group_ids(org, person)
    if roots is None:
        return None
    if not roots:
        return []
    expanded = set(roots) | descendant_group_ids(org.id, set(roots))
    return list(
        AssignmentGroup.all_objects.filter(
            id__in=expanded,
            organization_id=org.id,
            program_id=program.id,
            group_type=CLASSROOM,
            is_active=True,
        ).values_list("id", flat=True),
    )


def supervised_writer_ids(person, program) -> set[int] | None:
    """Writers of the classrooms ``person`` supervises, excluding their role.

    None when the org has not saved group_types. This is the faculty
    queue's supervised set.
    """
    class_ids = supervised_classroom_ids(person, program)
    if class_ids is None:
        return None
    by_group = writer_ids_by_group(
        program.organization, class_ids, exclude_supervisors=True,
    )
    if not by_group:
        return set()
    return {pid for ids in by_group.values() for pid in ids}


def challenge_classroom_ids(person, program) -> list[int] | None:
    """Classrooms where ``person`` may file a challenge.

    None when unsaved: callers keep the subject seat. Saved: the author
    seat on a classroom, and only when their role is configured to write.
    Cohort groups are never included.
    """
    org = program.organization
    if saved_group_type_config(org) is None:
        return None
    authored = list(
        AssignmentGroupMembership.all_objects.filter(
            person=person,
            role_in_group=AUTHOR,
            is_active=True,
            group__group_type=CLASSROOM,
            group__program=program,
            group__is_active=True,
        ).values_list("group_id", flat=True),
    )
    if not authored:
        return []
    writers = writer_ids_by_group(org, authored, exclude_supervisors=False) or {}
    return [gid for gid in authored if person.id in writers.get(gid, ())]

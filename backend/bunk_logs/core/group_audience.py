"""Who writes, who is written about, and who supervises one group.

Saved ``Organization.settings["group_types"]`` is the switch. With no
saved key, ``group_audience`` returns None and callers keep today's
roster rules. A form's role filters only narrow the seats the group
type already configured; they never add a role.

``people_on_seats`` and ``supervising_group_ids`` are the same seats
across many groups, with no form narrow. Descendants are the caller's job.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Iterable

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.org_config import saved_group_type_config
from bunk_logs.core.program_scope import operational_program_q
from bunk_logs.core.time_utils import get_today

__all__ = [
    "GroupAudience",
    "group_audience",
    "people_on_seats",
    "supervising_group_ids",
]


@dataclass(frozen=True)
class GroupAudience:
    """Person ids for one group, after an optional form narrows the seats.

    ``writer_roles`` is the author-seat roles left after that narrow, so a
    person with two memberships only matches the one that writes.
    """

    writers: frozenset[int]
    subjects: frozenset[int]
    supervisors: frozenset[int]
    writer_roles: frozenset[str]


def group_audience(org, group, template=None) -> GroupAudience | None:
    """Writers, subjects, and supervisors for ``group``.

    Returns None when ``org`` has no saved group_types. A self-reflection
    has no separate subject: the writer is the subject.
    """
    config = saved_group_type_config(org)
    if config is None:
        return None

    type_cfg = config.get(getattr(group, "group_type", None)) or {}
    author_roles, subject_roles, supervisors_by_seat = _seat_roles(type_cfg)

    author_filter = _author_filter(template)
    if author_filter is not None:
        author_roles &= author_filter
    subject_filter = _subject_filter(template)
    if subject_filter is not None:
        subject_roles &= subject_filter

    roster = list(
        AssignmentGroupMembership.all_objects.filter(
            group=group,
            is_active=True,
            role_in_group__in=("author", "subject"),
        ).values_list("person_id", "role_in_group"),
    )
    roles_by_person = _roles_by_person(
        [person_id for person_id, _ in roster],
        group.program_id,
    )

    writers: set[int] = set()
    subjects: set[int] = set()
    supervisors: set[int] = set()
    for person_id, seat in roster:
        held = roles_by_person.get(person_id) or set()
        if seat == "author" and held & author_roles:
            writers.add(person_id)
        if seat == "subject" and held & subject_roles:
            subjects.add(person_id)
        if held & supervisors_by_seat.get(seat, set()):
            supervisors.add(person_id)

    if template is not None and getattr(template, "subject_mode", None) == "self":
        subjects = set(writers)

    return GroupAudience(
        frozenset(writers),
        frozenset(subjects),
        frozenset(supervisors),
        frozenset(author_roles),
    )


def people_on_seats(
    org,
    group_ids: Iterable[int],
) -> tuple[set[int], set[int]] | None:
    """``(writers, subjects)`` for ``group_ids``, or None when unsaved.

    No form narrow. A person is a writer or subject only when their roster
    seat matches a role the group type configured for that seat.
    """
    config = saved_group_type_config(org)
    if config is None:
        return None
    ids = [gid for gid in group_ids if gid]
    if not ids:
        return set(), set()

    groups = {
        gid: (group_type, program_id)
        for gid, group_type, program_id in AssignmentGroup.all_objects.filter(
            id__in=ids,
            organization_id=org.id,
        ).values_list("id", "group_type", "program_id")
    }
    if not groups:
        return set(), set()

    seats_by_type = {group_type: _seat_roles(config.get(group_type) or {}) for group_type in {group_type for group_type, _ in groups.values()}}
    roster = list(
        AssignmentGroupMembership.all_objects.filter(
            group_id__in=groups,
            is_active=True,
            role_in_group__in=("author", "subject"),
        ).values_list("group_id", "person_id", "role_in_group"),
    )
    roles = _roles_by_person_and_program(
        {person_id for _, person_id, _ in roster},
        {program_id for _, program_id in groups.values()},
    )

    writers: set[int] = set()
    subjects: set[int] = set()
    for group_id, person_id, seat in roster:
        group_type, program_id = groups[group_id]
        author_roles, subject_roles, _supervisors = seats_by_type[group_type]
        held = roles.get((person_id, program_id), set())
        if seat == "author" and held & author_roles:
            writers.add(person_id)
        elif seat == "subject" and held & subject_roles:
            subjects.add(person_id)
    return writers, subjects


def supervising_group_ids(org, person, *, today=None) -> set[int] | None:
    """Groups where ``person`` holds the ``supervises_group`` seat.

    None when ``org`` has no saved group_types. Descendants are not
    included. Only operational programs count.
    """
    config = saved_group_type_config(org)
    if config is None:
        return None
    if today is None:
        today = get_today(org)

    supervise: dict[tuple[str, str], set[str]] = {}
    for group_type, type_cfg in config.items():
        _authors, _subjects, by_seat = _seat_roles(type_cfg or {})
        for seat, roles in by_seat.items():
            if roles:
                supervise[(group_type, seat)] = roles
    if not supervise:
        return set()

    rows = list(
        AssignmentGroupMembership.all_objects.filter(
            person=person,
            is_active=True,
            group__is_active=True,
            group__organization_id=org.id,
            role_in_group__in=("author", "subject"),
        )
        .filter(operational_program_q(today=today, prefix="group__program"))
        .values_list(
            "group_id",
            "role_in_group",
            "group__group_type",
            "group__program_id",
        ),
    )
    if not rows:
        return set()

    roles = _roles_by_person_and_program(
        [person.id],
        {program_id for *_, program_id in rows},
    )
    out: set[int] = set()
    for group_id, seat, group_type, program_id in rows:
        needed = supervise.get((group_type, seat))
        held = roles.get((person.id, program_id), set())
        if needed and held & needed:
            out.add(group_id)
    return out


def _seat_roles(
    type_cfg: dict[str, Any],
) -> tuple[set[str], set[str], dict[str, set[str]]]:
    """Author roles, subject roles, and supervisor roles by seat."""
    members: list[dict[str, Any]] = []
    if type_cfg.get("enabled", True):
        members = list(type_cfg.get("members") or [])
    author_roles = {m["role"] for m in members if m.get("placed_as") == "author"}
    subject_roles = {m["role"] for m in members if m.get("placed_as") == "subject"}
    supervisors_by_seat: dict[str, set[str]] = {}
    for member in members:
        if member.get("supervises_group"):
            supervisors_by_seat.setdefault(member["placed_as"], set()).add(member["role"])
    return author_roles, subject_roles, supervisors_by_seat


def _author_filter(template) -> set[str] | None:
    """Author roles the form allows, or None when no form is in play.

    An empty filter falls back to ``template.role``. Both empty means
    the form names nobody, which adds nobody.
    """
    if template is None:
        return None
    roles = [role for role in (getattr(template, "author_role_filter", None) or []) if role]
    if roles:
        return set(roles)
    role = getattr(template, "role", None)
    if role:
        return {role}
    return set()


def _subject_filter(template) -> set[str] | None:
    """Subject roles the form allows. Empty does not narrow.

    Self-reflections ignore this: the writer is the subject.
    """
    if template is None or getattr(template, "subject_mode", None) == "self":
        return None
    roles = [role for role in (getattr(template, "subject_role_filter", None) or []) if role]
    if not roles:
        return None
    return set(roles)


def _roles_by_person(person_ids: list[int], program_id: int) -> dict[int, set[str]]:
    paired = _roles_by_person_and_program(person_ids, [program_id])
    return {person_id: roles for (person_id, _program_id), roles in paired.items()}


def _roles_by_person_and_program(
    person_ids,
    program_ids,
) -> dict[tuple[int, int], set[str]]:
    if not person_ids or not program_ids:
        return {}
    out: dict[tuple[int, int], set[str]] = {}
    rows = Membership.all_objects.filter(
        person_id__in=person_ids,
        program_id__in=program_ids,
        is_active=True,
    ).values_list("person_id", "program_id", "role")
    for person_id, program_id, role in rows:
        out.setdefault((person_id, program_id), set()).add(role)
    return out

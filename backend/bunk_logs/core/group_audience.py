"""Who writes, who is written about, and who supervises one group.

Saved ``Organization.settings["group_types"]`` is the switch. With no
saved key, ``group_audience`` returns None and callers keep today's
roster rules. A form's role filters only narrow the seats the group
type already configured; they never add a role.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.org_config import saved_group_type_config

__all__ = ["GroupAudience", "group_audience"]


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
    members: list[dict[str, Any]] = []
    if type_cfg.get("enabled", True):
        members = list(type_cfg.get("members") or [])

    author_roles = {m["role"] for m in members if m.get("placed_as") == "author"}
    subject_roles = {m["role"] for m in members if m.get("placed_as") == "subject"}
    supervisors_by_seat: dict[str, set[str]] = {}
    for member in members:
        if member.get("supervises_group"):
            supervisors_by_seat.setdefault(member["placed_as"], set()).add(member["role"])

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
    if not person_ids:
        return {}
    out: dict[int, set[str]] = {}
    rows = Membership.all_objects.filter(
        person_id__in=person_ids,
        program_id=program_id,
        is_active=True,
    ).values_list("person_id", "role")
    for person_id, role in rows:
        out.setdefault(person_id, set()).add(role)
    return out

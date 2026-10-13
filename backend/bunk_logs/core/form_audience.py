"""Who a form will reach, before an assignment is saved.

Writers and subjects come from ``group_audience`` when the org has saved
group types, and from the legacy roster rules otherwise. Supervisors of
the group, and of each parent group, use that same seat rule. A form's
role filters only narrow seats the group type already configured.
"""

from __future__ import annotations

from datetime import date

from bunk_logs.core.assignment_resolution import resolve_members
from bunk_logs.core.group_audience import _author_filter
from bunk_logs.core.group_audience import _roles_by_person
from bunk_logs.core.group_audience import _seat_roles
from bunk_logs.core.group_audience import _subject_filter
from bunk_logs.core.group_audience import group_audience
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.org_config import group_type_config
from bunk_logs.core.program_scope import operational_program_q
from bunk_logs.core.terminology import term

__all__ = [
    "form_role_filters_error",
    "preview_form_audience",
]


def form_role_filters_error(org, group_types, author_filter, subject_filter) -> dict | None:
    """Reject a filter role the checked group types do not configure for that seat.

    Empty filters are allowed: an empty author filter still means the
    template's role, and an empty subject filter does not narrow.
    """
    types = [group_type for group_type in (group_types or []) if group_type]
    if not types:
        return None
    config = group_type_config(org)
    authors: set[str] = set()
    subjects: set[str] = set()
    for group_type in types:
        cfg = config.get(group_type) or {}
        if cfg.get("enabled", True) is False:
            continue
        for member in cfg.get("members") or []:
            if member.get("placed_as") == "author":
                authors.add(member["role"])
            elif member.get("placed_as") == "subject":
                subjects.add(member["role"])
    bad_authors = [role for role in (author_filter or []) if role and role not in authors]
    if bad_authors:
        label = _and_join(term(org, role, capitalize=True) for role in bad_authors)
        return {
            "author_role_filter": (f"{label} cannot write this form for the selected group types."),
        }
    bad_subjects = [role for role in (subject_filter or []) if role and role not in subjects]
    if bad_subjects:
        label = _and_join(term(org, role, capitalize=True) for role in bad_subjects)
        return {
            "subject_role_filter": (f"{label} is not who this form can be about for the selected group types."),
        }
    return None


def preview_form_audience(org, template, *, target_type, role="", groups=None) -> dict:
    """Writers, subjects, supervisors, and one sentence an admin can read."""
    if target_type == "role":
        return _preview_role(org, template, role)
    rows = [_preview_group(org, template, group) for group in (groups or [])]
    if not rows:
        return _empty("Choose a group.")
    return _combine(rows)


def _preview_role(org, template, role: str) -> dict:
    if not role:
        return _empty("Pick a role.")
    today = date.today()
    person_ids = set(
        Membership.all_objects.filter(
            program__organization=org,
            is_active=True,
            role=role,
        )
        .filter(operational_program_q(today=today))
        .values_list("person_id", flat=True),
    )
    program_ids = (
        set(
            Membership.all_objects.filter(
                program__organization=org,
                is_active=True,
                role=role,
                person_id__in=person_ids,
            ).values_list("program_id", flat=True),
        )
        if person_ids
        else set()
    )
    writers = _people(org, person_ids, program_ids, {role})
    about_self = getattr(template, "subject_mode", None) == "self"
    subjects = list(writers) if about_self else []
    label = term(org, role, plural=True)
    if not writers:
        sentence = f"No {label} will write this yet. People added to that role later will be included."
    elif about_self:
        sentence = f"{_names(writers)} will write about themselves."
    else:
        sentence = f"{_names(writers)} will write this form about the people in their groups."
    return {
        "sentence": sentence,
        "can_assign": True,
        "writers": writers,
        "subjects": subjects,
        "supervisors": [],
        "groups": [],
    }


def _preview_group(org, template, group) -> dict:
    audience = group_audience(org, group, template)
    if audience is not None:
        writer_ids = set(audience.writers)
        subject_ids = set(audience.subjects)
    else:
        writer_ids = _legacy_writer_ids(org, group, template)
        if getattr(template, "subject_mode", None) == "self":
            subject_ids = set(writer_ids)
        else:
            subject_ids = _legacy_subject_ids(group, template)
    supervisor_ids = _supervisor_ids(org, group)
    program_ids = {group.program_id}
    about_self = getattr(template, "subject_mode", None) == "self"
    writers = _people(org, writer_ids, program_ids, _writer_roles(org, group, template))
    subjects = (
        []
        if about_self
        else _people(
            org,
            subject_ids,
            program_ids,
            _subject_roles(org, group, template),
        )
    )
    supervisors = _people(org, supervisor_ids, program_ids, _supervisor_roles(org, group))
    missing = []
    if not writers:
        missing.append("writers")
    if not about_self and not subjects:
        missing.append("subjects")
    row = {
        "id": group.id,
        "name": group.name,
        "missing": missing,
        "can_assign": not missing,
        "writers": writers,
        "subjects": subjects,
        "supervisors": supervisors,
        "writer_phrase": _phrase(org, _writer_roles(org, group, template)),
        "subject_phrase": _phrase(org, _subject_roles(org, group, template)),
        "about_self": about_self,
    }
    row["sentence"] = _group_sentence(row)
    return row


def _combine(rows: list[dict]) -> dict:
    return {
        "sentence": " ".join(row["sentence"] for row in rows),
        "can_assign": all(row["can_assign"] for row in rows),
        "writers": _union(rows, "writers"),
        "subjects": _union(rows, "subjects"),
        "supervisors": _union(rows, "supervisors"),
        "groups": [
            {
                key: row[key]
                for key in (
                    "id",
                    "name",
                    "missing",
                    "can_assign",
                    "writers",
                    "subjects",
                    "supervisors",
                )
            }
            for row in rows
        ],
    }


def _empty(sentence: str) -> dict:
    return {
        "sentence": sentence,
        "can_assign": False,
        "writers": [],
        "subjects": [],
        "supervisors": [],
        "groups": [],
    }


def _legacy_writer_ids(org, group, template) -> set[int]:
    stub = TemplateAssignment(
        organization=org,
        program=group.program,
        template=template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=group,
        target_payload={},
    )
    return set(resolve_members(stub, date.today()).values_list("person_id", flat=True))


def _legacy_subject_ids(group, template) -> set[int]:
    subject_ids = set(
        AssignmentGroupMembership.all_objects.filter(
            group=group,
            role_in_group="subject",
            is_active=True,
        ).values_list("person_id", flat=True),
    )
    role_filter = [role for role in (getattr(template, "subject_role_filter", None) or []) if role]
    if not subject_ids or not role_filter:
        return subject_ids
    return set(
        Membership.all_objects.filter(
            person_id__in=subject_ids,
            program_id=group.program_id,
            is_active=True,
            role__in=role_filter,
        ).values_list("person_id", flat=True),
    )


def _supervisor_ids(org, group) -> set[int]:
    """Supervisors of this group and each parent group."""
    found: set[int] = set()
    seen: set[int] = set()
    node = group
    while node is not None and node.id not in seen:
        seen.add(node.id)
        audience = group_audience(org, node, None)
        if audience is not None:
            found |= set(audience.supervisors)
        else:
            found |= _default_seat_supervisors(org, node)
        node = node.parent
    return found


def _default_seat_supervisors(org, group) -> set[int]:
    """Supervisor seat from the default group-type map, for an unsaved org."""
    cfg = group_type_config(org).get(group.group_type) or {}
    _authors, _subjects, supervisors_by_seat = _seat_roles(cfg)
    if not any(supervisors_by_seat.values()):
        return set()
    roster = list(
        AssignmentGroupMembership.all_objects.filter(
            group=group,
            is_active=True,
            role_in_group__in=("author", "subject"),
        ).values_list("person_id", "role_in_group"),
    )
    roles_by_person = _roles_by_person(
        [person_id for person_id, _seat in roster],
        group.program_id,
    )
    found: set[int] = set()
    for person_id, seat in roster:
        held = roles_by_person.get(person_id) or set()
        if held & supervisors_by_seat.get(seat, set()):
            found.add(person_id)
    return found


def _writer_roles(org, group, template) -> list[str]:
    configured = _configured_roles(org, group, "author")
    wanted = _author_filter(template) or set()
    if wanted:
        narrowed = [role for role in configured if role in wanted]
        return narrowed or list(wanted)
    return configured


def _subject_roles(org, group, template) -> list[str]:
    configured = _configured_roles(org, group, "subject")
    wanted = _subject_filter(template)
    if not wanted:
        return configured
    narrowed = [role for role in configured if role in wanted]
    return narrowed or list(wanted)


def _supervisor_roles(org, group) -> set[str]:
    roles: set[str] = set()
    node = group
    seen: set[int] = set()
    config = group_type_config(org)
    while node is not None and node.id not in seen:
        seen.add(node.id)
        cfg = config.get(node.group_type) or {}
        _authors, _subjects, supervisors_by_seat = _seat_roles(cfg)
        for seat_roles in supervisors_by_seat.values():
            roles |= seat_roles
        node = node.parent
    return roles


def _configured_roles(org, group, placed_as: str) -> list[str]:
    cfg = group_type_config(org).get(group.group_type) or {}
    if cfg.get("enabled", True) is False:
        return []
    ordered = [code for code, _label in Membership.ROLES]
    found = [member["role"] for member in cfg.get("members") or [] if member.get("placed_as") == placed_as and member.get("role")]
    return [role for role in ordered if role in found]


def _people(org, person_ids, program_ids, preferred) -> list[dict]:
    if not person_ids:
        return []
    people = Person.all_objects.filter(organization=org, id__in=person_ids).order_by(
        "last_name",
        "first_name",
        "id",
    )
    held: dict[int, set[str]] = {}
    if program_ids:
        rows = Membership.all_objects.filter(
            person_id__in=person_ids,
            program_id__in=program_ids,
            is_active=True,
        ).values_list("person_id", "role")
        for person_id, role in rows:
            held.setdefault(person_id, set()).add(role)
    preferred_order = [code for code, _label in Membership.ROLES if code in set(preferred)]
    out = []
    for person in people:
        roles = held.get(person.id) or set()
        role = next((item for item in preferred_order if item in roles), next(iter(roles), ""))
        out.append(
            {
                "id": person.id,
                "name": str(person),
                "role": role,
                "role_label": term(org, role, capitalize=True) if role else "",
            },
        )
    return out


def _group_sentence(row: dict) -> str:
    name = row["name"]
    if "writers" in row["missing"]:
        who = row["writer_phrase"] or "anyone"
        return f"{name} has no {who} to write this form."
    if "subjects" in row["missing"]:
        who = row["subject_phrase"] or "one to write about"
        return f"{name} has no {who}. This form is about other people, so it cannot be assigned there."
    writers = _names(row["writers"])
    if row["about_self"]:
        text = f"{writers} will write about themselves."
    else:
        text = f"{writers} will write about {_names(row['subjects'])}."
    if row["supervisors"]:
        text += f" {_names(row['supervisors'])} can read it."
    return text


def _names(people: list[dict]) -> str:
    return _and_join(person["name"] for person in people)


def _phrase(org, roles) -> str:
    return _or_join(term(org, role, plural=True) for role in roles)


def _and_join(parts) -> str:
    return _join(list(parts), "and")


def _or_join(parts) -> str:
    return _join(list(parts), "or")


def _join(parts: list[str], conj: str) -> str:
    items = [part for part in parts if part]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"
    return f"{', '.join(items[:-1])}, {conj} {items[-1]}"


def _union(rows: list[dict], key: str) -> list[dict]:
    seen: set[int] = set()
    out = []
    for row in rows:
        for person in row[key]:
            if person["id"] in seen:
                continue
            seen.add(person["id"])
            out.append(person)
    return out

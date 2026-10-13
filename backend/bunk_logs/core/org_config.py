"""Per-org role list and how each group type places people.

``Organization.settings["roles"]`` and ``["group_types"]`` override the
defaults. With neither key set, the defaults match current Crane Lake
and Temple Beth-El behavior, so those tenants need no data change.

Display nouns stay in ``terminology``. Nothing here decides permissions;
``Membership.capability`` still does.
"""
from __future__ import annotations

import copy
from typing import Any

from django.db.models import Count

from bunk_logs.core.models import ROLE_TO_CAPABILITY
from bunk_logs.core.models import SUPERVISOR_CAPABILITIES
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import Membership
from bunk_logs.core.terminology import term

KNOWN_ROLES: frozenset[str] = frozenset(code for code, _ in Membership.ROLES)
KNOWN_GROUP_TYPES: frozenset[str] = frozenset(code for code, _ in AssignmentGroup.GROUP_TYPES)
PLACEMENTS: frozenset[str] = frozenset({"author", "subject"})

# One line each, for the Settings role list. Plain language, no slugs.
ROLE_DESCRIPTIONS: dict[str, str] = {
    "camper": "Someone the program writes logs about.",
    "student": "Someone the program writes logs about.",
    "counselor": "Writes logs about the people in their group.",
    "junior_counselor": "Writes logs alongside a counselor.",
    "general_counselor": "Writes logs and can move between groups.",
    "specialist": "Writes logs for an activity they lead.",
    "unit_head": "Supervises the groups in a unit.",
    "leadership_team": "Reviews the whole program.",
    "kitchen_staff": "Writes a kitchen reflection.",
    "maintenance": "Handles repair requests.",
    "administrative_staff": "Office staff who are not tied to one group.",
    "housekeeping": "Housekeeping staff.",
    "camper_care": "Follows a caseload of people who need extra support.",
    "health_center": "Writes health notes.",
    "medical": "Writes medical notes.",
    "special_diets": "Tracks special diets.",
    "madrich": "Can write logs and be written about in the same group.",
    "faculty": "Leads a class.",
    "admin": "Runs the organization.",
}


def _member(role: str, placed_as: str, *, supervises_group: bool = False) -> dict[str, Any]:
    return {
        "role": role,
        "placed_as": placed_as,
        "supervises_group": supervises_group,
    }


# Camper care is intentionally absent: their caseload stays a Supervision
# row with target_type "bunk", not a placement on the unit.
DEFAULT_GROUP_TYPE_CONFIG: dict[str, dict[str, Any]] = {
    "bunk": {
        "enabled": True,
        "members": [
            _member("counselor", "author"),
            _member("junior_counselor", "author"),
            _member("general_counselor", "author"),
            _member("camper", "subject"),
        ],
    },
    "classroom": {
        "enabled": True,
        "members": [
            _member("madrich", "author"),
            _member("madrich", "subject"),
            _member("faculty", "author"),
            _member("student", "subject"),
        ],
    },
    "unit": {
        "enabled": True,
        "members": [
            _member("unit_head", "author", supervises_group=True),
        ],
    },
    "division": {
        "enabled": True,
        "members": [
            _member("unit_head", "author", supervises_group=True),
        ],
    },
}


def _ordered(roles: set[str]) -> list[str]:
    return [code for code, _ in Membership.ROLES if code in roles]


def enabled_roles(org) -> list[str]:
    """Role slugs this org may assign.

    An explicit ``settings["roles"]`` list wins. Otherwise every role that
    has any Membership in the org, plus admin, so a tenant with no setting
    keeps the roles it already uses.
    """
    raw = (getattr(org, "settings", None) or {}).get("roles")
    if isinstance(raw, list) and raw:
        chosen = {role for role in raw if role in KNOWN_ROLES}
        if chosen:
            return _ordered(chosen)
    in_use = set(
        Membership.all_objects.filter(
            program__organization=org,
        ).values_list("role", flat=True),
    )
    in_use.add("admin")
    return _ordered(in_use)


def explicit_role_list(org) -> set[str] | None:
    """The saved role list, or None when the org has not chosen one.

    Create-person enforces the list only after it is saved. Until then the
    dropdown is the computed set and existing imports keep working.
    """
    raw = (getattr(org, "settings", None) or {}).get("roles")
    if not isinstance(raw, list) or not raw:
        return None
    chosen = {role for role in raw if role in KNOWN_ROLES}
    return chosen or None


def role_allowed(org, role: str) -> bool:
    chosen = explicit_role_list(org)
    if chosen is None:
        return role in KNOWN_ROLES
    return role in chosen


def group_type_config(org) -> dict[str, dict[str, Any]]:
    """Resolved group-type map. A saved dict replaces the defaults entirely."""
    raw = (getattr(org, "settings", None) or {}).get("group_types")
    if not isinstance(raw, dict) or not raw:
        return copy.deepcopy(DEFAULT_GROUP_TYPE_CONFIG)
    normalized = _normalize_group_types(raw)
    if not normalized:
        return copy.deepcopy(DEFAULT_GROUP_TYPE_CONFIG)
    return normalized


def author_roles_for(org, group_type: str) -> frozenset[str]:
    """Membership roles that may open this group type by authoring it."""
    cfg = group_type_config(org).get(group_type) or {}
    if not cfg.get("enabled", True):
        return frozenset()
    return frozenset(
        member["role"]
        for member in cfg.get("members") or []
        if member.get("placed_as") == "author"
    )


def role_catalog(org=None) -> list[dict[str, Any]]:
    """Every role, with a description and whether it may supervise a group."""
    return [
        {
            "role": code,
            "description": ROLE_DESCRIPTIONS.get(code, ""),
            "can_supervise": ROLE_TO_CAPABILITY.get(code) in SUPERVISOR_CAPABILITIES,
            "label": term(org, code, capitalize=True) if org is not None else term(None, code, capitalize=True),
        }
        for code, _ in Membership.ROLES
    ]


def validate_roles_update(org, roles: Any) -> str | None:
    """Reject an explicit role list that drops a role people still hold."""
    if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
        return "Choose roles from the list."
    unknown = [role for role in roles if role not in KNOWN_ROLES]
    if unknown:
        return "Choose roles from the list."
    if not roles:
        return "Choose at least one role."
    chosen = set(roles)
    rows = (
        Membership.all_objects.filter(
            program__organization=org,
            is_active=True,
        )
        .exclude(role__in=chosen)
        .values("role")
        .annotate(n=Count("id"))
        .order_by("role")
    )
    parts = []
    for row in rows:
        label = term(org, row["role"], capitalize=True)
        noun = "person" if row["n"] == 1 else "people"
        parts.append(f"{label} still has {row['n']} active {noun}")
    if not parts:
        return None
    joined = "; ".join(parts)
    return f"{joined}. Change their role before turning it off."


def validate_group_types(org, raw: Any) -> str | None:
    """Reject a group-type map that isn't a legal placement list."""
    if not isinstance(raw, dict):
        return "Group settings must list each kind of group."
    for group_type, cfg in raw.items():
        type_label = term(org, group_type, capitalize=True)
        if group_type not in KNOWN_GROUP_TYPES:
            return "That kind of group isn't one this organization can use."
        if not isinstance(cfg, dict):
            return f"{type_label} settings are incomplete."
        members = cfg.get("members") or []
        if not isinstance(members, list):
            return f"{type_label} needs a list of roles."
        seen: dict[str, set[str]] = {}
        for member in members:
            if not isinstance(member, dict):
                return f"{type_label} has a role that isn't filled in."
            role = member.get("role")
            placed = member.get("placed_as")
            if role not in KNOWN_ROLES or placed not in PLACEMENTS:
                return f"Choose a role and how they sit in the {type_label.lower()}."
            label = term(org, role)
            if placed in seen.get(role, set()):
                return (
                    f"{label.capitalize()} is listed twice the same way "
                    f"for a {type_label.lower()}."
                )
            seen.setdefault(role, set()).add(placed)
            if member.get("supervises_group") and (
                ROLE_TO_CAPABILITY.get(role) not in SUPERVISOR_CAPABILITIES
            ):
                return (
                    f"A {label} can't supervise a group. "
                    "Pick a role like unit head or faculty."
                )
    return None


def _normalize_group_types(raw: dict) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for group_type, cfg in raw.items():
        if group_type not in KNOWN_GROUP_TYPES or not isinstance(cfg, dict):
            continue
        members = []
        for member in cfg.get("members") or []:
            if not isinstance(member, dict):
                continue
            role = member.get("role")
            placed = member.get("placed_as")
            if role not in KNOWN_ROLES or placed not in PLACEMENTS:
                continue
            members.append({
                "role": role,
                "placed_as": placed,
                "supervises_group": bool(member.get("supervises_group")),
            })
        out[group_type] = {
            "enabled": bool(cfg.get("enabled", True)),
            "members": members,
        }
    return out

"""Normalize a generic spreadsheet roster CSV to canonical importer fields.

Orgs without a Campminder or ShulCloud export just keep a spreadsheet of
names, so this reads the headers admins actually type ("First Name",
"Grade", "Class") and defaults a blank ``role`` to ``student`` -- the whole
point of the generic source.

Invariant: a blank ``role`` cell must resolve to ``student``, never to a
staff role, or a bulk student upload silently provisions logins.
"""

from __future__ import annotations

from bunk_logs.core.campminder_csv import normalize_role_value

DEFAULT_ROLE = "student"

# Group type per program type, used when a row names a group but no explicit
# group_type column. Religious schools think in classes, camps in bunks.
_GROUP_TYPE_BY_PROGRAM_TYPE: dict[str, str] = {
    "religious_school": "classroom",
    "summer_camp": "bunk",
}
FALLBACK_GROUP_TYPE = "custom"

# Canonical field -> accepted normalized header variants (see _normalize_header).
_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "external_id": ("external id", "id", "student id", "person id", "member id"),
    "first_name": ("first name", "firstname", "first", "given name"),
    "last_name": ("last name", "lastname", "last", "surname", "family name"),
    "preferred_name": (
        "preferred name",
        "preferredname",
        "preferred",
        "nickname",
        "goes by",
    ),
    "email": ("email", "email address", "e mail", "e-mail"),
    "role": ("role",),
    "grade_level": ("grade level", "grade", "gradelevel"),
    "group_name": (
        "group name",
        "group",
        "class",
        "class name",
        "classroom",
        "classroom name",
        "bunk",
        "bunk name",
    ),
    "group_type": ("group type", "grouptype"),
    "role_in_group": ("role in group", "group role"),
}


def _normalize_header(key: str) -> str:
    return (
        key.lstrip("\ufeff")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("/", " ")
    )


def _indexed_row(row: dict) -> dict[str, str]:
    """Build a case/spacing-insensitive lookup from raw CSV headers."""
    indexed: dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized = _normalize_header(str(key))
        if normalized and value is not None and str(value).strip():
            indexed.setdefault(normalized, str(value).strip())
    return indexed


def _field_value(indexed: dict[str, str], field: str) -> str:
    for alias in _HEADER_ALIASES[field]:
        value = indexed.get(alias)
        if value:
            return value
    return ""


def default_group_type(program_type: str) -> str:
    """Group type to create when a row names a group but not its type."""
    return _GROUP_TYPE_BY_PROGRAM_TYPE.get(program_type or "", FALLBACK_GROUP_TYPE)


def parse_optional_int(raw: str) -> int | None:
    """Parse a whole number from a CSV cell; None when blank or unparseable."""
    value = (raw or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def normalize_people_row(row: dict) -> dict:
    """Map spreadsheet headers to the fields ``import_people_roster`` reads."""
    indexed = _indexed_row(row)

    first_name = _field_value(indexed, "first_name")
    preferred_name = _field_value(indexed, "preferred_name")
    if not first_name and preferred_name:
        first_name = preferred_name

    role = normalize_role_value(_field_value(indexed, "role")) or DEFAULT_ROLE

    return {
        "external_id": _field_value(indexed, "external_id"),
        "first_name": first_name,
        "last_name": _field_value(indexed, "last_name"),
        "preferred_name": preferred_name,
        "email": _field_value(indexed, "email"),
        "role": role,
        "grade_level": _field_value(indexed, "grade_level"),
        "group_name": _field_value(indexed, "group_name"),
        "group_type": _field_value(indexed, "group_type"),
        "role_in_group": _field_value(indexed, "role_in_group"),
    }

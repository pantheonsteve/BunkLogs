"""Normalize Campminder CSV export column variants to canonical importer fields."""

from __future__ import annotations

import csv
import io
from pathlib import Path


def _normalize_header(key: str) -> str:
    return (
        key.lstrip("\ufeff")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("/", " ")
    )


def format_csv_headers(row: dict) -> str:
    """Comma-separated normalized headers for import diagnostics."""
    return ", ".join(sorted({_normalize_header(str(k)) for k in row if k}))


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


# Canonical field -> accepted normalized header variants.
_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "campminder_id": (
        "campminder id",
        "campminder_id",
        "personid",
        "person id",
        "person_id",
    ),
    "first_name": ("first name", "firstname", "first", "legal first name"),
    "last_name": (
        "last name",
        "lastname",
        "last",
        "family name",
        "surname",
        "camper last name",
        "legal last name",
        "primary last name",
    ),
    "preferred_name": (
        "preferred name",
        "preferredname",
        "preferred",
        "nickname",
        "nick name",
        "goes by",
    ),
    "email": (
        "email",
        "email address",
        "login email",
        "login",
    ),
    "role": ("role",),
    "position_type": ("position types", "position type", "positiontypes"),
    "position": ("position", "title", "job title"),
    "bunk_name": ("bunk name", "bunk", "bunk_name"),
    "unit_name": ("unit name", "unit", "unit_name"),
    "division_name": ("division name", "division", "division_name"),
    "caseload_name": ("caseload name", "caseload", "caseload_name"),
    "caseload_owner_campminder_id": (
        "caseload owner campminder id",
        "caseload owner id",
        "caseload_owner_campminder_id",
        "caseload_owner_id",
    ),
    "language_preference": ("language preference", "language", "language_preference"),
    "tags": ("tags",),
}


def _field_value(indexed: dict[str, str], field: str) -> str:
    for alias in _HEADER_ALIASES[field]:
        value = indexed.get(alias)
        if value:
            return value
    return ""


def _position_key(value: str) -> str:
    return value.strip().lower()


def infer_role_from_position(position_type: str, position: str) -> str:
    """Map Campminder staff ``Position Types`` / ``Position`` to Membership.role."""
    pos = _position_key(position)
    pos_type = _position_key(position_type)

    if pos == "camper care associate":
        return "camper_care"
    if pos == "allergies and special food coordinator":
        return "special_diets"
    if pos == "driver":
        return "maintenance"
    if pos.startswith("director:"):
        return "specialist"
    if "camper care" in pos:
        return "camper_care"
    if "unit head" in pos:
        return "unit_head"
    if "junior counselor" in pos:
        return "junior_counselor"
    if "general counselor" in pos:
        return "general_counselor"
    if "counselor" in pos:
        return "counselor"
    if "kitchen" in pos:
        return "kitchen_staff"
    if "housekeeping" in pos:
        return "housekeeping"
    if "health" in pos or "nurse" in pos or "wellness" in pos:
        return "health_center"
    if "special diet" in pos or "allerg" in pos:
        return "special_diets"
    if "maintenance" in pos:
        return "maintenance"

    if pos_type == "leadership team":
        return "leadership_team"
    if pos_type == "administrative staff":
        return "maintenance"
    if pos_type == "counseling staff":
        return "counselor"
    if pos_type == "kitchen staff":
        return "kitchen_staff"
    if pos_type == "maintenance":
        return "maintenance"
    if pos_type == "housekeeping":
        return "housekeeping"

    return ""


def _infer_default_role(
    indexed: dict[str, str],
    *,
    first_name: str,
    email: str,
    position_type: str,
    position: str,
) -> str:
    explicit_role = _field_value(indexed, "role")
    if explicit_role:
        return explicit_role

    from_position = infer_role_from_position(position_type, position)
    if from_position:
        return from_position

    if first_name and email:
        return "counselor"
    return "camper"


def normalize_campminder_row(row: dict) -> dict:
    """Map Campminder export headers to the fields expected by roster importers.

    Supports the full roster format (``campminder_id``, ``first_name``, ``role``,
    bunk columns, etc.) and minimal exports:

    * Campers: ``Last Name``, ``Preferred Name``, ``PersonID``
    * Staff: ``PersonID``, ``Last Name``, ``First Name``, ``Login/Email``,
      ``Position Types``, ``Position``
    """
    indexed = _indexed_row(row)

    campminder_id = _field_value(indexed, "campminder_id")
    first_name = _field_value(indexed, "first_name")
    last_name = _field_value(indexed, "last_name")
    preferred_name = _field_value(indexed, "preferred_name")
    email = _field_value(indexed, "email")
    position_type = _field_value(indexed, "position_type")
    position = _field_value(indexed, "position")
    if not first_name and preferred_name:
        first_name = preferred_name

    role = _infer_default_role(
        indexed,
        first_name=first_name,
        email=email,
        position_type=position_type,
        position=position,
    )

    return {
        "campminder_id": campminder_id,
        "first_name": first_name,
        "last_name": last_name,
        "preferred_name": preferred_name,
        "email": email,
        "role": role,
        "position_type": position_type,
        "position": position,
        "bunk_name": _field_value(indexed, "bunk_name"),
        "unit_name": _field_value(indexed, "unit_name"),
        "division_name": _field_value(indexed, "division_name"),
        "caseload_name": _field_value(indexed, "caseload_name"),
        "caseload_owner_campminder_id": _field_value(indexed, "caseload_owner_campminder_id"),
        "language_preference": _field_value(indexed, "language_preference"),
        "tags": _field_value(indexed, "tags"),
    }


def read_campminder_csv_rows(source) -> list[dict]:
    """Read a Campminder CSV from a path or text stream, sniffing comma/tab delimiters."""
    if isinstance(source, (str, Path)):
        with Path(source).open(newline="", encoding="utf-8-sig") as handle:
            return _read_dict_rows(handle)
    return _read_dict_rows(source)


def read_campminder_csv_bytes(raw_bytes: bytes) -> list[dict]:
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    return _read_dict_rows(io.StringIO(text))


def _read_dict_rows(handle) -> list[dict]:
    sample = handle.read(4096)
    handle.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    return list(csv.DictReader(handle, dialect=dialect))

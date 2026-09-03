"""Per-organization display vocabulary.

Canonical keys (``camper``, ``director``, ``cohort``, ...) stay in the
database, in ``ReflectionTemplate.schema``, and in URLs; only the rendered
noun varies per tenant. An org opts in through
``Organization.settings["terminology"]``, and every key it omits falls back
to ``DEFAULT_TERMS`` -- so a tenant without the setting renders exactly the
copy it rendered before this module existed.

Invariant: nothing here may be used to derive permissions or to look up
rows. Display only.
"""
from __future__ import annotations

from typing import Any

# ``one`` / ``other`` rather than a bare string because the replacements are
# not all the same shape: "camper" pluralizes, "Ed Team" is a collective noun
# that stays singular in copy that used to say "Director".
DEFAULT_TERMS: dict[str, dict[str, str]] = {
    "camper": {"one": "camper", "other": "campers"},
    "student": {"one": "student", "other": "students"},
    "director": {"one": "Director", "other": "Directors"},
    "cohort": {"one": "cohort", "other": "cohorts"},
    # Group nouns. The canonical key stays the camp word even where a tenant
    # renames it, the same way ``camper`` does -- ``AssignmentGroup.group_type``
    # still stores ``bunk`` when a school renders it as "class".
    "bunk": {"one": "bunk", "other": "bunks"},
    "unit": {"one": "unit", "other": "units"},
    "team": {"one": "team", "other": "teams"},
    "caseload": {"one": "caseload", "other": "caseloads"},
    # The admin's merged roster area holds every ``group_type`` at once, so it
    # needs a noun broader than ``bunk``. A school that only has classrooms
    # renames it to "class"; the camp keeps the generic word.
    "group": {"one": "group", "other": "groups"},
    # ``Program`` is a year or a season to the people administering it, but
    # "program" means a curriculum to most educators.
    "program": {"one": "program", "other": "programs"},
    # Role nouns, for screens that name a role in prose. These do NOT rename
    # ``Membership.role`` slugs, which route templates and derive capabilities.
    "counselor": {"one": "counselor", "other": "counselors"},
    "unit_head": {"one": "unit head", "other": "unit heads"},
    "camper_care": {"one": "Camper Care", "other": "Camper Care"},
    "leadership": {"one": "Leadership", "other": "Leadership"},
    "staff": {"one": "staff", "other": "staff"},
}


def _normalize(override: Any, default: dict[str, str]) -> dict[str, str]:
    """Coerce one org override into ``{one, other}``, falling back per form."""
    if isinstance(override, str):
        override = {"one": override, "other": override}
    if not isinstance(override, dict):
        return dict(default)
    one = str(override.get("one") or "").strip()
    other = str(override.get("other") or "").strip()
    # ``other`` inherits a *supplied* ``one`` (collectives like "Ed Team" that
    # don't pluralize), but never a defaulted one -- otherwise an org that sets
    # only ``other`` would silently lose the default plural.
    return {
        "one": one or default["one"],
        "other": other or one or default["other"],
    }


def terms_for_organization(org: Any | None) -> dict[str, dict[str, str]]:
    """Defaults merged with this org's overrides, one entry per canonical key."""
    raw = (getattr(org, "settings", None) or {}).get("terminology") if org else None
    overrides = raw if isinstance(raw, dict) else {}
    return {
        key: _normalize(overrides.get(key), default)
        for key, default in DEFAULT_TERMS.items()
    }


def term(
    org: Any | None,
    key: str,
    *,
    plural: bool = False,
    capitalize: bool = False,
) -> str:
    """Render one canonical key for ``org``; unknown keys return themselves."""
    forms = terms_for_organization(org).get(key)
    if forms is None:
        return key
    value = forms["other"] if plural else forms["one"]
    if capitalize and value:
        return value[0].upper() + value[1:]
    return value

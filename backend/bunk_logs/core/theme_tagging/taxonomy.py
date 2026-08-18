"""Fixed theme taxonomy for reflection tagging (Growth Dashboard by Grade Level).

The taxonomy is a versioned code constant rather than a database table so
that cross-grade comparisons stay stable for a whole program year. Editing
it mid-year would silently change what a cohort's numbers mean, so a change
must bump :data:`TAXONOMY_VERSION` and be followed by a
``backfill_reflection_themes --retag`` run.

``complexity_tier`` is the one editorial input in the whole feature: tier 1
themes are the fundamentals a brand-new Madrich wrestles with, tier 3 are
challenges that require real judgement. The dashboard averages it into a
per-grade concern-complexity index -- the actual developmental milestones are
derived from cohort data, not declared here.

Labels use the ``{"en": ...}`` shape from ``ReflectionTemplate.schema`` so
Hebrew can be added without a data migration.
"""

from __future__ import annotations

TAXONOMY_VERSION = "v1"

# Only text fields carrying these dashboard roles get tagged. Ratings are
# already numeric and aggregate without an LLM.
TAGGED_DASHBOARD_ROLES: tuple[str, ...] = ("open_concern", "wins", "improvements")

# Field types we can hand to the LLM. Everything else (ratings, dates) is
# skipped even when it carries a tagged dashboard_role.
TAGGABLE_FIELD_TYPES: tuple[str, ...] = ("text", "textarea", "text_list")

# Cap per field so one rambling answer can't dominate a grade's theme mix.
MAX_THEMES_PER_FIELD = 3

FALLBACK_THEME_KEY = "other"

THEME_TAXONOMY_V1: tuple[dict, ...] = (
    {
        "key": "logistics_scheduling",
        "complexity_tier": 1,
        "labels": {"en": "Logistics, schedule & attendance"},
    },
    {
        "key": "own_confidence",
        "complexity_tier": 1,
        "labels": {"en": "Own confidence & readiness"},
    },
    {
        "key": "classroom_management",
        "complexity_tier": 1,
        "labels": {"en": "Classroom management & behavior"},
    },
    {
        "key": "lesson_content",
        "complexity_tier": 2,
        "labels": {"en": "Lesson content & Judaic knowledge"},
    },
    {
        "key": "student_engagement",
        "complexity_tier": 2,
        "labels": {"en": "Student engagement & motivation"},
    },
    {
        "key": "peer_coteaching",
        "complexity_tier": 2,
        "labels": {"en": "Working with co-madrichim"},
    },
    {
        "key": "adult_supervision",
        "complexity_tier": 2,
        "labels": {"en": "Support from teachers & Director"},
    },
    {
        "key": "conflict_resolution",
        "complexity_tier": 3,
        "labels": {"en": "Conflict & difficult conversations"},
    },
    {
        "key": "family_communication",
        "complexity_tier": 3,
        "labels": {"en": "Communication with families"},
    },
    {
        "key": "personal_growth",
        "complexity_tier": 3,
        "labels": {"en": "Personal growth & goals"},
    },
    {
        "key": FALLBACK_THEME_KEY,
        "complexity_tier": 1,
        "labels": {"en": "Other"},
    },
)

_BY_KEY: dict[str, dict] = {theme["key"]: theme for theme in THEME_TAXONOMY_V1}


def theme_keys() -> tuple[str, ...]:
    """Valid theme keys for the current taxonomy version."""
    return tuple(_BY_KEY)


def is_valid_theme(key: str) -> bool:
    return key in _BY_KEY


def theme_label(key: str, language: str = "en") -> str:
    """Human label for ``key``, falling back to English then to the key itself."""
    theme = _BY_KEY.get(key)
    if theme is None:
        return key
    labels = theme.get("labels") or {}
    return labels.get(language) or labels.get("en") or key


def complexity_tier(key: str) -> int:
    """Editorial sophistication rank for ``key``; unknown keys read as tier 1."""
    theme = _BY_KEY.get(key)
    if theme is None:
        return 1
    return int(theme.get("complexity_tier") or 1)


def taxonomy_payload(language: str = "en") -> list[dict]:
    """Serialise the taxonomy for API responses so the UI can label + order."""
    return [
        {
            "key": theme["key"],
            "label": theme_label(theme["key"], language),
            "complexity_tier": complexity_tier(theme["key"]),
        }
        for theme in THEME_TAXONOMY_V1
    ]


def taggable_fields(schema: dict | None) -> list[dict]:
    """Return the schema fields eligible for theme tagging.

    A field qualifies when it carries one of :data:`TAGGED_DASHBOARD_ROLES`
    and is one of :data:`TAGGABLE_FIELD_TYPES`.
    """
    fields = (schema or {}).get("fields") or []
    out: list[dict] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        if field.get("dashboard_role") not in TAGGED_DASHBOARD_ROLES:
            continue
        if field.get("type") not in TAGGABLE_FIELD_TYPES:
            continue
        if not field.get("key"):
            continue
        out.append(field)
    return out

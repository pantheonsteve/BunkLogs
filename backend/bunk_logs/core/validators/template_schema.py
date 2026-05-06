"""Validate ReflectionTemplate.schema against the v1 field type spec."""
from __future__ import annotations

import re
from typing import Any

from django.core.exceptions import ValidationError

# Field types that use prompts (user-facing label text per language)
_PROMPTS_TYPES = frozenset(
    {
        "text",
        "textarea",
        "text_list",
        "single_choice",
        "multiple_choice",
        "yes_no",
        "date",
        "number",
        "section_header",
        "instructions",
    },
)
# Field types that use scale_labels instead of prompts
_SCALE_TYPES = frozenset({"rating_group", "single_rating"})

# Types whose fields are not collected as answer data
META_FIELD_TYPES = frozenset({"section_header", "instructions"})

# All valid field types
ALL_FIELD_TYPES = _PROMPTS_TYPES | _SCALE_TYPES

DASHBOARD_ROLES = frozenset(
    {"primary_rating", "category_ratings", "wins", "improvements", "open_concern"},
)
# Maps dashboard_role → set of field types that may carry it
DASHBOARD_ROLE_ALLOWED_TYPES: dict[str, frozenset[str]] = {
    "primary_rating": frozenset({"single_rating"}),
    "category_ratings": frozenset({"rating_group"}),
    "wins": frozenset({"text_list"}),
    "improvements": frozenset({"text_list"}),
    "open_concern": frozenset({"text", "textarea"}),
}

RESERVED_KEYS = frozenset(
    {
        "id",
        "created_at",
        "updated_at",
        "submitted_at",
        "submitted_by",
        "template",
        "program",
        "person",
        "organization",
    },
)

_NON_WORD = re.compile(r"[^a-z0-9]+")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_prompts(field: dict, loc: str) -> None:
    prompts = field.get("prompts")
    if not isinstance(prompts, dict) or len(prompts) < 1:
        raise ValidationError(
            {"schema": f"Field requires prompts with at least one language code {loc}."},
        )


def _validate_scale(field: dict, ftype: str, loc: str) -> None:
    scale = field.get("scale")
    if (
        not isinstance(scale, list)
        or len(scale) != 2
        or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in scale)
        or scale[0] >= scale[1]
    ):
        raise ValidationError(
            {"schema": f"{ftype} requires scale as [min, max] with min < max {loc}."},
        )
    labels = field.get("scale_labels")
    if not isinstance(labels, dict) or len(labels) < 1:
        raise ValidationError(
            {"schema": f"{ftype} requires scale_labels with at least one language {loc}."},
        )
    for lang, vals in labels.items():
        if not lang or not isinstance(vals, list):
            raise ValidationError(
                {"schema": f"scale_labels must map language codes to lists {loc}."},
            )


def _validate_rating_group(field: dict, loc: str) -> None:
    _validate_scale(field, "rating_group", loc)
    cats = field.get("categories")
    if not isinstance(cats, list) or not cats:
        raise ValidationError(
            {"schema": f"rating_group requires a non-empty categories array {loc}."},
        )
    for j, cat in enumerate(cats):
        if not isinstance(cat, dict):
            raise ValidationError(
                {"schema": f"categories[{j}] must be an object {loc}."},
            )
        ckey = cat.get("key")
        if not isinstance(ckey, str) or not ckey.strip():
            raise ValidationError(
                {"schema": f"categories[{j}] requires a non-empty key {loc}."},
            )
        clabels = cat.get("labels")
        if not isinstance(clabels, dict) or len(clabels) < 1:
            raise ValidationError(
                {"schema": f"categories[{j}] requires labels with at least one language {loc}."},
            )


def _validate_options(field: dict, ftype: str, loc: str) -> None:
    options = field.get("options")
    if not isinstance(options, list) or not options:
        raise ValidationError(
            {"schema": f"{ftype} requires a non-empty options list {loc}."},
        )
    for k, opt in enumerate(options):
        if not isinstance(opt, dict):
            raise ValidationError({"schema": f"options[{k}] must be an object {loc}."})
        # Accept either "key" (new spec) or "value" (legacy) as the option identifier
        opt_id = opt.get("key") or opt.get("value")
        if not isinstance(opt_id, str) or not opt_id.strip():
            raise ValidationError(
                {"schema": f"options[{k}] requires a non-empty key or value {loc}."},
            )
        labels = opt.get("labels")
        if not isinstance(labels, dict) or len(labels) < 1:
            raise ValidationError(
                {"schema": f"options[{k}] requires labels with at least one language {loc}."},
            )


def _validate_language_coverage(
    field: dict, ftype: str, languages: list[str], loc: str,
) -> None:
    """Ensure every declared language is present in this field's locale data."""
    if ftype == "rating_group":
        labels = field.get("scale_labels") or {}
        for lang in languages:
            if lang not in labels:
                raise ValidationError(
                    {"schema": f'scale_labels missing language "{lang}" {loc}.'},
                )
        for j, cat in enumerate(field.get("categories") or []):
            if not isinstance(cat, dict):
                continue
            clabels = cat.get("labels") or {}
            for lang in languages:
                if lang not in clabels:
                    raise ValidationError(
                        {
                            "schema": (
                                f'categories[{j}] labels missing language '
                                f'"{lang}" {loc}.'
                            ),
                        },
                    )
    elif ftype == "single_rating":
        labels = field.get("scale_labels") or {}
        for lang in languages:
            if lang not in labels:
                raise ValidationError(
                    {"schema": f'scale_labels missing language "{lang}" {loc}.'},
                )
    else:
        prompts = field.get("prompts") or {}
        for lang in languages:
            if lang not in prompts:
                raise ValidationError(
                    {"schema": f'prompts missing language "{lang}" {loc}.'},
                )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_template_schema(schema: Any, languages: list[str]) -> None:
    """Validate a ReflectionTemplate schema dict against the v1 field type spec.

    Raises ``django.core.exceptions.ValidationError`` with field-specific messages.

    Args:
        schema:    The value of ``ReflectionTemplate.schema`` (must be a dict).
        languages: Declared language codes from ``ReflectionTemplate.languages``.
                   When non-empty, every field's locale data must cover all listed
                   codes.
    """
    if not isinstance(schema, dict):
        raise ValidationError({"schema": "Schema must be a JSON object."})
    fields = schema.get("fields")
    if not isinstance(fields, list) or len(fields) == 0:
        raise ValidationError(
            {"schema": 'Schema must include a non-empty "fields" array.'},
        )

    seen_keys: set[str] = set()

    for i, field in enumerate(fields):
        loc = f"(field index {i})"
        if not isinstance(field, dict):
            raise ValidationError({"schema": f"Each field must be an object {loc}."})

        # Key validation
        key = field.get("key")
        if not isinstance(key, str) or not key.strip():
            raise ValidationError(
                {"schema": f"Each field requires a non-empty string key {loc}."},
            )
        if key in RESERVED_KEYS:
            raise ValidationError(
                {"schema": f'Key "{key}" is reserved and cannot be used {loc}.'},
            )
        if key in seen_keys:
            raise ValidationError(
                {"schema": f'Duplicate key "{key}" {loc}.'},
            )
        seen_keys.add(key)

        # Type validation
        ftype = field.get("type")
        if ftype not in ALL_FIELD_TYPES:
            raise ValidationError(
                {
                    "schema": (
                        f"Unknown or missing type {loc}; allowed: "
                        f"{', '.join(sorted(ALL_FIELD_TYPES))}."
                    ),
                },
            )

        # dashboard_role validation
        dashboard_role = field.get("dashboard_role")
        if dashboard_role is not None:
            if dashboard_role not in DASHBOARD_ROLES:
                raise ValidationError(
                    {
                        "schema": (
                            f'Invalid dashboard_role "{dashboard_role}" {loc}; '
                            f"allowed: {', '.join(sorted(DASHBOARD_ROLES))}."
                        ),
                    },
                )
            allowed = DASHBOARD_ROLE_ALLOWED_TYPES[dashboard_role]
            if ftype not in allowed:
                raise ValidationError(
                    {
                        "schema": (
                            f'dashboard_role "{dashboard_role}" is not valid for '
                            f'type "{ftype}" {loc}; allowed on: '
                            f"{', '.join(sorted(allowed))}."
                        ),
                    },
                )

        # Type-specific structural validation
        if ftype == "rating_group":
            _validate_rating_group(field, loc)
        elif ftype == "single_rating":
            _validate_scale(field, "single_rating", loc)
        else:
            _validate_prompts(field, loc)
            if ftype in ("single_choice", "multiple_choice"):
                _validate_options(field, ftype, loc)

        # Language coverage check (only when languages are declared)
        if languages:
            _validate_language_coverage(field, ftype, languages, loc)


# ---------------------------------------------------------------------------
# Field key registry hints (DB-aware, non-blocking)
# ---------------------------------------------------------------------------


def check_field_key_hints(schema: Any, org) -> list[str]:
    """Return a list of warning strings for type mismatches with the FieldKey registry.

    Does NOT raise — callers surface these as non-blocking warnings in API responses.

    Args:
        schema: A validated ReflectionTemplate.schema dict.
        org:    The Organization instance (or None) for the current request.
    """
    from django.db.models import Q

    from bunk_logs.core.models import FieldKey

    if not isinstance(schema, dict):
        return []
    fields = schema.get("fields")
    if not isinstance(fields, list):
        return []

    if org is not None:
        registry_qs = FieldKey.all_objects.filter(
            Q(organization=org) | Q(organization__isnull=True),
        )
    else:
        registry_qs = FieldKey.all_objects.filter(organization__isnull=True)

    registry: dict[str, FieldKey] = {fk.key: fk for fk in registry_qs}

    warnings: list[str] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        key = field.get("key")
        ftype = field.get("type")
        if not isinstance(key, str) or not isinstance(ftype, str):
            continue
        registered = registry.get(key)
        if registered and registered.expected_field_type and registered.expected_field_type != ftype:
            warnings.append(
                f'Field "{key}" uses type "{ftype}" but the registry expects '
                f'"{registered.expected_field_type}" for this key.',
            )
    return warnings

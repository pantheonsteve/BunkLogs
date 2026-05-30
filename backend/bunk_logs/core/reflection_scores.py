"""Reflection score extraction primitives shared across role dashboards.

Counselor, Unit Head, Camper Care, Leadership Team, and Admin all need to
pull numeric ratings out of a ``Reflection.answers`` JSON blob given the
matching template schema. Each surface uses ratings slightly differently
(score grid vs trend graph vs concerns vs aggregations) but they all
share the same input → numeric extraction logic.

These helpers were duplicated across ``api/dashboards/subject.py`` and
``api/dashboards/trends.py`` before the Unit Head flow needed a third
copy. Centralising here lets every role dashboard call into one
canonical extractor, so a change to (say) how ``rating_group`` averaging
behaves only needs to land once.

Conventions
-----------

A template field is *scored* when ``type`` is ``single_rating`` or
``rating_group``. The "scale" for both is read from the field's
``scale`` array (``[min, max]``) with a default of ``[1, 5]``.

For a score grid (UH Story 12) we want **every** scored cell — one
column per ``single_rating`` and one column per ``rating_group``
category. :func:`resolve_rating_cells` returns that flat ``{label:
value}`` projection.

For a trend graph (UH Story 13) we typically collapse to a single
numeric per reflection — either the ``primary_rating`` field or an
average across ``rating_group`` categories. :func:`reduce_rating` does
that collapse.

To enumerate the columns of a score grid without inspecting individual
answers, use :func:`iter_scored_fields` which yields ``(field, label,
scale_max)`` triples in template order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bunk_logs.core.models import ReflectionTemplate


SCORED_FIELD_TYPES = frozenset({"single_rating", "rating_group"})
GRID_META_FIELD_TYPES = frozenset({"section_header", "instructions"})


def scale_max(field: dict) -> int:
    """Return the inclusive upper bound of ``field['scale']`` (default 5).

    Used by the frontend ``ratingColor()`` palette selector and by the
    backend trend grid to size the legend. Anything that yields a
    non-integer falls back to 5 — the canonical Crane Lake scale.
    """
    scale = field.get("scale") or [1, 5]
    try:
        return int(scale[-1])
    except (IndexError, ValueError, TypeError):
        return 5


def find_field_by_dashboard_role(
    template: ReflectionTemplate, role: str,
) -> dict | None:
    """Return the first schema field with ``dashboard_role == role``, if any.

    Templates surface specific scored fields onto dashboards by tagging
    them: ``primary_rating`` for the main scalar shown in score cards,
    ``category_ratings`` for the multi-dimensional row, ``open_concern``
    for the supervisor-flag textarea, etc. The convention lets a single
    Camper Dashboard payload work across templates that use different
    field keys.
    """
    for f in (template.schema or {}).get("fields") or []:
        if isinstance(f, dict) and f.get("dashboard_role") == role:
            return f
    return None


def iter_scored_fields(
    template: ReflectionTemplate,
) -> Iterator[tuple[dict, str, int]]:
    """Yield ``(field, label, scale_max)`` for every scored cell in the template.

    Labels mirror the keying convention used by
    :func:`resolve_rating_cells` so a caller can build a column list
    that matches the per-reflection extracted dict. Single ratings use
    the field key as the label; rating groups expand to one label per
    category, formatted as ``"<field_key>__<category_key>"``.

    Order is template-defined (the order fields appear in
    ``schema['fields']``); a UH score grid relies on that order to
    render columns in a stable, template-author-controlled sequence
    (Story 12 criterion 7 forbids reordering by the viewer).
    """
    for field in (template.schema or {}).get("fields") or []:
        if not isinstance(field, dict):
            continue
        ftype = field.get("type")
        if ftype not in SCORED_FIELD_TYPES:
            continue
        fkey = field.get("key")
        if not isinstance(fkey, str):
            continue
        sm = scale_max(field)
        if ftype == "single_rating":
            yield field, fkey, sm
        else:
            for cat in field.get("categories") or []:
                if not isinstance(cat, dict):
                    continue
                ck = cat.get("key")
                if not isinstance(ck, str):
                    continue
                yield field, f"{fkey}__{ck}", sm


def iter_grid_fields(
    template: ReflectionTemplate,
) -> Iterator[tuple[dict, str, int | None]]:
    """Yield ``(field, label, scale_max)`` for every score-grid column.

    Scored fields expand the same way as :func:`iter_scored_fields`.
    All other answerable template fields (text, textarea, yes_no, etc.)
    yield one column keyed by the field key with ``scale_max=None``.
    Section headers and instructions are skipped.
    """
    for field in (template.schema or {}).get("fields") or []:
        if not isinstance(field, dict):
            continue
        ftype = field.get("type")
        if ftype in GRID_META_FIELD_TYPES:
            continue
        fkey = field.get("key")
        if not isinstance(fkey, str):
            continue
        if ftype in SCORED_FIELD_TYPES:
            sm = scale_max(field)
            if ftype == "single_rating":
                yield field, fkey, sm
            else:
                for cat in field.get("categories") or []:
                    if not isinstance(cat, dict):
                        continue
                    ck = cat.get("key")
                    if not isinstance(ck, str):
                        continue
                    yield field, f"{fkey}__{ck}", sm
        else:
            yield field, fkey, None


def resolve_grid_cells(field: dict, answers: dict) -> dict[str, float | str | None]:
    """Pull one or more grid cell values out of an answers blob for ``field``."""
    ftype = field.get("type")
    if ftype in SCORED_FIELD_TYPES:
        return resolve_rating_cells(field, answers)
    fkey = field.get("key")
    if not isinstance(fkey, str):
        return {}
    return {fkey: format_grid_cell_value(field, (answers or {}).get(fkey))}


def format_grid_cell_value(field: dict, value: object) -> str | None:
    """Render a non-scored answer for display in the score grid."""
    if value is None:
        return None
    ftype = field.get("type")
    if ftype == "yes_no":
        if isinstance(value, bool):
            return "Yes" if value else "No"
        s = str(value).strip().lower()
        if s in {"yes", "true", "1"}:
            return "Yes"
        if s in {"no", "false", "0"}:
            return "No"
        return str(value).strip() or None
    if ftype == "text_list":
        if isinstance(value, list):
            items = [str(v).strip() for v in value if str(v).strip()]
            return "\n".join(f"• {item}" for item in items) if items else None
        return str(value).strip() or None
    if ftype == "multiple_choice":
        if isinstance(value, list):
            joined = ", ".join(str(v).strip() for v in value if str(v).strip())
            return joined or None
        return str(value).strip() or None
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)) and ftype == "number":
        return str(value)
    if isinstance(value, str):
        return value.strip() or None
    return str(value) if value is not None else None


def resolve_rating_cells(field: dict, answers: dict) -> dict[str, float | None]:
    """Pull numeric rating cells out of an answers blob for a given field.

    Returns a flat ``{label: value}`` projection:

    * ``single_rating`` → one entry keyed by the field key.
    * ``rating_group`` → one entry per category keyed
      ``"<field_key>__<category_key>"``.

    Missing or non-numeric values resolve to ``None`` rather than being
    omitted so the score grid can distinguish "no submission" from "no
    answer" by checking whether the label appears in the dict at all.
    """
    ftype = field.get("type")
    fkey = field.get("key")
    out: dict[str, float | None] = {}
    if ftype == "single_rating":
        v = answers.get(fkey)
        out[fkey] = _as_float(v)
        return out
    if ftype == "rating_group":
        block = answers.get(fkey) if isinstance(answers.get(fkey), dict) else {}
        for cat in field.get("categories") or []:
            ck = cat.get("key") if isinstance(cat, dict) else None
            if ck is None:
                continue
            label = f"{fkey}__{ck}"
            out[label] = _as_float(block.get(ck) if isinstance(block, dict) else None)
    return out


def reduce_rating(
    answers: dict,
    primary: dict | None,
    category: dict | None,
    category_key: str | None = None,
) -> float | None:
    """Collapse an answers blob to a single numeric for trend visualisation.

    Resolution order:

    1. If ``primary`` is provided and its value is numeric, return it.
    2. Else if ``category`` is provided:
       * with ``category_key`` → return that single category's value.
       * without → average across all configured categories.
    3. Else → ``None`` (no data this day).

    Matches the trend-grid contract: one numeric per (subject, date) so
    the heat grid can colour cells via the shared palette. Callers that
    want every cell (score grid) should use :func:`resolve_rating_cells`
    instead.
    """
    if primary is not None:
        v = _as_float(answers.get(primary.get("key")))
        if v is not None:
            return v
    if category is not None:
        block = answers.get(category.get("key"))
        if not isinstance(block, dict):
            return None
        if category_key:
            return _as_float(block.get(category_key))
        vals: list[float] = []
        for cat in category.get("categories") or []:
            ck = cat.get("key") if isinstance(cat, dict) else None
            if ck is None:
                continue
            v = _as_float(block.get(ck))
            if v is not None:
                vals.append(v)
        if vals:
            return sum(vals) / len(vals)
    return None


def _as_float(value: object) -> float | None:
    """Numeric cast that rejects bool. Used everywhere a rating must not be 0/1 from a bool."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None

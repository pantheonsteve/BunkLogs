"""Per-subject detail dashboard.

GET /api/v1/dashboards/subject/{person_id}/?date_start=&date_end=

Returns all reflections about ``person_id`` (visible to viewer), grouped by
template, plus per-rating-field time series, recent text responses, and a
``concerning_patterns`` array (low ratings + downward trends) — used to surface
campers who may need a check-in.

No scipy dependency: trend detection is a simple two-window average compare.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from datetime import timedelta
from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection

DEFAULT_WINDOW_DAYS = 30
MAX_WINDOW_DAYS = 90
LOW_RATING_LOOKBACK_DAYS = 14
TREND_LOOKBACK_DAYS = 14
TREND_DELTA_THRESHOLD = 0.5
MIN_REFLECTIONS_PER_HALF_FOR_TREND = 3
RECENT_TEXT_LIMIT = 30


def _parse_date(s: str | None, default: date) -> date:
    if not s:
        return default
    try:
        return date.fromisoformat(s)
    except ValueError:
        return default


def _resolve_rating(field: dict, answers: dict) -> dict[str, float | None]:
    """Pull numeric ratings out of an answers blob for a given schema field.

    Returns a flat dict ``{label: value}`` — for ``single_rating`` a single
    entry under the field key, for ``rating_group`` one entry per category
    keyed as ``"<field_key>__<cat_key>"``.
    """
    ftype = field.get("type")
    fkey = field.get("key")
    out: dict[str, float | None] = {}
    if ftype == "single_rating":
        v = answers.get(fkey)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[fkey] = float(v)
        else:
            out[fkey] = None
    elif ftype == "rating_group":
        block = answers.get(fkey) if isinstance(answers.get(fkey), dict) else {}
        for cat in field.get("categories") or []:
            ck = cat.get("key") if isinstance(cat, dict) else None
            if ck is None:
                continue
            v = block.get(ck) if isinstance(block, dict) else None
            label = f"{fkey}__{ck}"
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[label] = float(v)
            else:
                out[label] = None
    return out


def _detect_concerning_patterns(
    series_by_label: dict[str, list[tuple[date, float, int, int | None]]],
    today: date,
) -> list[dict[str, Any]]:
    """Two-rule detection: any rating==1 in last 14d, or recent half lower than prior half.

    series_by_label[label] is a list of (date, value, reflection_id, scale_max, team_visibility).
    """
    patterns: list[dict[str, Any]] = []
    low_cutoff = today - timedelta(days=LOW_RATING_LOOKBACK_DAYS - 1)
    for label, points in series_by_label.items():
        # Any rating of 1 in last 14 days
        for d, v, ref_id, _scale, team_visibility in points:
            if d >= low_cutoff and v is not None and v <= 1.0:
                patterns.append({
                    "kind": "low_rating",
                    "field_label": label,
                    "date": d.isoformat(),
                    "value": v,
                    "reflection_id": ref_id,
                    "team_visibility": team_visibility,
                })
        # Downward trend: split last 14 days in half, require >=3 each
        recent_cutoff = today - timedelta(days=TREND_LOOKBACK_DAYS - 1)
        midpoint = today - timedelta(days=(TREND_LOOKBACK_DAYS // 2) - 1)
        recent_vals = [v for d, v, *_ in points if d >= midpoint and v is not None]
        prior_vals = [
            v for d, v, *_ in points
            if recent_cutoff <= d < midpoint and v is not None
        ]
        if (
            len(recent_vals) >= MIN_REFLECTIONS_PER_HALF_FOR_TREND
            and len(prior_vals) >= MIN_REFLECTIONS_PER_HALF_FOR_TREND
        ):
            recent_mean = sum(recent_vals) / len(recent_vals)
            prior_mean = sum(prior_vals) / len(prior_vals)
            if recent_mean < prior_mean - TREND_DELTA_THRESHOLD:
                patterns.append({
                    "kind": "downward_trend",
                    "field_label": label,
                    "recent_mean": round(recent_mean, 2),
                    "prior_mean": round(prior_mean, 2),
                })
    return patterns


class SubjectDetailView(APIView):
    """Cross-template aggregation for one subject Person."""

    permission_classes = [IsAuthenticated]

    def get(self, request, person_id: int, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)

        subject = Person.objects.filter(id=person_id).first()
        if subject is None:
            return Response({"detail": "Subject not found."}, status=404)

        today = date.today()
        cur_end = _parse_date(request.query_params.get("date_end"), today)
        cur_start = _parse_date(
            request.query_params.get("date_start"),
            cur_end - timedelta(days=DEFAULT_WINDOW_DAYS - 1),
        )
        if cur_end < cur_start:
            cur_start, cur_end = cur_end, cur_start
        if (cur_end - cur_start).days > MAX_WINDOW_DAYS - 1:
            cur_start = cur_end - timedelta(days=MAX_WINDOW_DAYS - 1)

        # Pull reflections about this subject within window, scoped to viewer
        refs = list(
            reflections_visible_for_user(
                request.user,
                Reflection.objects.filter(
                    subject_id=person_id,
                    period_end__gte=cur_start,
                    period_end__lte=cur_end,
                    is_complete=True,
                ).select_related("template", "author", "assignment_group"),
            ).order_by("period_end"),
        )

        if not refs:
            # 403 vs empty: if viewer has zero visible reflections of any kind for this
            # subject, that may legitimately be empty (subject not in a visible group).
            # We don't 403 — empty result is informative. Caller can render empty state.
            pass

        # Group by template
        by_template: dict[int, dict[str, Any]] = {}
        # series_by_label across ALL templates: used for concerning-pattern detection
        all_series: dict[str, list[tuple[date, float, int, int | None, str]]] = defaultdict(list)
        recent_texts: list[dict[str, Any]] = []

        for r in refs:
            tpl = r.template
            tpl_entry = by_template.get(tpl.id)
            if tpl_entry is None:
                tpl_entry = {
                    "template": {
                        "id": tpl.id,
                        "name": tpl.name,
                        "slug": tpl.slug,
                        "subject_mode": tpl.subject_mode,
                    },
                    "rating_series": defaultdict(list),
                    "reflections": [],
                }
                by_template[tpl.id] = tpl_entry
            schema_fields = (tpl.schema or {}).get("fields") or []
            for field in schema_fields:
                if not isinstance(field, dict):
                    continue
                ftype = field.get("type")
                if ftype not in ("single_rating", "rating_group"):
                    if ftype in ("text", "textarea"):
                        v = r.answers.get(field.get("key"))
                        if isinstance(v, str) and v.strip():
                            recent_texts.append({
                                "reflection_id": r.id,
                                "template_id": tpl.id,
                                "template_name": tpl.name,
                                "field_key": field.get("key"),
                                "dashboard_role": field.get("dashboard_role"),
                                "text": v.strip()[:1000],
                                "date": r.period_end.isoformat(),
                                "author_name": r.author.full_name if r.author else None,
                                "team_visibility": r.team_visibility,
                            })
                    continue
                ratings = _resolve_rating(field, r.answers)
                scale = field.get("scale") or [1, 5]
                try:
                    scale_max = int(scale[-1])
                except (IndexError, ValueError, TypeError):
                    scale_max = 5
                for label, value in ratings.items():
                    tpl_entry["rating_series"][label].append({
                        "date": r.period_end.isoformat(),
                        "value": value,
                        "reflection_id": r.id,
                        "scale_max": scale_max,
                        "team_visibility": r.team_visibility,
                    })
                    if value is not None:
                        all_series[label].append(
                            (r.period_end, value, r.id, scale_max, r.team_visibility),
                        )
            tpl_entry["reflections"].append({
                "id": r.id,
                "date": r.period_end.isoformat(),
                "author_name": r.author.full_name if r.author else None,
                "team_visibility": r.team_visibility,
                "assignment_group": (
                    {"id": r.assignment_group_id, "name": r.assignment_group.name}
                    if r.assignment_group_id else None
                ),
            })

        # Convert defaultdicts to lists for JSON serialization
        templates_out = []
        for entry in by_template.values():
            series = []
            for label, points in entry["rating_series"].items():
                series.append({
                    "label": label,
                    "scale_max": (points[0]["scale_max"] if points else 5),
                    "points": points,
                })
            entry["rating_series"] = series
            templates_out.append(entry)

        recent_texts.sort(key=lambda x: x["date"], reverse=True)
        recent_texts = recent_texts[:RECENT_TEXT_LIMIT]

        concerns = _detect_concerning_patterns(all_series, today)

        return Response({
            "subject": {
                "id": subject.id,
                "name": subject.full_name,
                "preferred_name": subject.preferred_name or subject.first_name,
            },
            "period": {"start": cur_start.isoformat(), "end": cur_end.isoformat()},
            "templates": templates_out,
            "recent_texts": recent_texts,
            "concerning_patterns": concerns,
        })

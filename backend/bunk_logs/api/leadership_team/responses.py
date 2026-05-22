"""LT Template Responses view (Step 7_12 PR B — Story 53).

``GET /api/v1/leadership-team/templates/<id>/responses/`` returns either:

* ``tab=individual`` — paginated reflections under a template (across
  versions), with filters: date range, respondent multi-select,
  language_of_authorship, ``rating_le``, ``has_free_text``.
* ``tab=aggregate`` — completion rate over time, avg rating per
  dimension (annotated with version-boundary markers when a dimension
  only exists in some versions), language distribution, response volume
  per period.

``combine_assignments=true`` includes responses from all assignments of
the same template slug rather than only the matching version chain.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING
from typing import Any

from django.db.models import Count
from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import person_display_name
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.reflection_scores import _as_float
from bunk_logs.core.reflection_scores import iter_scored_fields

from .common import viewer_or_403

if TYPE_CHECKING:
    from datetime import date


MAX_PAGE_SIZE = 100


def _template_versions(
    organization, template: ReflectionTemplate, *, combine: bool,
):
    """Return queryset of templates this response view covers.

    Without ``combine``, only the explicit template id (single version).
    With ``combine``, all versions under the same slug + org.
    """
    if not combine:
        return ReflectionTemplate.all_objects.filter(pk=template.pk)
    if template.organization_id is None:
        return ReflectionTemplate.all_objects.filter(
            organization__isnull=True, slug=template.slug,
        )
    return ReflectionTemplate.all_objects.filter(
        organization=organization, slug=template.slug,
    )


def _parse_filter_date(raw: str | None, *, field: str) -> date | None:
    if raw is None or not raw.strip():
        return None
    parsed = parse_date(raw)
    if parsed is None:
        msg = f"Invalid '{field}' filter — expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


class LeadershipTeamTemplateResponsesView(APIView):
    """Single endpoint with two tabs: ``individual`` and ``aggregate``."""

    permission_classes = [IsAuthenticated]

    def get(self, request, template_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        try:
            template = ReflectionTemplate.all_objects.get(pk=template_id)
        except ReflectionTemplate.DoesNotExist as exc:
            raise NotFound from exc

        combine = (
            request.query_params.get("combine_assignments") or ""
        ).lower() in {"1", "true"}
        templates_qs = _template_versions(
            ctx.organization, template, combine=combine,
        )

        reflections = reflections_visible_for_user(
            request.user,
            Reflection.objects.filter(
                organization=ctx.organization, template__in=templates_qs,
            ).select_related("template", "author", "subject"),
        )

        date_from = _parse_filter_date(
            request.query_params.get("date_from"), field="date_from",
        )
        date_to = _parse_filter_date(
            request.query_params.get("date_to"), field="date_to",
        )
        if date_from:
            reflections = reflections.filter(period_end__gte=date_from)
        if date_to:
            reflections = reflections.filter(period_start__lte=date_to)

        tab = (request.query_params.get("tab") or "individual").lower()
        if tab == "aggregate":
            return Response(self._aggregate(reflections, list(templates_qs)))
        return Response(self._individual(request, reflections, template))

    # ------------------------------------------------------------------
    # Individual tab
    # ------------------------------------------------------------------

    def _individual(self, request, reflections, template) -> dict[str, Any]:
        respondents = request.query_params.getlist("respondent")
        if respondents:
            reflections = reflections.filter(
                author_id__in=[r for r in respondents if r.isdigit()],
            )
        language = (request.query_params.get("language") or "").strip()
        if language:
            reflections = reflections.filter(language=language)
        rating_le_raw = request.query_params.get("rating_le")
        if rating_le_raw and rating_le_raw.lstrip("-").isdigit():
            rating_le = int(rating_le_raw)
            reflections = reflections.filter(
                pk__in=self._rating_filter_ids(reflections, rating_le),
            )
        has_free_text = (request.query_params.get("has_free_text") or "").lower()
        if has_free_text in {"1", "true"}:
            reflections = reflections.exclude(answers={})

        page = max(int(request.query_params.get("page") or 1), 1)
        size_raw = int(request.query_params.get("page_size") or 25)
        size = min(max(size_raw, 1), MAX_PAGE_SIZE)
        ordered = reflections.order_by("-period_end", "-updated_at")
        total = ordered.count()
        start = (page - 1) * size
        rows = list(ordered[start:start + size])

        return {
            "tab": "individual",
            "template": {"id": template.pk, "slug": template.slug},
            "total": total,
            "page": page,
            "page_size": size,
            "results": [self._serialize_row(r) for r in rows],
        }

    @staticmethod
    def _rating_filter_ids(reflections, threshold: int) -> list[int]:
        """Return IDs whose primary rating or any scored answer is <= threshold."""
        ids: list[int] = []
        for r in reflections.select_related("template").iterator():
            answers = r.answers or {}
            scored = list(iter_scored_fields(r.template))
            if not scored:
                continue
            for _f, _label, _scale in scored:
                val = _as_float(answers.get(_f.get("key")))
                if val is not None and val <= threshold:
                    ids.append(r.pk)
                    break
        return ids

    @staticmethod
    def _serialize_row(r: Reflection) -> dict[str, Any]:
        return {
            "id": r.pk,
            "period_start": r.period_start.isoformat() if r.period_start else None,
            "period_end": r.period_end.isoformat() if r.period_end else None,
            "language": r.language,
            "author": {
                "id": r.author_id,
                "name": person_display_name(r.author) if r.author_id else None,
            } if r.author_id else None,
            "subject": {
                "id": r.subject_id,
                "name": person_display_name(r.subject) if r.subject_id else None,
            } if r.subject_id else None,
            "template_version": r.template.version if r.template_id else None,
            "answers": r.answers or {},
        }

    # ------------------------------------------------------------------
    # Aggregate tab
    # ------------------------------------------------------------------

    def _aggregate(self, reflections, templates) -> dict[str, Any]:
        rows = list(reflections.values("pk", "language", "period_start", "answers", "template_id"))

        per_period: dict[date, int] = defaultdict(int)
        per_language: dict[str, int] = defaultdict(int)
        for r in rows:
            per_period[r["period_start"]] += 1
            per_language[r["language"] or "en"] += 1

        ratings_by_key: dict[str, list[float]] = defaultdict(list)
        valid_versions_by_key: dict[str, set[int]] = defaultdict(set)
        templates_by_id = {t.pk: t for t in templates}
        for r in rows:
            tpl = templates_by_id.get(r["template_id"])
            if tpl is None:
                continue
            for field, label, _ in iter_scored_fields(tpl):
                valid_versions_by_key[label].add(tpl.version)
                key = field.get("key")
                ftype = field.get("type")
                answers = r["answers"] or {}
                if ftype == "single_rating":
                    val = _as_float(answers.get(key))
                    if val is not None:
                        ratings_by_key[label].append(val)
                else:
                    block = answers.get(key) or {}
                    if isinstance(block, dict):
                        for cat in field.get("categories") or []:
                            ck = cat.get("key") if isinstance(cat, dict) else None
                            if ck is None:
                                continue
                            v = _as_float(block.get(ck))
                            if v is not None:
                                ratings_by_key[f"{key}__{ck}"].append(v)

        avg_per_dimension = [
            {
                "key": label,
                "avg": (sum(values) / len(values)) if values else None,
                "count": len(values),
                "versions": sorted(valid_versions_by_key.get(label, set())),
            }
            for label, values in sorted(ratings_by_key.items())
        ]

        return {
            "tab": "aggregate",
            "total_responses": len(rows),
            "response_volume_per_period": [
                {"period_start": k.isoformat(), "count": v}
                for k, v in sorted(per_period.items()) if k is not None
            ],
            "language_distribution": [
                {"language": k, "count": v}
                for k, v in sorted(per_language.items())
            ],
            "avg_rating_per_dimension": avg_per_dimension,
            "completion_rate_over_time": _completion_rate_over_time(reflections),
        }


def _completion_rate_over_time(reflections) -> list[dict[str, Any]]:
    """Crude completion-rate slice: completed / total grouped by week-of-period_start."""
    rows = (
        reflections.values("period_start")
        .annotate(
            total=Count("pk"),
            done=Count("pk", filter=Q(is_complete=True)),
        )
        .order_by("period_start")
    )
    return [
        {
            "period_start": row["period_start"].isoformat() if row["period_start"] else None,
            "completion_rate": (row["done"] / row["total"]) if row["total"] else 0,
            "total": row["total"],
            "done": row["done"],
        }
        for row in rows
    ]

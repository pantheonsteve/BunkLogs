"""LT CSV exports (Step 7_12 PR B — Story 48 c5/c6 + Story 53 c7).

Two distinct exports under ``/api/v1/leadership-team/``:

* ``GET teams/<team_role>/aggregate/export/`` — row-per-submission
  across a team's active published template version, including any
  available translated content alongside the original (LT13).
* ``GET templates/<id>/responses/export/?tab=individual|aggregate`` —
  one CSV per tab matching the on-screen Responses view, with the
  ``combine_assignments`` toggle honoured.

Both endpoints audit via ``audit.export`` so the trail captures which
filter set the LT used. Pattern mirrors
``api/dashboards/template.TemplateDashboardExportView``.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from bunk_logs.core import audit
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.reflection_scores import _as_float
from bunk_logs.core.reflection_scores import iter_scored_fields

from .common import admin_only_or_403
from .common import supervised_roles
from .common import viewer_or_403


def _csv_response(rows: list[list[Any]], header: list[str], *, filename: str) -> HttpResponse:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for r in rows:
        writer.writerow(r)
    resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


class LeadershipTeamTeamAggregateExportView(APIView):
    """``GET teams/<team_role>/aggregate/export/`` — row-per-submission CSV."""

    permission_classes = [IsAuthenticated]

    def get(self, request, team_role: str, *args, **kwargs):
        ctx = viewer_or_403(request)
        if team_role not in supervised_roles(ctx.membership, today=ctx.today):
            msg = "You do not supervise that team role."
            raise NotFound(msg)

        templates = list(
            ReflectionTemplate.all_objects.filter(
                role=team_role,
                status=ReflectionTemplate.Status.PUBLISHED,
            ).filter(
                organization__in=[ctx.organization, None],
            ),
        )
        if not templates:
            return _csv_response([], header=["no_template"], filename=f"{team_role}-aggregate.csv")

        reflections = reflections_visible_for_user(
            request.user,
            Reflection.objects.filter(
                organization=ctx.organization, template__in=templates,
            ).select_related("template", "author", "subject"),
        ).order_by("-period_end")

        translation_index = _translation_lookup(reflections)
        header = [
            "reflection_id",
            "template_slug",
            "template_version",
            "author",
            "subject",
            "period_start",
            "period_end",
            "language",
            "translated_language",
            "answers_original",
            "translated_text",
        ]
        rows = []
        for r in reflections:
            translation = translation_index.get(r.pk)
            rows.append([
                r.pk,
                r.template.slug,
                r.template.version,
                f"{getattr(r.author, 'first_name', '')} {getattr(r.author, 'last_name', '')}".strip(),
                f"{getattr(r.subject, 'first_name', '')} {getattr(r.subject, 'last_name', '')}".strip(),
                r.period_start.isoformat() if r.period_start else "",
                r.period_end.isoformat() if r.period_end else "",
                r.language or "",
                translation.target_language if translation else "",
                _flatten_answers(r.answers),
                translation.translated_text if translation else "",
            ])

        audit.export(
            actor=request.user,
            content_query={
                "endpoint": "leadership_team.team_aggregate_export",
                "team_role": team_role,
            },
            organization=ctx.organization,
            program=ctx.program,
        )
        return _csv_response(
            rows, header=header, filename=f"{team_role}-aggregate.csv",
        )


class LeadershipTeamTemplateResponsesExportView(APIView):
    """``GET templates/<id>/responses/export/`` — CSV matching the Responses tab."""

    permission_classes = [IsAuthenticated]

    def get(self, request, template_id: int, *args, **kwargs):
        ctx = admin_only_or_403(request)
        try:
            template = ReflectionTemplate.all_objects.get(pk=template_id)
        except ReflectionTemplate.DoesNotExist as exc:
            raise NotFound from exc

        combine = (
            request.query_params.get("combine_assignments") or ""
        ).lower() in {"1", "true"}
        if not combine:
            templates_qs = ReflectionTemplate.all_objects.filter(pk=template.pk)
        elif template.organization_id is None:
            templates_qs = ReflectionTemplate.all_objects.filter(
                organization__isnull=True, slug=template.slug,
            )
        else:
            templates_qs = ReflectionTemplate.all_objects.filter(
                organization=ctx.organization, slug=template.slug,
            )

        reflections = reflections_visible_for_user(
            request.user,
            Reflection.objects.filter(
                organization=ctx.organization, template__in=templates_qs,
            ).select_related("template", "author", "subject"),
        ).order_by("-period_end")
        date_from = parse_date(request.query_params.get("date_from") or "")
        date_to = parse_date(request.query_params.get("date_to") or "")
        if date_from:
            reflections = reflections.filter(period_end__gte=date_from)
        if date_to:
            reflections = reflections.filter(period_start__lte=date_to)

        tab = (request.query_params.get("tab") or "individual").lower()
        if tab == "aggregate":
            header, rows = _aggregate_rows(reflections, list(templates_qs))
            filename = f"{template.slug}-responses-aggregate.csv"
        else:
            header, rows = _individual_rows(reflections)
            filename = f"{template.slug}-responses-individual.csv"

        audit.export(
            actor=request.user,
            content_query={
                "endpoint": "leadership_team.template_responses_export",
                "template_id": template.pk,
                "tab": tab,
                "combine_assignments": combine,
            },
            organization=ctx.organization,
            program=ctx.program,
        )
        return _csv_response(rows, header=header, filename=filename)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _individual_rows(reflections):
    header = [
        "reflection_id",
        "template_slug",
        "template_version",
        "author",
        "subject",
        "period_start",
        "period_end",
        "language",
        "answers",
    ]
    rows = []
    for r in reflections:
        rows.append([
            r.pk,
            r.template.slug,
            r.template.version,
            f"{getattr(r.author, 'first_name', '')} {getattr(r.author, 'last_name', '')}".strip(),
            f"{getattr(r.subject, 'first_name', '')} {getattr(r.subject, 'last_name', '')}".strip(),
            r.period_start.isoformat() if r.period_start else "",
            r.period_end.isoformat() if r.period_end else "",
            r.language or "",
            _flatten_answers(r.answers),
        ])
    return header, rows


def _aggregate_rows(reflections, templates):
    """Header + rows for the aggregate CSV: one row per scored dimension."""
    header = [
        "dimension_key",
        "avg",
        "count",
        "valid_versions",
    ]
    by_key: dict[str, list[float]] = {}
    versions_by_key: dict[str, set[int]] = {}
    templates_by_id = {t.pk: t for t in templates}
    for r in reflections:
        tpl = templates_by_id.get(r.template_id)
        if tpl is None:
            continue
        for field, label, _scale in iter_scored_fields(tpl):
            versions_by_key.setdefault(label, set()).add(tpl.version)
            key = field.get("key")
            answers = r.answers or {}
            if field.get("type") == "single_rating":
                val = _as_float(answers.get(key))
                if val is not None:
                    by_key.setdefault(label, []).append(val)
            else:
                block = answers.get(key) or {}
                if isinstance(block, dict):
                    for cat in field.get("categories") or []:
                        ck = cat.get("key") if isinstance(cat, dict) else None
                        if ck is None:
                            continue
                        v = _as_float(block.get(ck))
                        if v is not None:
                            by_key.setdefault(f"{key}__{ck}", []).append(v)

    rows = []
    for label in sorted(by_key.keys()):
        values = by_key[label]
        avg = sum(values) / len(values) if values else ""
        versions = sorted(versions_by_key.get(label, set()))
        rows.append([
            label,
            f"{avg:.2f}" if isinstance(avg, float) else avg,
            len(values),
            ",".join(str(v) for v in versions),
        ])
    return header, rows


def _flatten_answers(answers) -> str:
    """Compact key=value list for CSV cells (preserves nested rating groups)."""
    if not isinstance(answers, dict):
        return ""
    parts: list[str] = []
    for k, v in answers.items():
        if isinstance(v, dict):
            for ck, cv in v.items():
                parts.append(f"{k}.{ck}={cv}")
        else:
            parts.append(f"{k}={v}")
    return "; ".join(parts)


def _translation_lookup(reflections) -> dict[int, Any]:
    """Map reflection_id -> TranslationRecord (latest by created_at)."""
    from bunk_logs.core.models import TranslationRecord

    ids = [r.pk for r in reflections]
    if not ids:
        return {}
    out: dict[int, Any] = {}
    qs = TranslationRecord.all_objects.filter(
        content_type="reflection",
        content_id__in=[str(i) for i in ids],
        status=TranslationRecord.Status.COMPLETED,
    ).order_by("-created_at")
    for tr in qs:
        try:
            rid = int(tr.content_id)
        except (TypeError, ValueError):
            continue
        out.setdefault(rid, tr)
    return out

"""Per-subject detail dashboard.

GET /api/v1/dashboards/subject/{person_id}/?date_start=&date_end=
GET /api/v1/dashboards/subject/{person_id}/export/?date_start=&date_end=

Returns all reflections about ``person_id`` (visible to viewer), grouped by
template, plus per-rating-field time series, recent text responses, and a
``concerning_patterns`` array (low ratings + downward trends) — used to surface
campers who may need a check-in.

No scipy dependency: trend detection is a simple two-window average compare.
"""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Any

from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import is_truthy_yes_no
from bunk_logs.core import audit
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.permissions.observation_read import filter_observations_readable
from bunk_logs.core.permissions.subject_dashboard import can_view_subject_dashboard
from bunk_logs.core.time_utils import get_org_timezone
from bunk_logs.notes.models import Observation

DEFAULT_WINDOW_DAYS = 30
MAX_WINDOW_DAYS = 90
MAX_REFLECTIONS_PER_SUBJECT = 200
LOW_RATING_LOOKBACK_DAYS = 14
TREND_LOOKBACK_DAYS = 14
TREND_DELTA_THRESHOLD = 0.5
MIN_REFLECTIONS_PER_HALF_FOR_TREND = 3
RECENT_TEXT_LIMIT = 30
MAX_OBSERVATIONS_PER_SUBJECT = 200
TEXT_FIELD_TYPES = frozenset({"text", "textarea", "long_text"})
SCORE_CATEGORY_KEYS = ("behavior", "participation", "social")
NARRATIVE_FIELD_KEYS = frozenset({"daily_report", "description"})
NARRATIVE_DASHBOARD_ROLES = frozenset({"open_concern"})
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _parse_date(s: str | None, default: date) -> date:
    if not s:
        return default
    try:
        return date.fromisoformat(s)
    except ValueError:
        return default


# Re-export the canonical helper from ``core.reflection_scores`` so existing
# call sites in this module keep working without touching the rest of the
# file. New callers should import directly from
# ``bunk_logs.core.reflection_scores``.
from bunk_logs.core.reflection_scores import resolve_rating_cells as _resolve_rating


@dataclass(frozen=True)
class SubjectDashboardContext:
    subject: Person
    viewer_person: Person | None
    org: Any
    cur_start: date
    cur_end: date


def _parse_period_from_request(request) -> tuple[date, date]:
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
    return cur_start, cur_end


def _get_subject_dashboard_context(
    request,
    person_id: int,
) -> tuple[SubjectDashboardContext | None, Response | None]:
    org = getattr(request, "organization", None)
    if org is None:
        return None, Response({"detail": "Organization context required."}, status=403)

    subject = Person.objects.filter(id=person_id).first()
    if subject is None:
        return None, Response({"detail": "Subject not found."}, status=404)

    if subject.organization_id != org.id:
        return None, Response({"detail": "Subject not found."}, status=404)

    viewer_person = Person.all_objects.filter(user=request.user).first()
    if not can_view_subject_dashboard(viewer_person, subject, org, request.user):
        return None, Response(
            {"detail": "You do not have permission to view this subject's dashboard."},
            status=403,
        )

    cur_start, cur_end = _parse_period_from_request(request)
    return SubjectDashboardContext(
        subject=subject,
        viewer_person=viewer_person,
        org=org,
        cur_start=cur_start,
        cur_end=cur_end,
    ), None


def _reflections_for_subject(
    user,
    person_id: int,
    cur_start: date,
    cur_end: date,
) -> list[Reflection]:
    return list(
        reflections_visible_for_user(
            user,
            Reflection.objects.filter(
                subject_id=person_id,
                period_end__gte=cur_start,
                period_end__lte=cur_end,
                is_complete=True,
            ).select_related("template", "author", "assignment_group"),
        ).order_by("period_end")[:MAX_REFLECTIONS_PER_SUBJECT],
    )


def _normalize_csv_cell(value: str) -> str:
    """Collapse whitespace/newlines so each CSV row stays on one physical line."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _narrative_text_fields(schema_fields: list, language: str) -> list[dict]:
    """Fields whose answers belong in the export ``full_text`` column.

    Prefer the main daily narrative (``daily_report`` / ``open_concern``) and
    skip short supplementary prompts such as "elaborate on why …".
    """
    text_fields = [
        f for f in schema_fields
        if isinstance(f, dict) and f.get("type") in TEXT_FIELD_TYPES
    ]
    daily = [f for f in text_fields if f.get("key") in NARRATIVE_FIELD_KEYS]
    if daily:
        return daily
    concern = [
        f for f in text_fields
        if f.get("dashboard_role") in NARRATIVE_DASHBOARD_ROLES
    ]
    if concern:
        return concern
    return [
        f for f in text_fields
        if "elaborate" not in _field_label(f, language).lower()
    ] or text_fields


def _strip_html(value: str) -> str:
    if not value:
        return ""
    text = strip_tags(value)
    text = _HTML_TAG_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _localized_label(labels: dict | str | None, language: str, fallback: str = "") -> str:
    if not labels:
        return fallback
    if isinstance(labels, str):
        return labels
    return labels.get(language) or labels.get("en") or next(iter(labels.values()), fallback)


def _field_label(field: dict, language: str) -> str:
    return _localized_label(
        field.get("prompts") or field.get("labels"),
        language,
        field.get("key", ""),
    )


def _format_reflection_flags(schema_fields: list, answers: dict, language: str) -> str:
    parts: list[str] = []
    for field in schema_fields:
        if isinstance(field, dict) and _is_yes_no_field(field):
            if is_truthy_yes_no(answers.get(field.get("key"))):
                parts.append(_field_label(field, language))
    return "; ".join(parts)


def _extract_category_scores(schema_fields: list, answers: dict) -> dict[str, Any]:
    """Pull behavior / participation / social from rating_group answers."""
    scores = {key: "" for key in SCORE_CATEGORY_KEYS}
    for field in schema_fields:
        if not isinstance(field, dict):
            continue
        if field.get("type") != "rating_group":
            continue
        block = answers.get(field.get("key")) or {}
        if not isinstance(block, dict):
            continue
        for cat_key in SCORE_CATEGORY_KEYS:
            val = block.get(cat_key)
            if val is not None and val != "":
                scores[cat_key] = val
    return scores


def _format_reflection_full_text(schema_fields: list, answers: dict, language: str) -> str:
    chunks: list[str] = []
    for field in _narrative_text_fields(schema_fields, language):
        raw = answers.get(field.get("key"))
        if not isinstance(raw, str) or not raw.strip():
            continue
        plain = _strip_html(raw.strip())
        if plain:
            chunks.append(plain)
    return _normalize_csv_cell("\n\n".join(chunks))


def _sortable_datetime(d: date, dt: datetime | None) -> datetime:
    if dt is not None and dt.tzinfo is not None:
        return dt
    naive = dt if dt is not None else datetime.combine(d, time.min)
    return timezone.make_aware(naive, timezone.get_current_timezone())


def _build_subject_entries_csv(
    *,
    subject_name: str,
    reflections: list[Reflection],
    observations: list[Observation],
) -> str:
    rows: list[tuple[date, datetime, list[Any]]] = []

    for r in reflections:
        schema_fields = (r.template.schema or {}).get("fields") or []
        language = r.language or "en"
        category_scores = _extract_category_scores(schema_fields, r.answers or {})
        rows.append((
            r.period_end,
            datetime.combine(r.period_end, time.min),
            [
                r.period_end.isoformat(),
                subject_name,
                "reflection",
                r.template.name if r.template else "",
                r.author.full_name if r.author else "",
                r.assignment_group.name if r.assignment_group else "",
                language,
                category_scores["behavior"],
                category_scores["participation"],
                category_scores["social"],
                _format_reflection_flags(schema_fields, r.answers or {}, language),
                _format_reflection_full_text(schema_fields, r.answers or {}, language),
                r.id,
            ],
        ))

    for o in observations:
        obs_date = o.observed_at.date() if o.observed_at else date.min
        rows.append((
            obs_date,
            o.observed_at or datetime.combine(obs_date, time.min),
            [
                obs_date.isoformat() if o.observed_at else "",
                subject_name,
                "observation",
                "",
                o.author.full_name if o.author else "",
                "",
                o.language or "",
                "",
                "",
                "",
                "",
                _normalize_csv_cell(_strip_html(o.body or "")),
                o.id,
            ],
        ))

    rows.sort(key=lambda item: _sortable_datetime(item[0], item[1]))

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "date",
        "subject_name",
        "entry_type",
        "template_name",
        "author_name",
        "assignment_group",
        "language",
        "behavior",
        "participation",
        "social",
        "flags",
        "full_text",
        "entry_id",
    ])
    for _, __, row in rows:
        writer.writerow(row)
    return "\ufeff" + out.getvalue()


def _subject_profile(subject: Person, organization) -> dict[str, Any]:
    """Non-PII profile block safe to expose to any viewer with reflection
    visibility. Emails / DOB stay in the admin-only people endpoint.
    """
    memberships = list(
        Membership.all_objects.filter(person=subject, is_active=True)
        .select_related("program")
        .order_by("-created_at"),
    )
    programs = [
        {
            "id": m.program_id,
            "name": m.program.name if m.program_id else None,
            "role": m.role,
        }
        for m in memberships
        if m.program_id is None or m.program.organization_id == organization.id
    ]
    primary_role = programs[0]["role"] if programs else None
    group_rows = list(
        AssignmentGroupMembership.all_objects.filter(
            person=subject, is_active=True, role_in_group="subject",
        )
        .select_related("group")
        .order_by("group__name"),
    )
    assignment_groups = [
        {
            "id": gm.group_id,
            "name": gm.group.name,
            "group_type": gm.group.group_type,
        }
        for gm in group_rows
        if gm.group and gm.group.organization_id == organization.id
    ]
    return {
        "id": subject.id,
        "full_name": subject.full_name,
        "preferred_name": subject.preferred_name or subject.first_name,
        "preferred_language": subject.preferred_language,
        "primary_role": primary_role,
        "programs": programs,
        "assignment_groups": assignment_groups,
    }


def _is_yes_no_field(field: dict) -> bool:
    """Yes/no flag field: ``yes_no`` type or two-option ``single_choice``."""
    if field.get("type") == "yes_no":
        return True
    if field.get("type") != "single_choice":
        return False
    options = field.get("options") or []
    if len(options) != 2:
        return False
    values = {str(o.get("value", "")).lower() for o in options if isinstance(o, dict)}
    return values == {"yes", "no"}


def _observations_for_viewer(
    viewer_person: Person | None,
    subject: Person,
    org,
    user,
    *,
    start: date,
    end: date,
    limit: int | None = MAX_OBSERVATIONS_PER_SUBJECT,
) -> list[dict[str, Any]]:
    """Return Observations about ``subject`` the viewer may read, newest first.

    Step 7_23 Profile feed: every observation the viewer may read about this
    person within ``start``..``end`` (org-TZ day buckets on ``observed_at``).
    """
    tz = get_org_timezone(org)
    range_start = datetime.combine(start, time.min, tzinfo=tz)
    range_end = datetime.combine(end, time.min, tzinfo=tz) + timedelta(days=1)
    base = (
        Observation.all_objects.filter(
            organization=org,
            subject_links__subject=subject,
            observed_at__gte=range_start,
            observed_at__lt=range_end,
        )
        .select_related("author")
        .prefetch_related("subject_links__subject")
    )
    qs = filter_observations_readable(base, viewer_person, org, user).order_by("-observed_at")
    if limit is not None:
        qs = qs[:limit]
    observations = list(qs)
    return [
        {
            "id": o.id,
            "body": o.body,
            "context": o.context,
            "sensitivity": o.sensitivity,
            "subject_visible": o.subject_visible,
            "amendment_of": o.amendment_of_id,
            "author": (
                {"id": o.author_id, "name": o.author.full_name}
                if o.author_id and o.author else None
            ),
            "observed_at": o.observed_at.isoformat() if o.observed_at else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in observations
    ]


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
        ctx, err = _get_subject_dashboard_context(request, person_id)
        if err is not None:
            return err
        assert ctx is not None
        subject = ctx.subject
        viewer_person = ctx.viewer_person
        org = ctx.org
        cur_start = ctx.cur_start
        cur_end = ctx.cur_end
        today = date.today()

        refs = _reflections_for_subject(request.user, person_id, cur_start, cur_end)

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
            schema_fields = (tpl.schema or {}).get("fields") or []
            if tpl_entry is None:
                flag_keys = [
                    f.get("key")
                    for f in schema_fields
                    if isinstance(f, dict) and _is_yes_no_field(f)
                ]
                tpl_entry = {
                    "template": {
                        "id": tpl.id,
                        "name": tpl.name,
                        "slug": tpl.slug,
                        "subject_mode": tpl.subject_mode,
                    },
                    "schema_fields": schema_fields,
                    "summary": {
                        "total_reflections": 0,
                        "flag_counts": {
                            k: {"yes": 0, "no": 0, "total": 0} for k in flag_keys
                        },
                    },
                    "rating_series": defaultdict(list),
                    "reflections": [],
                }
                by_template[tpl.id] = tpl_entry
            tpl_entry["summary"]["total_reflections"] += 1
            for fkey, counts in tpl_entry["summary"]["flag_counts"].items():
                raw = (r.answers or {}).get(fkey)
                if is_truthy_yes_no(raw):
                    counts["yes"] += 1
                    counts["total"] += 1
                elif raw is not None and str(raw).lower() == "no":
                    counts["no"] += 1
                    counts["total"] += 1
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
                "language": r.language,
                "answers": r.answers or {},
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

        observations = _observations_for_viewer(
            viewer_person, subject, org, request.user,
            start=cur_start, end=cur_end,
        )

        return Response({
            "subject": {
                "id": subject.id,
                "name": subject.full_name,
                "preferred_name": subject.preferred_name or subject.first_name,
            },
            "subject_profile": _subject_profile(subject, org),
            "period": {"start": cur_start.isoformat(), "end": cur_end.isoformat()},
            "templates": templates_out,
            "recent_texts": recent_texts,
            "concerning_patterns": concerns,
            # TODO(7_23): legacy "notes" key removed; observations is the Profile feed.
            "observations": observations,
        })


class SubjectEntriesExportView(APIView):
    """CSV export of all visible reflections + observations for one subject."""

    permission_classes = [IsAuthenticated]

    def get(self, request, person_id: int, *args, **kwargs):
        ctx, err = _get_subject_dashboard_context(request, person_id)
        if err is not None:
            return err
        assert ctx is not None

        refs = _reflections_for_subject(
            request.user, person_id, ctx.cur_start, ctx.cur_end,
        )
        tz = get_org_timezone(ctx.org)
        range_start = datetime.combine(ctx.cur_start, time.min, tzinfo=tz)
        range_end = datetime.combine(ctx.cur_end, time.min, tzinfo=tz) + timedelta(days=1)
        obs_base = (
            Observation.all_objects.filter(
                organization=ctx.org,
                subject_links__subject=ctx.subject,
                observed_at__gte=range_start,
                observed_at__lt=range_end,
            )
            .select_related("author")
        )
        observations = list(
            filter_observations_readable(
                obs_base, ctx.viewer_person, ctx.org, request.user,
            ).order_by("observed_at"),
        )

        csv_text = _build_subject_entries_csv(
            subject_name=ctx.subject.full_name,
            reflections=refs,
            observations=observations,
        )
        name_part = ctx.subject.full_name or ctx.subject.preferred_name or str(ctx.subject.id)
        slug = re.sub(r"[^\w\-]+", "_", name_part.strip()) or str(ctx.subject.id)
        filename = f"{slug}_entries_{ctx.cur_start}_{ctx.cur_end}.csv"
        response = HttpResponse(csv_text, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        audit.export(
            actor=request.user,
            content_query={
                "endpoint": "dashboards.subject_entries_export",
                "person_id": person_id,
                "date_start": ctx.cur_start.isoformat(),
                "date_end": ctx.cur_end.isoformat(),
            },
            organization=ctx.org,
        )
        return response

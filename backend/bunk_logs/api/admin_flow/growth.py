"""Admin growth dashboard grouped by grade level (Growth Dashboard by Grade Level).

Answers "what are 8th graders asking about versus 11th graders?" by
aggregating the LLM-produced :class:`ReflectionThemeTag` rows alongside the
self-rating means each grade reports.

Endpoints (mounted under ``/api/v1/admin/reflections/growth/``):

* ``GET  ``          -- per-grade theme mix, rating means, derived milestones
* ``GET  export/``   -- long-format CSV for board reporting
* ``GET  examples/`` -- excerpts behind one (grade, theme) cell

Key invariants
--------------
* Grade comes from the denormalized ``ReflectionThemeTag.grade_level``, which
  captures the author's grade at tag time. Resolving it lazily would
  retroactively relabel a prior year's cohort as the students are promoted.
* The main payload and the CSV carry counts and labels only, never free text.
  Excerpts live behind the separate ``examples/`` endpoint, which returns
  content the admin can already read via the member detail view.
* ``coverage`` reports tagged / pending / failed counts so a thin grade can
  be told apart from an untagged backlog.
* Milestones are derived: a least-squares slope across grades over the
  cohort's own numbers. Nothing here declares what a grade "should" score.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from io import StringIO
from typing import TYPE_CHECKING
from typing import Any

from django.db.models import Count
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionThemeTag
from bunk_logs.core.models import ReflectionThemeTagging
from bunk_logs.core.theme_tagging.taxonomy import TAGGED_DASHBOARD_ROLES
from bunk_logs.core.theme_tagging.taxonomy import TAXONOMY_VERSION
from bunk_logs.core.theme_tagging.taxonomy import complexity_tier
from bunk_logs.core.theme_tagging.taxonomy import is_valid_theme
from bunk_logs.core.theme_tagging.taxonomy import taxonomy_payload
from bunk_logs.core.theme_tagging.taxonomy import theme_label

from .common import resolve_current_program_for_role
from .common import viewer_or_403
from .reflections import _parse_grade_levels
from .reflections import _resolve_role_template
from .reflections import _role_memberships
from .reflections import _validate_role

if TYPE_CHECKING:
    from datetime import date

DEFAULT_ROLE = "madrich"

# Slope magnitude below this reads as "flat" rather than a real trend. On a
# 1-4 rating scale across five grades, anything smaller is noise.
FLAT_SLOPE_EPSILON = 0.05

CONCERN_COMPLEXITY_KEY = "__concern_complexity"

MAX_EXAMPLES = 20

EXCERPT_CHARS = 500


class AdminGrowthDashboardView(APIView):
    """``GET growth/`` -- per-grade theme mix, ratings, and derived milestones."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = _build_growth_payload(request, ctx)
        return Response(data)


class AdminGrowthDashboardExportView(APIView):
    """``GET growth/export/`` -- long-format CSV.

    One row per (grade, metric) so themes, rating means, and the complexity
    index all export uniformly and pivot cleanly in a spreadsheet. Carries no
    free text.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        payload = _build_growth_payload(request, ctx)

        header = [
            "grade_level",
            "member_count",
            "reflection_count",
            "metric_type",
            "metric_key",
            "metric_label",
            "value",
        ]
        rows: list[list[Any]] = []
        for grade in payload["grades"]:
            base = [
                grade["grade_level"] if grade["grade_level"] is not None else "",
                grade["member_count"],
                grade["reflection_count"],
            ]
            for theme in grade["themes"]:
                for role in TAGGED_DASHBOARD_ROLES:
                    rows.append([
                        *base,
                        f"theme_{role}",
                        theme["theme_key"],
                        theme["label"],
                        theme[f"{role}_count"],
                    ])
            for rating in grade["ratings"]:
                rows.append([
                    *base,
                    "rating_mean",
                    rating["category_key"],
                    rating["label"],
                    rating["mean"] if rating["mean"] is not None else "",
                ])
            rows.append([
                *base,
                "index",
                CONCERN_COMPLEXITY_KEY,
                "Concern complexity index",
                grade["concern_complexity_index"]
                if grade["concern_complexity_index"] is not None
                else "",
            ])

        period = payload["header"]["period"]
        audit.export(
            actor=request.user,
            content_query={
                "endpoint": "admin_flow.reflections_growth_export",
                "role": payload["header"]["role"],
                "start": period["start"],
                "end": period["end"],
                "taxonomy_version": TAXONOMY_VERSION,
            },
            organization=ctx.organization,
        )

        return _csv_response(
            rows,
            header=header,
            filename=f"{payload['header']['role']}-growth-by-grade-{period['start']}.csv",
        )


class AdminGrowthExamplesView(APIView):
    """``GET growth/examples/`` -- excerpts behind one (grade, theme) cell.

    Requires ``theme``; ``grade_level`` narrows to a single cohort. Returns
    reflection content, so it runs the same visibility filter the member
    detail view uses rather than reading rows directly.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        role = _resolve_role(request)

        theme_key = (request.query_params.get("theme") or "").strip()
        if not theme_key:
            msg = "A 'theme' parameter is required."
            raise ValidationError(msg)
        if not is_valid_theme(theme_key):
            msg = f"Unknown theme: {theme_key!r}."
            raise ValidationError(msg)

        grade_levels = _parse_grade_levels(request.query_params.get("grade_level"))
        program = resolve_current_program_for_role(ctx.organization, role, ctx.today)
        start, end = _resolve_window(request, program, ctx.today)

        tags = ReflectionThemeTag.all_objects.filter(
            organization=ctx.organization,
            theme_key=theme_key,
            period_start__gte=start,
            period_start__lte=end,
        )
        if program is not None:
            tags = tags.filter(program=program)
        if grade_levels:
            tags = tags.filter(grade_level__in=grade_levels)

        dashboard_role = (request.query_params.get("dashboard_role") or "").strip()
        if dashboard_role:
            tags = tags.filter(dashboard_role=dashboard_role)

        tags = list(
            tags.select_related("reflection", "reflection__template").order_by(
                "-period_start",
            )[: MAX_EXAMPLES * 2],
        )

        visible_ids = set(
            reflections_visible_for_user(
                request.user,
                Reflection.all_objects.filter(
                    pk__in=[t.reflection_id for t in tags],
                ),
            ).values_list("pk", flat=True),
        )

        items: list[dict] = []
        for tag in tags:
            if tag.reflection_id not in visible_ids:
                continue
            excerpt = _answer_excerpt(tag.reflection, tag.field_key)
            if not excerpt:
                continue
            items.append({
                "reflection_id": tag.reflection_id,
                "grade_level": tag.grade_level,
                "field_key": tag.field_key,
                "dashboard_role": tag.dashboard_role,
                "period_start": tag.period_start.isoformat(),
                "excerpt": excerpt,
            })
            if len(items) >= MAX_EXAMPLES:
                break

        return Response({
            "theme": {
                "key": theme_key,
                "label": theme_label(theme_key),
                "complexity_tier": complexity_tier(theme_key),
            },
            "grade_levels": grade_levels,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "count": len(items),
            "items": items,
        })


# ---------------------------------------------------------------------------
# Payload assembly
# ---------------------------------------------------------------------------


def _build_growth_payload(request, ctx) -> dict:
    role = _resolve_role(request)
    grade_filter = _parse_grade_levels(request.query_params.get("grade_level"))

    program = resolve_current_program_for_role(ctx.organization, role, ctx.today)
    start, end = _resolve_window(request, program, ctx.today)
    template = _resolve_role_template(ctx.organization, program, role, ctx.today)

    memberships = (
        list(_role_memberships(program, role, grade_filter).select_related("person"))
        if program
        else []
    )
    grade_by_person = {
        m.person_id: m.grade_level for m in memberships if m.person_id
    }
    member_counts: dict[int | None, int] = defaultdict(int)
    for m in memberships:
        member_counts[m.grade_level] += 1

    reflections = _window_reflections(
        request.user, ctx.organization, program, template, start, end,
    )
    reflections_by_grade: dict[int | None, list[Reflection]] = defaultdict(list)
    for reflection in reflections:
        grade = grade_by_person.get(reflection.subject_id)
        if grade_filter and grade not in grade_filter:
            continue
        reflections_by_grade[grade].append(reflection)

    theme_counts = _theme_counts(
        ctx.organization, program, start, end, grade_filter,
    )
    rating_field = _rating_field(template)

    grades = sorted(
        {
            *member_counts.keys(),
            *theme_counts.keys(),
            *reflections_by_grade.keys(),
        },
        key=lambda g: (g is None, g),
    )

    grade_payloads = [
        _grade_payload(
            grade=grade,
            member_count=member_counts.get(grade, 0),
            reflections=reflections_by_grade.get(grade, []),
            theme_counts=theme_counts.get(grade, {}),
            rating_field=rating_field,
        )
        for grade in grades
    ]

    return {
        "header": {
            "role": role,
            "role_label": dict(Membership.ROLES).get(
                role, role.replace("_", " ").title(),
            ),
            "program": {"id": program.id, "name": program.name} if program else None,
            "template": {"id": template.id, "slug": template.slug} if template else None,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "taxonomy_version": TAXONOMY_VERSION,
            "coverage": _coverage(ctx.organization, program, start, end, reflections),
        },
        "taxonomy": taxonomy_payload(),
        "grades": grade_payloads,
        "milestones": _milestones(grade_payloads, rating_field),
    }


def _grade_payload(
    *,
    grade: int | None,
    member_count: int,
    reflections: list[Reflection],
    theme_counts: dict[str, dict[str, int]],
    rating_field: dict | None,
) -> dict:
    concern_total = sum(
        counts.get("open_concern", 0) for counts in theme_counts.values()
    )
    themes = []
    for theme_key, counts in theme_counts.items():
        open_concern = counts.get("open_concern", 0)
        themes.append({
            "theme_key": theme_key,
            "label": theme_label(theme_key),
            "complexity_tier": complexity_tier(theme_key),
            "open_concern_count": open_concern,
            "wins_count": counts.get("wins", 0),
            "improvements_count": counts.get("improvements", 0),
            "total_count": sum(counts.get(role, 0) for role in TAGGED_DASHBOARD_ROLES),
            "share_of_concerns": (
                round(open_concern / concern_total, 4) if concern_total else None
            ),
        })
    themes.sort(key=lambda t: (-t["open_concern_count"], -t["total_count"], t["label"]))

    return {
        "grade_level": grade,
        "member_count": member_count,
        "reflection_count": len(reflections),
        "themes": themes,
        "ratings": _rating_means(rating_field, reflections),
        "concern_complexity_index": _complexity_index(theme_counts),
    }


def _theme_counts(
    organization, program, start: date, end: date, grade_filter: list[int] | None,
) -> dict[int | None, dict[str, dict[str, int]]]:
    """Group tag rows into ``{grade: {theme_key: {dashboard_role: count}}}``.

    One grouped query -- the whole reason grade level is denormalized onto
    the tag rows.
    """
    qs = ReflectionThemeTag.all_objects.filter(
        organization=organization,
        period_start__gte=start,
        period_start__lte=end,
        tagging__taxonomy_version=TAXONOMY_VERSION,
    )
    if program is not None:
        qs = qs.filter(program=program)
    if grade_filter:
        qs = qs.filter(grade_level__in=grade_filter)

    out: dict[int | None, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int)),
    )
    rows = qs.values("grade_level", "theme_key", "dashboard_role").annotate(
        n=Count("id"),
    )
    for row in rows:
        out[row["grade_level"]][row["theme_key"]][row["dashboard_role"]] = row["n"]
    return {
        grade: {theme: dict(roles) for theme, roles in themes.items()}
        for grade, themes in out.items()
    }


def _window_reflections(
    user, organization, program, template, start: date, end: date,
) -> list[Reflection]:
    if program is None or template is None:
        return []
    qs = Reflection.all_objects.filter(
        organization=organization,
        program=program,
        template=template,
        period_start__gte=start,
        period_start__lte=end,
        is_complete=True,
    ).select_related("template")
    return list(reflections_visible_for_user(user, qs))


def _rating_field(template) -> dict | None:
    """First ``rating_group`` field on the template, or None."""
    if template is None:
        return None
    for field in (template.schema or {}).get("fields") or []:
        if isinstance(field, dict) and field.get("type") == "rating_group":
            return field
    return None


def _rating_means(rating_field: dict | None, reflections: list[Reflection]) -> list[dict]:
    """Per-category means for one grade bucket.

    Matches ``dashboards/template._agg_rating_group``'s value handling:
    numeric answers only, booleans excluded.
    """
    if rating_field is None:
        return []
    key = rating_field["key"]
    categories = rating_field.get("categories") or []
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for reflection in reflections:
        block = (reflection.answers or {}).get(key)
        if not isinstance(block, dict):
            continue
        for category in categories:
            value = block.get(category["key"])
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                sums[category["key"]] += float(value)
                counts[category["key"]] += 1
    out = []
    for category in categories:
        ckey = category["key"]
        mean = sums[ckey] / counts[ckey] if counts[ckey] else None
        labels = category.get("labels") or {}
        out.append({
            "category_key": ckey,
            "label": labels.get("en") or ckey,
            "mean": round(mean, 3) if mean is not None else None,
            "n": counts[ckey],
        })
    return out


def _complexity_index(theme_counts: dict[str, dict[str, int]]) -> float | None:
    """Mean complexity tier of the concerns a grade raised.

    This is the number that should climb with grade if older teens are
    taking on more sophisticated challenges.
    """
    weighted = 0.0
    total = 0
    for theme_key, counts in theme_counts.items():
        n = counts.get("open_concern", 0)
        if n:
            weighted += complexity_tier(theme_key) * n
            total += n
    if not total:
        return None
    return round(weighted / total, 3)


def _coverage(
    organization, program, start: date, end: date, reflections: list[Reflection],
) -> dict:
    """Tagging progress for the window, so thin grades can be explained."""
    reflection_ids = [r.pk for r in reflections]
    by_status: dict[str, int] = defaultdict(int)
    if reflection_ids:
        rows = (
            ReflectionThemeTagging.all_objects.filter(
                organization=organization,
                reflection_id__in=reflection_ids,
                taxonomy_version=TAXONOMY_VERSION,
            )
            .values("status")
            .annotate(n=Count("id"))
        )
        for row in rows:
            by_status[row["status"]] = row["n"]

    tagged = by_status.get(ReflectionThemeTagging.Status.COMPLETED, 0)
    pending = by_status.get(ReflectionThemeTagging.Status.PENDING, 0)
    failed = by_status.get(
        ReflectionThemeTagging.Status.FAILED_TERMINAL, 0,
    ) + by_status.get(ReflectionThemeTagging.Status.FAILED_RETRYABLE, 0)
    total = len(reflection_ids)
    return {
        "reflections": total,
        "tagged": tagged,
        "pending": pending,
        "failed": failed,
        "untagged": max(0, total - tagged - pending - failed),
    }


def _milestones(grade_payloads: list[dict], rating_field: dict | None) -> list[dict]:
    """Per-metric progression across grades.

    For each rating category plus the concern-complexity index, report the
    value at each grade and the least-squares slope over grade number. The
    slope is the coaching signal: flat or negative on a category means the
    older cohort is not pulling ahead of the younger one.
    """
    graded = [g for g in grade_payloads if g["grade_level"] is not None]
    if not graded:
        return []

    metrics: list[tuple[str, str, dict[int, float | None]]] = []
    for category in (rating_field or {}).get("categories") or []:
        ckey = category["key"]
        labels = category.get("labels") or {}
        values = {}
        for grade in graded:
            match = next(
                (r for r in grade["ratings"] if r["category_key"] == ckey), None,
            )
            values[grade["grade_level"]] = match["mean"] if match else None
        metrics.append((ckey, labels.get("en") or ckey, values))

    metrics.append((
        CONCERN_COMPLEXITY_KEY,
        "Concern complexity index",
        {g["grade_level"]: g["concern_complexity_index"] for g in graded},
    ))

    out = []
    for key, label, values in metrics:
        points = [(g, v) for g, v in sorted(values.items()) if v is not None]
        slope = _least_squares_slope(points)
        out.append({
            "metric_key": key,
            "label": label,
            "by_grade": [
                {"grade_level": grade, "value": values.get(grade)}
                for grade in sorted(values)
            ],
            "slope": slope,
            "direction": _slope_direction(slope),
        })
    return out


def _least_squares_slope(points: list[tuple[int, float]]) -> float | None:
    """Slope of the best-fit line, or None when fewer than two points."""
    if len(points) < 2:
        return None
    n = len(points)
    mean_x = sum(x for x, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    if denominator == 0:
        return None
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in points)
    return round(numerator / denominator, 4)


def _slope_direction(slope: float | None) -> str:
    if slope is None:
        return "insufficient_data"
    if slope > FLAT_SLOPE_EPSILON:
        return "improving"
    if slope < -FLAT_SLOPE_EPSILON:
        return "declining"
    return "flat"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_role(request) -> str:
    role = (request.query_params.get("role") or DEFAULT_ROLE).strip()
    _validate_role(role)
    return role


def _resolve_window(request, program, today: date) -> tuple[date, date]:
    """Date window for the dashboard, defaulting to the program to date.

    Growth is a whole-program-year question, so the default window is the
    program start through today rather than a single week.
    """
    start = _parse_window_date(request.query_params.get("start"), "start")
    end = _parse_window_date(request.query_params.get("end"), "end")

    if start is None:
        start = program.start_date if program else today.replace(month=1, day=1)
    if end is None:
        end = min(program.end_date, today) if program else today

    if start > end:
        msg = "'start' must not be after 'end'."
        raise ValidationError(msg)
    return start, end


def _parse_window_date(raw: str | None, name: str) -> date | None:
    if not raw:
        return None
    parsed = parse_date(raw)
    if parsed is None:
        msg = f"Invalid '{name}' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


def _answer_excerpt(reflection: Reflection, field_key: str) -> str:
    value = (reflection.answers or {}).get(field_key)
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, list):
        text = "; ".join(
            part.strip() for part in value if isinstance(part, str) and part.strip()
        )
    else:
        return ""
    return text[:EXCERPT_CHARS]


def _csv_response(rows: list[list[Any]], *, header: list[str], filename: str) -> HttpResponse:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

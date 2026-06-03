"""Assigned-template response cards for the unified group dashboard.

For a given ``AssignmentGroup`` + date, surface every reflection
template *assigned to that group* (``TemplateAssignment`` with
``target_type='assignment_group'``) whose date window contains the
date. Each card carries the same shape the per-subject dashboard uses
(``schema_fields`` + ``summary`` + ``rating_series`` + ``reflections``)
so the frontend can reuse one ``FormResponsesCard`` component.

Reflections are visibility-filtered through
``reflections_visible_for_user`` exactly like the subject dashboard, so
this never widens what a viewer can see beyond the group-access gate.
"""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING
from typing import Any

from django.db.models import Q

from bunk_logs.api.dashboards.subject import _is_yes_no_field
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.reflection_scores import resolve_rating_cells

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import AssignmentGroup
    from bunk_logs.core.models import Organization

# Cap per-template reflection rows so a long-history group can't trigger
# an unbounded query; a single day rarely exceeds the group's roster.
MAX_REFLECTIONS_PER_TEMPLATE = 200


def _assigned_templates(
    organization: Organization, group: AssignmentGroup, target_date: date,
):
    """TemplateAssignments targeting ``group`` whose window covers ``target_date``.

    Cancelled assignments are excluded; scheduled/active/ended are kept
    so a historical date inside an ended assignment's window still shows.
    """
    return (
        TemplateAssignment.all_objects.filter(
            organization=organization,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            assignment_group=group,
            start_date__lte=target_date,
        )
        .exclude(status=TemplateAssignment.Status.CANCELLED)
        .filter(Q(end_date__gte=target_date) | Q(end_date__isnull=True))
        .select_related("template")
        .order_by("start_date", "id")
    )


def build_group_template_cards(
    *,
    request,
    group: AssignmentGroup,
    target_date: date,
    organization: Organization,
) -> list[dict[str, Any]]:
    """One response card per template assigned to ``group`` on ``target_date``.

    Templates are de-duplicated (the first assignment that references a
    template owns the card's ``assignment`` metadata); reflections are
    those authored in this group context for the template on the date,
    visibility-filtered for the requesting user.
    """
    cards: list[dict[str, Any]] = []
    seen_template_ids: set[int] = set()

    for assignment in _assigned_templates(organization, group, target_date):
        tpl = assignment.template
        if tpl is None or tpl.id in seen_template_ids:
            continue
        if getattr(tpl, "subject_mode", None) == "self":
            continue
        seen_template_ids.add(tpl.id)

        schema_fields = (tpl.schema or {}).get("fields") or []
        flag_keys = [
            f.get("key")
            for f in schema_fields
            if isinstance(f, dict) and _is_yes_no_field(f)
        ]

        refs = list(
            reflections_visible_for_user(
                request.user,
                Reflection.objects.filter(
                    template=tpl,
                    assignment_group=group,
                    period_start__lte=target_date,
                    period_end__gte=target_date,
                    is_complete=True,
                ).select_related("template", "author", "subject", "assignment_group"),
            ).order_by("period_end", "id")[:MAX_REFLECTIONS_PER_TEMPLATE],
        )

        summary: dict[str, Any] = {
            "total_reflections": 0,
            "flag_counts": {
                k: {"yes": 0, "no": 0, "total": 0} for k in flag_keys
            },
        }
        rating_series: dict[str, list[dict[str, Any]]] = defaultdict(list)
        reflections_out: list[dict[str, Any]] = []

        for r in refs:
            summary["total_reflections"] += 1
            answers = r.answers or {}
            for fkey, counts in summary["flag_counts"].items():
                raw = answers.get(fkey)
                val = str(raw).lower() if raw is not None else ""
                if val == "yes":
                    counts["yes"] += 1
                    counts["total"] += 1
                elif val == "no":
                    counts["no"] += 1
                    counts["total"] += 1

            for field in schema_fields:
                if not isinstance(field, dict):
                    continue
                if field.get("type") not in ("single_rating", "rating_group"):
                    continue
                scale = field.get("scale") or [1, 5]
                try:
                    scale_max = int(scale[-1])
                except (IndexError, ValueError, TypeError):
                    scale_max = 5
                for label, value in resolve_rating_cells(field, answers).items():
                    rating_series[label].append({
                        "date": r.period_end.isoformat(),
                        "value": value,
                        "reflection_id": r.id,
                        "scale_max": scale_max,
                        "team_visibility": r.team_visibility,
                    })

            reflections_out.append({
                "id": r.id,
                "date": r.period_end.isoformat(),
                "author_name": r.author.full_name if r.author else None,
                "team_visibility": r.team_visibility,
                "language": r.language,
                "answers": answers,
                "subject": (
                    {"id": r.subject_id, "name": r.subject.full_name}
                    if r.subject_id and r.subject else None
                ),
                "assignment_group": (
                    {"id": r.assignment_group_id, "name": r.assignment_group.name}
                    if r.assignment_group_id else None
                ),
            })

        series = [
            {
                "label": label,
                "scale_max": (points[0]["scale_max"] if points else 5),
                "points": points,
            }
            for label, points in rating_series.items()
        ]

        cards.append({
            "assignment": {
                "id": assignment.id,
                "title": assignment.title or tpl.name,
                "is_required": assignment.is_required,
                "start_date": assignment.start_date.isoformat(),
                "end_date": (
                    assignment.end_date.isoformat() if assignment.end_date else None
                ),
            },
            "template": {
                "id": tpl.id,
                "name": tpl.name,
                "slug": tpl.slug,
                "subject_mode": tpl.subject_mode,
            },
            "schema_fields": schema_fields,
            "summary": summary,
            "rating_series": series,
            "reflections": reflections_out,
        })

    return cards

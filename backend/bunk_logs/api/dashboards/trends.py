"""Subject Trend Grid view (the signature 'color patterns' visualization).

GET /api/v1/dashboards/subject-trends/?assignment_group=&template=&date_start=&date_end=&category=

Returns a per-subject, per-day rating value derived from the template's
``primary_rating`` field, OR averaged across the ``category_ratings`` field's
categories, OR a single category when ``?category=<key>`` is provided.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.filters import reflections_visible_for_user

DEFAULT_WINDOW_DAYS = 14
MAX_WINDOW_DAYS = 60


def _parse_date(s: str | None, default: date) -> date:
    if not s:
        return default
    try:
        return date.fromisoformat(s)
    except ValueError:
        return default


def _date_range(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


def _scale_max(field: dict) -> int:
    scale = field.get("scale") or [1, 5]
    try:
        return int(scale[-1])
    except (IndexError, ValueError, TypeError):
        return 5


def _find_field(template: ReflectionTemplate, role: str) -> dict | None:
    for f in (template.schema or {}).get("fields") or []:
        if isinstance(f, dict) and f.get("dashboard_role") == role:
            return f
    return None


def _rating_from_answer(
    answers: dict,
    primary: dict | None,
    category: dict | None,
    category_key: str | None,
) -> float | None:
    """Resolve a single numeric rating for a reflection's answers."""
    if primary is not None:
        v = answers.get(primary.get("key"))
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    if category is not None:
        block = answers.get(category.get("key"))
        if not isinstance(block, dict):
            return None
        if category_key:
            v = block.get(category_key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
            return None
        # Average across all configured categories
        vals: list[float] = []
        for cat in category.get("categories") or []:
            ck = cat.get("key") if isinstance(cat, dict) else None
            if ck is None:
                continue
            v = block.get(ck)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                vals.append(float(v))
        if vals:
            return sum(vals) / len(vals)
    return None


class SubjectTrendGridView(APIView):
    """Per-subject, per-day rating heat grid for one assignment group + template."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)

        group_id_raw = (request.query_params.get("assignment_group") or "").strip()
        template_id_raw = (request.query_params.get("template") or "").strip()
        if not group_id_raw.isdigit() or not template_id_raw.isdigit():
            return Response(
                {"detail": "assignment_group and template query parameters are required."},
                status=400,
            )
        group = AssignmentGroup.objects.filter(id=int(group_id_raw), is_active=True).first()
        if group is None:
            return Response({"detail": "Assignment group not found."}, status=404)
        template = ReflectionTemplate.objects.filter(id=int(template_id_raw)).first()
        if template is None:
            return Response({"detail": "Template not found."}, status=404)

        # Permission: viewer must be able to see at least one reflection in this group
        # OR the group must be visible to them via author-or-descendant set.
        from bunk_logs.core.permissions.visibility import author_group_ids_with_descendants
        from bunk_logs.core.permissions.visibility import is_org_admin
        viewer = Person.objects.filter(user=request.user).first()
        if not is_org_admin(request.user):
            if viewer is None:
                return Response({"detail": "Person profile required."}, status=403)
            visible_gids = author_group_ids_with_descendants(viewer)
            if group.id not in visible_gids:
                return Response({"detail": "Access denied for this group."}, status=403)

        # Resolve scale + field roles
        primary = _find_field(template, "primary_rating")
        category_field = _find_field(template, "category_ratings")
        if primary is None and category_field is None:
            return Response(
                {"detail": "Template has no primary_rating or category_ratings field."},
                status=400,
            )
        scale_max = _scale_max(primary) if primary is not None else _scale_max(category_field)
        category_keys = [
            c.get("key")
            for c in (category_field.get("categories") if category_field else []) or []
            if isinstance(c, dict) and c.get("key")
        ]
        category_filter = (request.query_params.get("category") or "").strip() or None
        if category_filter and category_filter not in category_keys:
            return Response(
                {"detail": f"Unknown category key: {category_filter}"},
                status=400,
            )

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

        # Subjects
        subjects = list(
            AssignmentGroupMembership.objects.filter(
                group=group, role_in_group="subject", is_active=True,
            ).select_related("person").order_by("person__last_name", "person__first_name"),
        )
        subject_rows = [
            {
                "person_id": agm.person_id,
                "name": agm.person.full_name,
                "last_name": agm.person.last_name,
            }
            for agm in subjects
        ]
        subject_ids = [s["person_id"] for s in subject_rows]

        # Reflections in window for this group + template + visible to viewer
        refs = list(
            reflections_visible_for_user(
                request.user,
                Reflection.objects.filter(
                    template=template,
                    assignment_group=group,
                    subject_id__in=subject_ids,
                    period_end__gte=cur_start,
                    period_end__lte=cur_end,
                    is_complete=True,
                ).select_related("author"),
            ).order_by("period_end"),
        )

        # Aggregate per (subject, day): if multiple, take most recent submission
        per_cell: dict[tuple[int, date], dict[str, Any]] = {}
        for r in refs:
            rating = _rating_from_answer(
                r.answers, primary, category_field, category_filter,
            )
            existing = per_cell.get((r.subject_id, r.period_end))
            if existing is None or r.submitted_at > existing["submitted_at"]:
                per_cell[(r.subject_id, r.period_end)] = {
                    "rating": rating,
                    "reflection_id": r.id,
                    "author_id": r.author_id,
                    "author_name": r.author.full_name if r.author else None,
                    "team_visibility": r.team_visibility,
                    "submitted_at": r.submitted_at,
                }

        days = _date_range(cur_start, cur_end)

        # Build response
        out_subjects = []
        for s in subject_rows:
            cells = []
            for d in days:
                c = per_cell.get((s["person_id"], d))
                cells.append({
                    "date": d.isoformat(),
                    "rating": (
                        round(c["rating"], 2) if c is not None and c["rating"] is not None else None
                    ),
                    "reflection_id": c["reflection_id"] if c is not None else None,
                    "author_id": c["author_id"] if c is not None else None,
                    "author_name": c["author_name"] if c is not None else None,
                    "team_visibility": c["team_visibility"] if c is not None else None,
                })
            out_subjects.append({
                "person_id": s["person_id"],
                "name": s["name"],
                "cells": cells,
            })

        return Response({
            "group": {
                "id": group.id,
                "name": group.name,
                "group_type": group.group_type,
            },
            "template": {
                "id": template.id,
                "name": template.name,
                "slug": template.slug,
                "primary_rating_key": primary.get("key") if primary else None,
                "category_ratings_key": category_field.get("key") if category_field else None,
                "category_keys": category_keys,
            },
            "period": {"start": cur_start.isoformat(), "end": cur_end.isoformat()},
            "scale_min": 1,
            "scale_max": scale_max,
            "category_filter": category_filter,
            "subjects": out_subjects,
        })

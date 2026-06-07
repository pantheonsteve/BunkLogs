"""Coverage dashboard view.

GET /api/v1/dashboards/coverage/ -> per-AssignmentGroup, per-day completion
percentages used to render the supervisor heat map.

Visibility is delegated to ``reflections_visible_to`` and to a parallel
"author-or-descendant" set so only groups the viewer supervises (or all groups
for org admins / unrestricted leadership) appear.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from datetime import timedelta

from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.permissions import is_super_admin
from bunk_logs.api.dashboards.group_dashboard_common import groups_visible_to_viewer
from bunk_logs.core.permissions.visibility import is_org_admin
from bunk_logs.core.time_utils import get_today

DEFAULT_WINDOW_DAYS = 14
MAX_WINDOW_DAYS = 60


def _parse_date(s: str | None, default: date) -> date:
    if not s:
        return default
    try:
        return date.fromisoformat(s)
    except ValueError:
        return default


def _coverage_status(percent: int | None, has_roster: bool) -> str:
    """Tier mapping for the coverage heatmap, per prompt spec."""
    if not has_roster:
        return "inactive"
    if percent is None or percent == 0:
        return "gray"
    if percent >= 100:
        return "green"
    if percent >= 90:
        return "light_green"
    if percent >= 70:
        return "yellow"
    if percent >= 40:
        return "orange"
    return "red"


def _date_range(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


class CoverageDashboardView(APIView):
    """Per-group / per-day completion heatmap."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)

        viewer = Person.objects.filter(user=request.user).first()
        if viewer is None and not is_super_admin(request.user):
            return Response({"detail": "Person profile required."}, status=403)

        # Time window
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

        # Determine visible groups
        groups_qs = AssignmentGroup.objects.filter(is_active=True)
        if request.query_params.get("group_type"):
            groups_qs = groups_qs.filter(group_type=request.query_params["group_type"])

        # Program (session) picker options before per-program visibility scoping.
        program_options = [
            {"id": pid, "name": name}
            for pid, name in groups_qs.values_list("program_id", "program__name")
            .distinct()
            .order_by("program__name")
        ]

        # Filter to a single program (session) when requested.
        program_filter = (request.query_params.get("program") or "").strip()
        if program_filter.isdigit():
            groups_qs = groups_qs.filter(program_id=int(program_filter))

        if not is_org_admin(request.user):
            if viewer is None:
                return Response({
                    "period": {"start": cur_start.isoformat(), "end": cur_end.isoformat()},
                    "org_summary": {"covered": 0, "total": 0, "percent": 0},
                    "programs": program_options,
                    "groups": [],
                })
            org_today = get_today(org)
            program_ids = (
                [int(program_filter)]
                if program_filter.isdigit()
                else [p["id"] for p in program_options]
            )
            visible_group_ids: set[int] = set()
            for pid in program_ids:
                program_obj = Program.objects.filter(
                    id=pid, organization=org,
                ).first()
                if program_obj is not None:
                    visible_group_ids |= groups_visible_to_viewer(
                        person=viewer,
                        organization=org,
                        program=program_obj,
                        today=org_today,
                    )
            if not visible_group_ids:
                return Response({
                    "period": {"start": cur_start.isoformat(), "end": cur_end.isoformat()},
                    "org_summary": {"covered": 0, "total": 0, "percent": 0},
                    "programs": program_options,
                    "groups": [],
                })
            groups_qs = groups_qs.filter(id__in=visible_group_ids)

        groups = list(
            groups_qs.values(
                "id", "name", "group_type", "program_id", "program__name",
            ).order_by("group_type", "name"),
        )
        if not groups:
            return Response({
                "period": {"start": cur_start.isoformat(), "end": cur_end.isoformat()},
                "org_summary": {"covered": 0, "total": 0, "percent": 0},
                "programs": program_options,
                "groups": [],
            })
        group_ids = [g["id"] for g in groups]

        # Filter templates to shared-roster ones; default = any
        templates_qs = ReflectionTemplate.objects.filter(
            is_active=True,
            subject_mode__in=["single_subject", "multi_subject", "group"],
        )
        template_filter = (request.query_params.get("template") or "").strip()
        if template_filter.isdigit():
            templates_qs = templates_qs.filter(id=int(template_filter))
        templates = list(templates_qs)
        template_ids = [t.id for t in templates]

        # Total subjects per group (fixed across the window — group changes are rare)
        roster_counts = dict(
            AssignmentGroupMembership.objects.filter(
                group_id__in=group_ids,
                role_in_group="subject",
                is_active=True,
            )
            .values_list("group_id")
            .annotate(c=Count("id"))
            .values_list("group_id", "c"),
        )
        # Group total = max of subjects; templates with subject_mode='group' contribute 1
        per_group_total = {}
        for g in groups:
            gid = g["id"]
            subj = roster_counts.get(gid, 0)
            # If any template is per_group, keep at least 1
            if subj == 0:
                # could still be a 'group' mode template target; treat as 1 if any group-mode template
                if any(t.subject_mode == "group" for t in templates):
                    per_group_total[gid] = 1
                else:
                    per_group_total[gid] = 0
            else:
                per_group_total[gid] = subj

        # Coverage rows: one query for per-subject reflections, one for group-mode reflections
        period_q = {"period_end__gte": cur_start, "period_end__lte": cur_end}
        per_subject_rows = list(
            reflections_visible_for_user(
                request.user,
                Reflection.objects.filter(
                    assignment_group_id__in=group_ids,
                    template_id__in=template_ids,
                    is_complete=True,
                    **period_q,
                ),
            )
            .values("assignment_group_id", "period_end")
            .annotate(c=Count("subject_id", distinct=True))
            .values_list("assignment_group_id", "period_end", "c"),
        )
        group_mode_rows = list(
            reflections_visible_for_user(
                request.user,
                Reflection.objects.filter(
                    subject_group_id__in=group_ids,
                    template_id__in=template_ids,
                    is_complete=True,
                    **period_q,
                ),
            )
            .values("subject_group_id", "period_end")
            .annotate(c=Count("id"))
            .values_list("subject_group_id", "period_end", "c"),
        )

        coverage: dict[tuple[int, date], int] = defaultdict(int)
        for gid, pe, c in per_subject_rows:
            coverage[(gid, pe)] = max(coverage[(gid, pe)], c)
        for gid, pe, c in group_mode_rows:
            coverage[(gid, pe)] = max(coverage[(gid, pe)], 1 if c else 0)

        days = _date_range(cur_start, cur_end)
        total_covered = 0
        total_total = 0
        result_groups = []
        for g in groups:
            gid = g["id"]
            total = per_group_total.get(gid, 0)
            day_rows = []
            for d in days:
                covered = coverage.get((gid, d), 0)
                if total > 0:
                    percent = round(covered / total * 100)
                else:
                    percent = None
                day_rows.append({
                    "date": d.isoformat(),
                    "covered": covered,
                    "total": total,
                    "percent": percent if percent is not None else 0,
                    "status": _coverage_status(percent, total > 0),
                })
                total_covered += covered
                total_total += total
            result_groups.append({
                "id": gid,
                "name": g["name"],
                "group_type": g["group_type"],
                "program_id": g["program_id"],
                "program_name": g["program__name"],
                "days": day_rows,
            })

        org_percent = round(total_covered / total_total * 100, 1) if total_total else 0
        return Response({
            "period": {"start": cur_start.isoformat(), "end": cur_end.isoformat()},
            "org_summary": {
                "covered": total_covered,
                "total": total_total,
                "percent": org_percent,
            },
            "programs": program_options,
            "groups": result_groups,
        })

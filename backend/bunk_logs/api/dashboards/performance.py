"""Group performance dashboard view.

GET /api/v1/dashboards/groups/performance/ -> per-group completion +
score distribution for a single day. Used by the Performance Dashboard
at ``/groups/performance``.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.camper_care.common import bunk_camper_ids
from bunk_logs.api.counselor.common import camper_reflection_template
from bunk_logs.api.counselor.common import off_camp_camper_ids
from bunk_logs.api.counselor.common import person_display_name
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.permissions import is_super_admin
from bunk_logs.core.permissions.visibility import author_group_ids_with_descendants
from bunk_logs.core.permissions.visibility import is_org_admin
from bunk_logs.core.reflection_scores import iter_scored_fields
from bunk_logs.core.reflection_scores import resolve_rating_cells
from bunk_logs.core.time_utils import get_today


def _parse_date(s: str | None, default: date) -> date:
    if not s:
        return default
    try:
        return date.fromisoformat(s)
    except ValueError:
        return default


def _program_options_from_qs(groups_qs) -> list[dict]:
    opts: list[dict] = []
    seen: set[int] = set()
    for pid, name, start, end, is_active in (
        groups_qs.values_list(
            "program_id",
            "program__name",
            "program__start_date",
            "program__end_date",
            "program__is_active",
        )
        .distinct()
        .order_by("-program__start_date")
    ):
        if pid in seen:
            continue
        seen.add(pid)
        opts.append({
            "id": pid,
            "name": name,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "is_active": is_active,
        })
    return opts


def _current_program(program_options: list[dict], today: date) -> dict | None:
    active = []
    for prog in program_options:
        if not prog.get("is_active"):
            continue
        start = date.fromisoformat(prog["start_date"])
        end = date.fromisoformat(prog["end_date"])
        if start <= today <= end:
            active.append(prog)
    if not active:
        return None
    return max(active, key=lambda p: p["start_date"])


def _performance_response(
    *,
    target_date: date,
    today: date,
    program_options: list[dict],
    selected_program: dict | None,
    groups: list[dict],
) -> dict:
    return {
        "date": target_date.isoformat(),
        "today": today.isoformat(),
        "current_program": _current_program(program_options, today),
        "program": selected_program,
        "programs": program_options,
        "groups": groups,
    }


def _author_names_by_group(group_ids: list[int]) -> dict[int, list[str]]:
    rows = (
        AssignmentGroupMembership.objects.filter(
            group_id__in=group_ids,
            role_in_group="author",
            is_active=True,
        )
        .select_related("person")
        .order_by("group_id", "person__last_name", "person__first_name")
    )
    out: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        if row.person:
            out[row.group_id].append(person_display_name(row.person))
    return dict(out)


def _score_distribution(reflections, template) -> dict:
    """Aggregate rating counts across all scored columns for pie chart."""
    if template is None:
        return {"scale_max": 5, "distribution": {}, "total_ratings": 0}

    sm = 5
    for field, _label, field_sm in iter_scored_fields(template):
        sm = max(sm, field_sm)

    dist: dict[str, int] = {str(i): 0 for i in range(1, sm + 1)}
    total = 0
    for ref in reflections:
        answers = ref.answers or {}
        for field, _label, _field_sm in iter_scored_fields(template):
            cells = resolve_rating_cells(field, answers)
            for val in cells.values():
                if val is None:
                    continue
                key = str(round(val))
                if key in dist:
                    dist[key] += 1
                    total += 1
    return {"scale_max": sm, "distribution": dist, "total_ratings": total}


class GroupPerformanceDashboardView(APIView):
    """Per-group daily completion + score breakdown for supervised groups."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)

        viewer = Person.objects.filter(user=request.user).first()
        if viewer is None and not is_super_admin(request.user):
            return Response({"detail": "Person profile required."}, status=403)

        today = get_today(org)
        target_date = _parse_date(request.query_params.get("date"), today)

        groups_qs = AssignmentGroup.objects.filter(
            organization=org,
            is_active=True,
        ).select_related("parent", "program")

        group_type = (request.query_params.get("group_type") or "").strip()
        if group_type:
            groups_qs = groups_qs.filter(group_type=group_type)

        if not is_org_admin(request.user):
            visible_ids = (
                author_group_ids_with_descendants(viewer) if viewer else set()
            )
            if not visible_ids:
                return Response(_performance_response(
                    target_date=target_date,
                    today=today,
                    program_options=[],
                    selected_program=None,
                    groups=[],
                ))
            groups_qs = groups_qs.filter(id__in=visible_ids)

        program_options = _program_options_from_qs(groups_qs)

        program_filter = (request.query_params.get("program") or "").strip()
        selected_program = None
        if program_filter.isdigit():
            pid = int(program_filter)
            groups_qs = groups_qs.filter(program_id=pid)
            for opt in program_options:
                if opt["id"] == pid:
                    selected_program = opt
                    break
        else:
            current = _current_program(program_options, today)
            if current is None:
                return Response(_performance_response(
                    target_date=target_date,
                    today=today,
                    program_options=program_options,
                    selected_program=None,
                    groups=[],
                ))
            groups_qs = groups_qs.filter(program_id=current["id"])
            selected_program = current

        groups = list(groups_qs.order_by("group_type", "name"))
        if not groups:
            return Response(_performance_response(
                target_date=target_date,
                today=today,
                program_options=program_options,
                selected_program=selected_program,
                groups=[],
            ))

        group_ids = [g.id for g in groups]
        authors = _author_names_by_group(group_ids)

        result_groups = []
        for group in groups:
            program = group.program
            camper_template = camper_reflection_template(
                org, program, bunk=group, as_of=target_date,
            )
            camper_ids = bunk_camper_ids(group) if group.group_type == "bunk" else []
            off_camp = off_camp_camper_ids(org, target_date, camper_ids) if camper_ids else set()

            submitted = 0
            reflections: list[Reflection] = []
            if camper_template and camper_ids:
                reflections = list(
                    Reflection.all_objects.filter(
                        template=camper_template,
                        assignment_group=group,
                        period_start=target_date,
                        period_end=target_date,
                        is_complete=True,
                    ),
                )
                submitted_ids = {r.subject_id for r in reflections}
                on_camp = [c for c in camper_ids if c not in off_camp]
                submitted = len([c for c in on_camp if c in submitted_ids])
                expected = len(on_camp)
            else:
                expected = 0

            percent = round(submitted / expected * 100) if expected else 0
            scores = _score_distribution(reflections, camper_template)

            result_groups.append({
                "id": group.id,
                "name": group.name,
                "group_type": group.group_type,
                "parent_name": group.parent.name if group.parent_id else None,
                "author_names": authors.get(group.id, []),
                "completion": {
                    "submitted": submitted,
                    "expected": expected,
                    "percent": percent,
                    "is_complete": expected > 0 and submitted >= expected,
                },
                "scores": scores,
            })

        return Response(_performance_response(
            target_date=target_date,
            today=today,
            program_options=program_options,
            selected_program=selected_program,
            groups=result_groups,
        ))

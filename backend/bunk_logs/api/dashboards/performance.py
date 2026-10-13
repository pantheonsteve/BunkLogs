"""Group performance dashboard view.

GET /api/v1/dashboards/groups/performance/ -> per-group completion +
score distribution for the selected date. Bunks count the daily camper
log. Other group types count recurring templates assigned to the group,
over the period that contains the date (a day, a week, and so on).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.camper_care.common import bunk_camper_ids
from bunk_logs.api.counselor.common import camper_reflection_template
from bunk_logs.api.counselor.common import off_camp_camper_ids
from bunk_logs.api.counselor.common import person_display_name
from bunk_logs.api.dashboards.group_dashboard_common import groups_visible_to_viewer
from bunk_logs.api.dashboards.group_roster import build_group_roster
from bunk_logs.core.assignment_resolution import assignment_cadence
from bunk_logs.core.assignment_resolution import resolve_members
from bunk_logs.core.group_audience import group_audience
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.permissions import is_super_admin
from bunk_logs.core.permissions.visibility import is_org_admin
from bunk_logs.core.reflection_scores import iter_scored_fields
from bunk_logs.core.reflection_scores import resolve_rating_cells
from bunk_logs.core.time_utils import get_current_period
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
    for pid, name, alias, start, end, is_active in (
        groups_qs.values_list(
            "program_id",
            "program__name",
            "program__display_alias",
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
            "name": alias or name,
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
    group_types: list[str] | None = None,
) -> dict:
    return {
        "date": target_date.isoformat(),
        "today": today.isoformat(),
        "current_program": _current_program(program_options, today),
        "program": selected_program,
        "programs": program_options,
        "group_types": group_types or [],
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


def _merge_scores(parts: list[tuple[list, object]]) -> dict:
    """Sum rating counts across the templates that contributed submissions."""
    if not parts:
        return _score_distribution([], None)
    merged: dict | None = None
    for refs, template in parts:
        block = _score_distribution(refs, template)
        if merged is None:
            merged = {
                "scale_max": block["scale_max"],
                "distribution": dict(block["distribution"]),
                "total_ratings": block["total_ratings"],
            }
            continue
        merged["scale_max"] = max(merged["scale_max"], block["scale_max"])
        for key, count in block["distribution"].items():
            merged["distribution"][key] = merged["distribution"].get(key, 0) + count
        merged["total_ratings"] += block["total_ratings"]
    scale_max = merged["scale_max"]
    merged["distribution"] = {
        str(i): merged["distribution"].get(str(i), 0) for i in range(1, scale_max + 1)
    }
    return merged


def _date_effective_group_assignments(group_ids: list[int], target_date: date):
    """Group-targeted assignments whose window contains ``target_date``.

    ``scheduled`` rows count: several orgs leave in-window assignments on
    that status. ``on_demand`` templates are incident forms, not a
    submission owed on the selected day, so they are omitted.
    """
    if not group_ids:
        return []
    rows = (
        TemplateAssignment.all_objects.filter(
            assignment_group_id__in=group_ids,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            start_date__lte=target_date,
        )
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=target_date))
        .exclude(status=TemplateAssignment.Status.CANCELLED)
        .select_related("template", "program")
    )
    kept = []
    for assignment in rows:
        template = assignment.template
        if template is None or not template.is_active:
            continue
        if assignment_cadence(assignment) == "on_demand":
            continue
        kept.append(assignment)
    return kept


def _subject_ids_for_template(group, template) -> set[int]:
    """People a group submission is about.

    Saved group_types uses ``group_audience``. Otherwise the subject
    seat, narrowed by ``subject_role_filter`` when that filter is set.
    """
    audience = group_audience(group.organization, group, template)
    if audience is not None:
        return set(audience.subjects)
    subject_ids = set(
        AssignmentGroupMembership.all_objects.filter(
            group=group, role_in_group="subject", is_active=True,
        ).values_list("person_id", flat=True),
    )
    role_filter = [role for role in (template.subject_role_filter or []) if role]
    if not subject_ids or not role_filter:
        return subject_ids
    return set(
        Membership.all_objects.filter(
            person_id__in=subject_ids,
            program_id=group.program_id,
            is_active=True,
            role__in=role_filter,
        ).values_list("person_id", flat=True),
    )


def _reflections_in_period(group, template, period_start: date, period_end: date, **extra):
    return list(
        Reflection.all_objects.filter(
            organization_id=group.organization_id,
            template=template,
            is_complete=True,
            period_start=period_start,
            period_end=period_end,
            **extra,
        ),
    )


def _completion_for_assignment(group, assignment, target_date: date):
    """Expected vs submitted for one group assignment in the date's period.

    Self templates: the people ``resolve_members`` says should file.
    With saved group_types those are the writers; otherwise authors and
    subjects whose membership role matches the template.
    A submission counts even when it was filed through a role assignment
    and has no group stamped on it.

    Subject templates: one expected row per subject, matching the bunk
    camper log. Group templates: one expected row for the group.
    """
    template = assignment.template
    cadence = assignment_cadence(assignment)
    period_start, period_end = get_current_period(
        cadence, group.organization, program=group.program, anchor=target_date,
    )
    if template.subject_mode == "self":
        person_ids = set(
            resolve_members(assignment, target_date).values_list("person_id", flat=True),
        )
        if not person_ids:
            return 0, 0, []
        refs = [
            ref for ref in _reflections_in_period(
                group, template, period_start, period_end,
                author_id__in=person_ids,
            )
            if ref.author_id == ref.subject_id and ref.author_id in person_ids
        ]
        submitted_ids = {ref.author_id for ref in refs}
        return len(person_ids), len(submitted_ids), refs
    if template.subject_mode == "group":
        refs = _reflections_in_period(
            group, template, period_start, period_end, assignment_group=group,
        )
        return 1, (1 if refs else 0), refs[:1]
    subject_ids = _subject_ids_for_template(group, template)
    if not subject_ids:
        return 0, 0, []
    refs = _reflections_in_period(
        group, template, period_start, period_end,
        assignment_group=group, subject_id__in=subject_ids,
    )
    submitted_ids = {ref.subject_id for ref in refs}
    return len(subject_ids), len(submitted_ids), refs


def _assigned_completion(group, assignments, target_date: date) -> tuple[int, int, dict]:
    """Sum completion across the group's recurring assigned templates."""
    seen: set[int] = set()
    expected = 0
    submitted = 0
    parts: list[tuple[list, object]] = []
    for assignment in assignments:
        template = assignment.template
        if template.id in seen:
            continue
        seen.add(template.id)
        exp, sub, refs = _completion_for_assignment(group, assignment, target_date)
        expected += exp
        submitted += sub
        if refs:
            parts.append((refs, template))
    return submitted, expected, _merge_scores(parts)


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

        org_groups_qs = AssignmentGroup.objects.filter(
            organization=org,
            is_active=True,
        ).select_related("parent", "program")

        program_filter = (request.query_params.get("program") or "").strip()

        # Program options ignore the group_type filter so an org without the
        # requested type (e.g. TBE has no bunks) still resolves its current program.
        program_options = _program_options_from_qs(org_groups_qs)

        selected_program = None
        target_program_id = None
        if program_filter.isdigit():
            target_program_id = int(program_filter)
            for opt in program_options:
                if opt["id"] == target_program_id:
                    selected_program = opt
                    break
        else:
            operational_options = [
                opt for opt in program_options
                if opt.get("is_active")
                and date.fromisoformat(opt["start_date"]) <= today <= date.fromisoformat(opt["end_date"])
            ]
            current = _current_program(operational_options, today)
            if current is None:
                return Response(_performance_response(
                    target_date=target_date,
                    today=today,
                    program_options=program_options,
                    selected_program=None,
                    groups=[],
                ))
            target_program_id = current["id"]
            selected_program = current

        program_groups_qs = org_groups_qs.filter(program_id=target_program_id)
        group_types = sorted(set(program_groups_qs.values_list("group_type", flat=True)))

        groups_qs = program_groups_qs
        group_type = (request.query_params.get("group_type") or "").strip()
        if group_type:
            groups_qs = groups_qs.filter(group_type=group_type)

        if not is_org_admin(request.user):
            if viewer is None:
                return Response(_performance_response(
                    target_date=target_date,
                    today=today,
                    program_options=program_options,
                    selected_program=selected_program,
                    groups=[],
                    group_types=group_types,
                ))
            program_obj = Program.objects.filter(id=target_program_id).first()
            if program_obj is None:
                visible_ids: set[int] = set()
            else:
                visible_ids = groups_visible_to_viewer(
                    person=viewer,
                    organization=org,
                    program=program_obj,
                    today=today,
                )
            if not visible_ids:
                return Response(_performance_response(
                    target_date=target_date,
                    today=today,
                    program_options=program_options,
                    selected_program=selected_program,
                    groups=[],
                ))
            group_types = sorted(set(
                program_groups_qs.filter(id__in=visible_ids).values_list("group_type", flat=True),
            ))
            groups_qs = groups_qs.filter(id__in=visible_ids)

        groups = list(groups_qs.order_by("group_type", "name"))
        if not groups:
            return Response(_performance_response(
                target_date=target_date,
                today=today,
                program_options=program_options,
                selected_program=selected_program,
                groups=[],
                group_types=group_types,
            ))

        group_ids = [g.id for g in groups]
        authors = _author_names_by_group(group_ids)
        # Bunks keep the camper-log path below so Crane Lake's numbers
        # stay put. Every other group type counts its assigned templates.
        other_ids = [g.id for g in groups if g.group_type != "bunk"]
        assignments_by_group: dict[int, list] = defaultdict(list)
        for assignment in _date_effective_group_assignments(other_ids, target_date):
            assignments_by_group[assignment.assignment_group_id].append(assignment)

        result_groups = []
        for group in groups:
            program = group.program
            if group.group_type == "bunk":
                camper_template = camper_reflection_template(
                    org, program, bunk=group, as_of=target_date,
                )
                camper_ids = bunk_camper_ids(group)
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

                scores = _score_distribution(reflections, camper_template)
            else:
                submitted, expected, scores = _assigned_completion(
                    group, assignments_by_group.get(group.id, []), target_date,
                )

            percent = round(submitted / expected * 100) if expected else 0

            result_groups.append({
                "id": group.id,
                "name": group.name,
                "group_type": group.group_type,
                "program_id": group.program_id,
                "program_name": program.display_name if program else None,
                "parent_name": group.parent.name if group.parent_id else None,
                "author_names": authors.get(group.id, []),
                "roster": build_group_roster(group=group, program=program),
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
            group_types=group_types,
        ))

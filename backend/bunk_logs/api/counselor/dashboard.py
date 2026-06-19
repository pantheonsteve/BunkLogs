"""``GET /api/v1/counselor/dashboard/`` — Story 2 + Story 9 (all set).

Returns the counselor home payload: viewer context, per-bunk tiles with
form-assignment progress, aggregated section summaries (camper reflections,
self-reflection, open requests), and all-set state.

State computation:

- ``camper_reflections``: count of campers (excluding off-camp) with a
  submitted reflection for the selected date's period.
- ``self_reflection``: viewer's own self-reflection for the selected period,
  with ``day_off`` treated as "complete" (Story 5 criterion 3).
- ``requests``: open Orders + MaintenanceTickets the viewer submitted on
  their bunks (aggregated count for quick-action badges).
- ``bunks``: one tile per bunk the viewer authors, each listing active
  form assignments with due/remaining copy, deep-link hints, and open
  requests filed for that bunk.

All-set (Story 9 criterion 1) is true iff both camper-reflections and
self-reflection sections are "complete". The Requests section is reactive,
not required, and does NOT affect all-set (Story 9 criterion 2).

Caching: a 30-second per-(org, viewer, selected-date) TTL covers the
cross-counselor freshness contract in Story 2 criterion 5.
"""

from __future__ import annotations

from datetime import date as date_type

from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.assignment_resolution import active_assignments_for
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.state_machine import OrderStateMachine
from bunk_logs.core.time_utils import get_current_period
from bunk_logs.core.time_utils import get_org_timezone
from bunk_logs.core.time_utils import get_rollover_hour

from .bunk_requests import bunk_requests_for_viewer
from .bunk_requests import viewer_open_requests
from .common import bunk_camper_persons
from .common import camper_reflection_template
from .common import counselor_self_template
from .common import dashboard_cache_key as _cache_key
from .common import is_day_off_answer
from .common import latest_camper_reflection_per_subject
from .common import latest_self_reflection
from .common import off_camp_camper_ids
from .common import person_display_name
from .common import viewer_or_403

DASHBOARD_CACHE_TTL_SECONDS = 30
OPEN_STATUSES: tuple[str, ...] = (OrderStateMachine.NEW, OrderStateMachine.IN_PROGRESS)


def _section_state(*, covered: int, total: int) -> str:
    if total == 0:
        return "complete"
    if covered == 0:
        return "none"
    if covered >= total:
        return "complete"
    return "in_progress"


def _parse_target_date(raw: str | None, default: date_type) -> date_type:
    if not raw:
        return default
    try:
        return date_type.fromisoformat(raw)
    except ValueError:
        return default


def _template_cadence(template: ReflectionTemplate, assignment: TemplateAssignment | None) -> str:
    if assignment is not None and assignment.cadence_override:
        return assignment.cadence_override
    return template.cadence or "daily"


def _format_due_label(
    *,
    cadence: str,
    remaining: int,
    period_end: date_type,
    target_date: date_type,
) -> str:
    cadence_key = (cadence or "daily").lower()
    if cadence_key in ("daily", "on_demand"):
        if remaining == 0:
            if target_date == period_end:
                return "All responses in for today"
            return "All responses in for this day"
        noun = "response" if remaining == 1 else "responses"
        return f"{remaining} {noun} needed today"
    end_label = period_end.strftime("%A, %b %d").replace(" 0", " ")
    if remaining == 0:
        return f"Complete for this period (through {end_label})"
    noun = "response" if remaining == 1 else "responses"
    return f"{remaining} {noun} due by {end_label}"


def _assignment_action_path(
    *,
    bunk_id: int,
    target_date: date_type,
    org_today: date_type,
    template: ReflectionTemplate,
    cadence: str,
) -> str:
    cadence_key = (cadence or "daily").lower()
    if template.subject_mode == "single_subject" and cadence_key in ("daily", "on_demand"):
        if target_date == org_today:
            return "/counselor/camper-reflections"
        return f"/counselor/camper-reflections/{target_date.isoformat()}"
    return f"/dashboards/group/{bunk_id}?date={target_date.isoformat()}"


class CounselorDashboardView(APIView):
    """Counselor home dashboard payload."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        org_today = ctx.today
        target_date = _parse_target_date(request.query_params.get("date"), org_today)

        skip_cache = request.query_params.get("nocache") in {"1", "true"}
        cache_key = _cache_key(viewer.id, org.id, target_date)
        if not skip_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        primary_membership = (
            Membership.objects.filter(person=viewer, is_active=True)
            .select_related("program")
            .order_by("-created_at")
            .first()
        )
        if primary_membership is None or primary_membership.program is None:
            payload = self._empty_payload(org_today, target_date, org, viewer)
            cache.set(cache_key, payload, DASHBOARD_CACHE_TTL_SECONDS)
            return Response(payload)
        program = primary_membership.program

        bunk_ids = list(
            AssignmentGroupMembership.objects.filter(
                person=viewer,
                role_in_group="author",
                is_active=True,
                group__is_active=True,
                group__group_type="bunk",
            ).values_list("group_id", flat=True),
        )
        bunks = list(
            AssignmentGroup.objects.filter(id__in=bunk_ids)
            .select_related("parent")
            .order_by("name"),
        )

        camper_section = self._camper_section(org, program, viewer, bunks, target_date)
        self_section = self._self_section(viewer, org, program, target_date)
        requests_section = self._requests_section(
            org, program, viewer, primary_membership, bunks,
        )
        bunk_tiles = self._bunks_section(
            org, program, viewer, primary_membership, bunks, target_date, org_today,
        )
        viewer_requests = viewer_open_requests(
            organization=org,
            viewer=viewer,
            bunks=bunks,
        )

        all_set = (
            camper_section["state"] == "complete"
            and self_section["state"] == "complete"
        )

        payload = {
            "viewer": {
                "id": viewer.id,
                "name": person_display_name(viewer),
                "full_name": viewer.full_name,
                "role": primary_membership.role,
            },
            "selected_date": target_date.isoformat(),
            "today": org_today.isoformat(),
            "is_today": target_date == org_today,
            "rollover_hour": get_rollover_hour(org),
            "timezone": str(get_org_timezone(org)),
            "program": {
                "id": program.id,
                "slug": program.slug,
                "name": program.name,
            },
            "all_set": all_set,
            "bunks": bunk_tiles,
            "viewer_requests": viewer_requests,
            "sections": {
                "camper_reflections": camper_section,
                "self_reflection": self_section,
                "requests": requests_section,
            },
        }
        cache.set(cache_key, payload, DASHBOARD_CACHE_TTL_SECONDS)
        return Response(payload)

    def _empty_payload(
        self,
        org_today: date_type,
        target_date: date_type,
        org,
        viewer: Person,
    ) -> dict:
        return {
            "viewer": {
                "id": viewer.id,
                "name": person_display_name(viewer),
                "full_name": viewer.full_name,
                "role": None,
            },
            "selected_date": target_date.isoformat(),
            "today": org_today.isoformat(),
            "is_today": target_date == org_today,
            "rollover_hour": get_rollover_hour(org),
            "timezone": str(get_org_timezone(org)),
            "program": None,
            "all_set": False,
            "bunks": [],
            "viewer_requests": [],
            "sections": {
                "camper_reflections": {
                    "state": "complete",
                    "covered": 0,
                    "total": 0,
                    "off_camp": 0,
                    "bunk_count": 0,
                },
                "self_reflection": {
                    "state": "complete",
                    "submitted": False,
                    "reflection_id": None,
                    "submitted_at": None,
                    "is_day_off": False,
                    "editable": False,
                    "template": None,
                    "cadence": None,
                    "period_start": None,
                    "period_end": None,
                },
                "requests": {
                    "state": "none",
                    "open_count": 0,
                    "by_type": {"camper_care": 0, "maintenance": 0},
                },
            },
        }

    def _assignment_tile(
        self,
        *,
        org,
        program: Program,
        viewer: Person,
        bunk,
        target_date: date_type,
        org_today: date_type,
        template: ReflectionTemplate,
        assignment: TemplateAssignment | None,
        expected_ids: set[int],
    ) -> dict:
        cadence = _template_cadence(template, assignment)
        period_start, period_end = get_current_period(
            cadence, org, program=program, anchor=target_date,
        )
        covered = 0
        total = len(expected_ids)
        if template.subject_mode == "single_subject" and total:
            reflections = latest_camper_reflection_per_subject(
                template, [bunk], period_start, period_end,
            )
            covered = sum(1 for sid in expected_ids if sid in reflections)
        remaining = max(total - covered, 0)
        title = (assignment.title if assignment and assignment.title else None) or template.name
        return {
            "assignment_id": assignment.id if assignment else None,
            "template_id": template.id,
            "template_name": title,
            "cadence": cadence,
            "subject_mode": template.subject_mode,
            "state": _section_state(covered=covered, total=total),
            "covered": covered,
            "total": total,
            "remaining": remaining,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "due_label": _format_due_label(
                cadence=cadence,
                remaining=remaining,
                period_end=period_end,
                target_date=target_date,
            ),
            "action_path": _assignment_action_path(
                bunk_id=bunk.id,
                target_date=target_date,
                org_today=org_today,
                template=template,
                cadence=cadence,
            ),
        }

    def _bunks_section(
        self,
        org,
        program: Program,
        viewer: Person,
        membership: Membership,
        bunks,
        target_date: date_type,
        org_today: date_type,
    ) -> list[dict]:
        if not bunks:
            return []

        roster_by_bunk = bunk_camper_persons(bunks)
        co_rows = (
            AssignmentGroupMembership.objects.filter(
                group__in=bunks,
                role_in_group="author",
                is_active=True,
            )
            .exclude(person=viewer)
            .select_related("person")
            .order_by("group_id", "person__last_name", "person__first_name")
        )
        co_names_by_bunk: dict[int, list[str]] = {b.id: [] for b in bunks}
        for row in co_rows:
            if row.person:
                co_names_by_bunk.setdefault(row.group_id, []).append(
                    person_display_name(row.person),
                )

        tiles: list[dict] = []
        for bunk in bunks:
            campers = roster_by_bunk.get(bunk.id, [])
            all_camper_ids = {p.id for p in campers}
            off_camp_ids = off_camp_camper_ids(org, target_date, camper_ids=all_camper_ids)
            expected_ids = all_camper_ids - off_camp_ids

            seen_template_ids: set[int] = set()
            assignments_out: list[dict] = []

            for assignment in active_assignments_for(
                viewer=viewer,
                organization=org,
                program=program,
                as_of=target_date,
                target_assignment_group=bunk,
            ):
                tpl = assignment.template
                if tpl is None or tpl.subject_mode == "self" or tpl.id in seen_template_ids:
                    continue
                seen_template_ids.add(tpl.id)
                assignments_out.append(
                    self._assignment_tile(
                        org=org,
                        program=program,
                        viewer=viewer,
                        bunk=bunk,
                        target_date=target_date,
                        org_today=org_today,
                        template=tpl,
                        assignment=assignment,
                        expected_ids=expected_ids,
                    ),
                )

            camper_tpl = camper_reflection_template(
                org, program, viewer=viewer, bunk=bunk, as_of=target_date,
            )
            if camper_tpl is not None and camper_tpl.id not in seen_template_ids:
                seen_template_ids.add(camper_tpl.id)
                assignments_out.append(
                    self._assignment_tile(
                        org=org,
                        program=program,
                        viewer=viewer,
                        bunk=bunk,
                        target_date=target_date,
                        org_today=org_today,
                        template=camper_tpl,
                        assignment=None,
                        expected_ids=expected_ids,
                    ),
                )

            tiles.append({
                "id": bunk.id,
                "name": bunk.name,
                "unit_name": bunk.parent.name if bunk.parent_id else None,
                "camper_count": len(campers),
                "off_camp_count": len(off_camp_ids),
                "co_counselor_names": co_names_by_bunk.get(bunk.id, []),
                "assignments": assignments_out,
                "dashboard_path": f"/dashboards/group/{bunk.id}?date={target_date.isoformat()}",
                "requests": bunk_requests_for_viewer(
                    organization=org,
                    program=program,
                    bunk=bunk,
                    viewer=viewer,
                    membership=membership,
                ),
            })
        return tiles

    def _camper_section(self, org, program, viewer: Person, bunks, target_date) -> dict:
        if not bunks:
            return {
                "state": "complete",
                "covered": 0,
                "total": 0,
                "off_camp": 0,
                "bunk_count": 0,
            }

        roster_by_bunk = bunk_camper_persons(bunks)
        all_camper_ids: set[int] = set()
        for campers in roster_by_bunk.values():
            all_camper_ids.update(p.id for p in campers)

        off_camp_ids = off_camp_camper_ids(org, target_date, camper_ids=all_camper_ids)
        expected_ids = all_camper_ids - off_camp_ids
        total = len(expected_ids)

        template = camper_reflection_template(
            org, program, viewer=viewer, as_of=target_date,
        )
        if template is None or total == 0:
            return {
                "state": "complete",
                "covered": 0,
                "total": total,
                "off_camp": len(off_camp_ids),
                "bunk_count": len(bunks),
            }

        cadence = template.cadence or "daily"
        period_start, period_end = get_current_period(
            cadence, org, program=program, anchor=target_date,
        )
        reflections = latest_camper_reflection_per_subject(
            template, bunks, period_start, period_end,
        )
        covered = sum(1 for sid in expected_ids if sid in reflections)

        return {
            "state": _section_state(covered=covered, total=total),
            "covered": covered,
            "total": total,
            "off_camp": len(off_camp_ids),
            "bunk_count": len(bunks),
        }

    def _self_section(self, viewer: Person, org, program: Program, target_date) -> dict:
        template = counselor_self_template(viewer, org, program, as_of=target_date)
        if template is None:
            return {
                "state": "complete",
                "submitted": False,
                "reflection_id": None,
                "submitted_at": None,
                "is_day_off": False,
                "editable": False,
                "template": None,
                "cadence": None,
                "period_start": None,
                "period_end": None,
            }

        cadence = template.cadence or "daily"
        period_start, period_end = get_current_period(
            cadence, org, program=program, anchor=target_date,
        )
        reflection = latest_self_reflection(viewer, template, period_start, period_end)
        submitted = reflection is not None
        return {
            "state": "complete" if submitted else "none",
            "submitted": submitted,
            "reflection_id": reflection.id if reflection else None,
            "submitted_at": (
                reflection.submitted_at.isoformat()
                if reflection and reflection.submitted_at else None
            ),
            "is_day_off": is_day_off_answer(reflection),
            "editable": submitted,
            "cadence": cadence,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "template": {
                "id": template.id,
                "slug": template.slug,
                "name": template.name,
                "version": template.version,
            },
        }

    def _requests_section(
        self, org, program, viewer: Person, membership: Membership, bunks,
    ) -> dict:
        del program, membership
        rows = viewer_open_requests(
            organization=org,
            viewer=viewer,
            bunks=bunks,
        )
        camper_care_count = sum(1 for r in rows if r["type"] == "camper_care")
        maintenance_count = sum(1 for r in rows if r["type"] == "maintenance")
        total = len(rows)
        return {
            "state": "in_progress" if total else "none",
            "open_count": total,
            "by_type": {
                "camper_care": camper_care_count,
                "maintenance": maintenance_count,
            },
        }

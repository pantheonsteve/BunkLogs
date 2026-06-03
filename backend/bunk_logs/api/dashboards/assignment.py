"""Assignment-centric Log Entries and Reflections dashboards.

Two endpoints, both scoped by ``assignments_visible_for_user``:

* ``GET /dashboards/assignment-templates/?scope=logs|reflections`` — the
  selector. ``scope=logs`` lists group-assigned templates only;
  ``scope=reflections`` lists self-reflection templates. Groups visible
  assignments by parent template. Filterable by lifecycle status and audience.
* ``GET /dashboards/assignment-template/<template_id>/?date=&group=<id>`` —
  the dashboard for one template on a date. Scope is inferred from the
  template's ``subject_mode`` when omitted.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from functools import reduce
from operator import or_
from typing import Any

from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.leadership_team.common import resolve_period
from bunk_logs.api.unit_head.common import score_grid_columns
from bunk_logs.core.assignment_resolution import resolve_members
from bunk_logs.core.assignment_visibility import assignments_visible_for_user
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.time_utils import get_today

from .template import aggregate_template_fields
from .template import serialize_template_block

_ROLE_LABELS = dict(Membership.ROLES)

SCOPE_LOGS = "logs"
SCOPE_REFLECTIONS = "reflections"
_VALID_SCOPES = frozenset({SCOPE_LOGS, SCOPE_REFLECTIONS})


def _parse_scope(request) -> str | None:
    raw = (request.query_params.get("scope") or "").strip().lower()
    if raw in _VALID_SCOPES:
        return raw
    return None


def _scope_for_template(template) -> str:
    if template and getattr(template, "subject_mode", None) == "self":
        return SCOPE_REFLECTIONS
    return SCOPE_LOGS


def _parse_dashboard_date(request, org) -> date:
    """Parse ``?date=`` for the dashboard; default to org-local today."""
    raw = (request.query_params.get("date") or "").strip()
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return get_today(org)


def _assignment_effective_on(assignment: TemplateAssignment, as_of: date) -> bool:
    """True when ``assignment`` would have applied on ``as_of``."""
    if assignment.status == TemplateAssignment.Status.CANCELLED:
        return False
    if assignment.start_date and assignment.start_date > as_of:
        return False
    return assignment.end_date is None or assignment.end_date >= as_of


def _status_matches(assignment: TemplateAssignment, as_of: date, wanted: str) -> bool:
    """Whether an assignment falls in the requested lifecycle bucket.

    * ``active``: in effect on ``as_of`` (its start/end window contains the day).
    * ``completed`` / ``ended``: lifecycle status is ``ended`` (date picker filters responses).
    * default (no filter): anything except ``cancelled``.

    ``active`` is date-relative so historical dates resolve the assignments
    that were running then. ``completed`` lists all ended assignments regardless
    of ``as_of`` — the selected date only scopes which reflections are shown.
    """
    if assignment.status == TemplateAssignment.Status.CANCELLED:
        return False
    if wanted == "active":
        return _assignment_effective_on(assignment, as_of)
    if wanted in ("completed", "ended"):
        return assignment.status == TemplateAssignment.Status.ENDED
    return True


def _audience(assignment: TemplateAssignment) -> tuple[str, str]:
    """Return ``(audience_type, audience_label)`` derived from the target."""
    target_type = assignment.target_type
    payload = assignment.target_payload or {}
    if target_type == TemplateAssignment.TargetType.ROLE:
        role = payload.get("role") or ""
        return "team", _ROLE_LABELS.get(role, role or "Team")
    if target_type == TemplateAssignment.TargetType.ASSIGNMENT_GROUP:
        group = assignment.assignment_group
        if group is not None:
            return group.group_type, group.name
        return "assignment_group", "Group"
    if target_type == TemplateAssignment.TargetType.INDIVIDUALS:
        count = len(payload.get("membership_ids") or [])
        return "individuals", f"{count} individual(s)"
    if target_type == TemplateAssignment.TargetType.TAG_GROUP:
        tag = payload.get("tag") or ""
        return "tag_group", f"#{tag}" if tag else "Tag group"
    return target_type, target_type


def _effective_cadence(assignment: TemplateAssignment) -> str:
    return assignment.cadence_override or assignment.template.cadence


def _person_name(person: Person) -> str:
    name = (getattr(person, "full_name", "") or "").strip()
    if name:
        return name
    return f"{person.first_name} {person.last_name}".strip()


def _is_yes_no_field(field: dict) -> bool:
    """Two-option ``single_choice`` field with yes/no values (case-insensitive)."""
    if not isinstance(field, dict) or field.get("type") != "single_choice":
        return False
    options = field.get("options") or []
    if len(options) != 2:
        return False
    values = {str(o.get("value", "")).lower() for o in options if isinstance(o, dict)}
    return values == {"yes", "no"}


def _grid_columns_payload(template) -> list[dict[str, Any]]:
    """Template-ordered columns for the responses table (matches ScoreGrid)."""
    return [
        {
            "label": col.label,
            "field_key": col.field_key,
            "field_type": col.field_type,
            "category_key": col.category_key,
            "scale_max": col.scale_max,
            "header": col.header,
        }
        for col in score_grid_columns(template)
    ]


def _build_responses_block(template, refs: list[Reflection]) -> dict[str, Any]:
    """Per-reflection rows in the shared ``FormResponsesCard`` block shape.

    Lets the dashboard render every response with all columns — including
    colour-coded score cells — using the same schema-aware table the subject
    and Leadership Team views use. ``rating_series`` is left empty because this
    surface is date-scoped (sparklines need a multi-day window).
    """
    schema_fields = (template.schema or {}).get("fields") or []
    flag_keys = [
        f.get("key") for f in schema_fields if _is_yes_no_field(f)
    ]
    flag_counts = {k: {"yes": 0, "no": 0, "total": 0} for k in flag_keys}
    rows: list[dict[str, Any]] = []
    for r in refs:
        answers = r.answers or {}
        for key, counts in flag_counts.items():
            val = str(answers.get(key)).lower() if answers.get(key) is not None else ""
            if val == "yes":
                counts["yes"] += 1
                counts["total"] += 1
            elif val == "no":
                counts["no"] += 1
                counts["total"] += 1
        subject = r.subject if r.subject_id else None
        rows.append(
            {
                "id": r.id,
                "date": r.period_end.isoformat(),
                "answers": answers,
                "author_name": r.author.full_name if r.author_id and r.author else None,
                "subject": (
                    {"id": subject.id, "name": _person_name(subject)} if subject else None
                ),
                "assignment_group": (
                    {"id": r.assignment_group_id, "name": r.assignment_group.name}
                    if r.assignment_group_id and r.assignment_group else None
                ),
                "team_visibility": r.team_visibility,
                "language": r.language,
                "created_at": r.submitted_at.isoformat() if r.submitted_at else None,
            },
        )
    rows.sort(
        key=lambda x: (
            (x["subject"]["name"].lower() if x["subject"] else "~"),
            x["date"],
        ),
    )
    return {
        "template": {
            "id": template.id,
            "name": template.name,
            "slug": template.slug,
            "subject_mode": template.subject_mode,
        },
        "schema_fields": schema_fields,
        "columns": _grid_columns_payload(template),
        "summary": {"total_reflections": len(refs), "flag_counts": flag_counts},
        "rating_series": [],
        "reflections": rows,
    }


def _audience_q(assignment: TemplateAssignment, member_person_ids: set[int]) -> Q | None:
    """Reflection filter scoping responses to one assignment's audience.

    Group assignments scope by the group context; role / individual / tag
    assignments scope by the responsible authors. Returns ``None`` when the
    assignment resolves to nobody (so it contributes no rows).
    """
    if (
        assignment.target_type == TemplateAssignment.TargetType.ASSIGNMENT_GROUP
        and assignment.assignment_group_id
    ):
        return Q(assignment_group_id=assignment.assignment_group_id)
    if member_person_ids:
        return Q(author_id__in=member_person_ids)
    return None


class AssignmentSelectorView(APIView):
    """List assignments grouped by parent template for the dashboard selector."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        viewer = Person.objects.filter(user=request.user).first()
        if org is None or viewer is None:
            return Response(
                {"detail": "Organization context and person profile required."},
                status=403,
            )

        wanted_status = (request.query_params.get("status") or "").strip().lower()
        wanted_audience = (request.query_params.get("audience") or "").strip().lower()
        scope = _parse_scope(request)
        as_of = _parse_dashboard_date(request, org)

        visible = assignments_visible_for_user(
            request.user, org, scope=scope,
        ).select_related(
            "template", "assignment_group", "program",
        )
        if scope == SCOPE_LOGS:
            visible = visible.filter(
                target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            ).exclude(template__subject_mode="self")
        elif scope == SCOPE_REFLECTIONS:
            visible = visible.filter(template__subject_mode="self")

        grouped: dict[int, dict[str, Any]] = {}
        for assignment in visible:
            if not _status_matches(assignment, as_of, wanted_status):
                continue
            audience_type, audience_label = _audience(assignment)
            if wanted_audience and audience_type != wanted_audience:
                continue
            entry = grouped.get(assignment.template_id)
            if entry is None:
                entry = {
                    "template_id": assignment.template_id,
                    "template_name": assignment.template.name if assignment.template_id else "",
                    "display_title": assignment.title
                    or (assignment.template.name if assignment.template_id else ""),
                    "cadence": _effective_cadence(assignment),
                    "audience_types": set(),
                    "groups": [],
                }
                grouped[assignment.template_id] = entry
            entry["audience_types"].add(audience_type)
            entry["groups"].append(
                {
                    "assignment_id": assignment.id,
                    "label": audience_label,
                    "audience_type": audience_type,
                    "status": assignment.status,
                    "program_id": assignment.program_id,
                    "program_label": assignment.program.name if assignment.program_id else "",
                },
            )

        templates = []
        for entry in grouped.values():
            entry["groups"].sort(key=lambda g: g["label"].lower())
            templates.append(
                {
                    "template_id": entry["template_id"],
                    "template_name": entry["template_name"],
                    "display_title": entry["display_title"],
                    "cadence": entry["cadence"],
                    "audience_types": sorted(entry["audience_types"]),
                    "group_count": len(entry["groups"]),
                    "groups": entry["groups"],
                },
            )
        templates.sort(key=lambda t: t["display_title"].lower())
        return Response({"templates": templates})


class AssignmentTemplateDashboardView(APIView):
    """Dashboard for one template on a date, aggregated across its groups.

    ``?group=<assignment_id>`` narrows to a single group; omitted = all visible
    groups for that template. ``?date=`` defaults to today; ``?status=`` selects
    which assignment lifecycle bucket the groups come from (default active).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, template_id: int, *args, **kwargs):
        org = getattr(request, "organization", None)
        viewer = Person.objects.filter(user=request.user).first()
        if org is None or viewer is None:
            return Response(
                {"detail": "Organization context and person profile required."},
                status=403,
            )

        visible_all = list(
            assignments_visible_for_user(
                request.user,
                org,
                scope=_parse_scope(request) or _scope_for_template(
                    ReflectionTemplate.objects.filter(
                        id=template_id, organization=org,
                    ).first(),
                ),
            )
            .filter(template_id=template_id)
            .select_related("template", "program", "assignment_group"),
        )
        if not visible_all:
            return Response(
                {"detail": "Access denied for this template."},
                status=403,
            )

        template = visible_all[0].template
        as_of = _parse_dashboard_date(request, org)
        wanted_status = (request.query_params.get("status") or "active").strip().lower()
        in_status = [a for a in visible_all if _status_matches(a, as_of, wanted_status)]

        programs = sorted(
            (
                {"program_id": pid, "program_label": label}
                for pid, label in {
                    (a.program_id, a.program.name if a.program_id else "")
                    for a in in_status
                }
            ),
            key=lambda p: p["program_label"].lower(),
        )

        # Program scope (selected before the group drill-down).
        selected_program_id = self._parse_int(request.query_params.get("program"))
        if selected_program_id is not None:
            in_scope = [a for a in in_status if a.program_id == selected_program_id]
        else:
            in_scope = in_status

        groups = sorted(
            (self._group_dict(a) for a in in_scope),
            key=lambda g: g["label"].lower(),
        )

        selected_assignment_id = self._parse_int(request.query_params.get("group"))
        if selected_assignment_id is not None:
            to_use = [a for a in in_scope if a.id == selected_assignment_id]
            if not to_use:
                return Response(
                    {"detail": "Access denied for this group."},
                    status=403,
                )
        else:
            to_use = in_scope

        as_of = self._parse_date(request, org)
        payload = self._build_payload(
            request.user, org, to_use, template, as_of,
            program=(to_use[0].program if to_use else visible_all[0].program),
            programs=programs,
            groups=groups,
            selected_program_id=selected_program_id,
            selected_assignment_id=selected_assignment_id,
        )
        return Response(payload)

    @staticmethod
    def _group_dict(assignment: TemplateAssignment) -> dict[str, Any]:
        audience_type, audience_label = _audience(assignment)
        return {
            "assignment_id": assignment.id,
            "label": audience_label,
            "audience_type": audience_type,
            "program_id": assignment.program_id,
            "program_label": assignment.program.name if assignment.program_id else "",
        }

    @staticmethod
    def _parse_int(raw: str | None) -> int | None:
        raw = (raw or "").strip()
        if not raw or raw.lower() == "all":
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def _build_payload(
        self,
        user,
        org,
        assignments: list[TemplateAssignment],
        template,
        as_of: date,
        *,
        program,
        programs: list[dict[str, Any]],
        groups: list[dict[str, Any]],
        selected_program_id: int | None,
        selected_assignment_id: int | None,
    ) -> dict[str, Any]:
        # A single selected group honors its cadence_override; an aggregate
        # view falls back to the template cadence (overrides are rare and not
        # meaningfully combinable across groups).
        if len(assignments) == 1:
            effective_cadence = _effective_cadence(assignments[0])
        else:
            effective_cadence = template.cadence
        template.cadence = effective_cadence  # in-memory; instance not saved
        period_start, period_end = resolve_period(
            template, anchor=as_of, program=program,
        )
        window = period_end - period_start
        prior_end = period_start - timedelta(days=1)
        prior_start = prior_end - window

        members_by_person: dict[int, dict[str, str]] = {}
        audience_qs: list[Q] = []
        for assignment in assignments:
            members = resolve_members(assignment, as_of).select_related("person")
            member_ids: set[int] = set()
            for m in members:
                member_ids.add(m.person_id)
                members_by_person.setdefault(
                    m.person_id, {"name": _person_name(m.person), "role": m.role},
                )
            q = _audience_q(assignment, member_ids)
            if q is not None:
                audience_qs.append(q)

        cur_refs = self._reflections(
            user, template, org.id, period_start, period_end, audience_qs,
        )
        prev_refs = self._reflections(
            user, template, org.id, prior_start, prior_end, audience_qs,
        )

        submitted_author_ids = {r.author_id for r in cur_refs}
        roster = [
            {
                "person_id": pid,
                "name": info["name"],
                "role": info["role"],
                "status": "submitted" if pid in submitted_author_ids else "outstanding",
            }
            for pid, info in members_by_person.items()
        ]
        roster.sort(key=lambda r: r["name"].lower())

        expected = len(members_by_person)
        submitted = sum(1 for r in roster if r["status"] == "submitted")
        selected_label = next(
            (g["label"] for g in groups if g["assignment_id"] == selected_assignment_id),
            None,
        )
        selected_program_label = next(
            (p["program_label"] for p in programs if p["program_id"] == selected_program_id),
            None,
        )

        return {
            "template": serialize_template_block(template),
            "selection": {
                "template_id": template.id,
                "display_title": (assignments[0].title if assignments else "") or template.name,
                "cadence": effective_cadence,
                "program_count": len(programs),
                "group_count": len(groups),
                "selected_program": selected_program_id,
                "selected_program_label": selected_program_label,
                "selected_assignment": selected_assignment_id,
                "selected_label": selected_label,
            },
            "programs": programs,
            "groups": groups,
            "period": {
                "current_start": period_start.isoformat(),
                "current_end": period_end.isoformat(),
                "prior_start": prior_start.isoformat(),
                "prior_end": prior_end.isoformat(),
            },
            "summary": {
                "person_count": len({r.subject_id for r in cur_refs}),
                "response_count": len(cur_refs),
                "expected_count": expected,
                "submitted_count": submitted,
                "completion_rate": round(submitted / expected, 4) if expected else 0.0,
            },
            "fields": aggregate_template_fields(template, cur_refs, prev_refs),
            "responses": _build_responses_block(template, cur_refs),
            "roster": roster,
        }

    @staticmethod
    def _parse_date(request, org) -> date:
        return _parse_dashboard_date(request, org)

    @staticmethod
    def _reflections(
        user,
        template,
        org_id: int,
        start: date,
        end: date,
        audience_qs: list[Q],
    ) -> list[Reflection]:
        if not audience_qs:
            return []
        base = Reflection.objects.filter(
            template=template,
            organization_id=org_id,
            is_complete=True,
            period_start__lte=end,
            period_end__gte=start,
        ).filter(reduce(or_, audience_qs)).select_related(
            "subject", "author", "assignment_group", "subject_group",
        )
        return list(reflections_visible_for_user(user, base))

"""Admin-scoped reflections completion dashboard (Step 4_4 — TBE).

Mirrors the shape of ``api/leadership_team/team_dashboard.py`` (period
resolution, per-member submission status) but gates on the standard
``admin_flow`` org-admin membership instead of a ``Supervision`` row --
TBE admins have no Supervision relationship over the ``madrich`` role,
and ``content_visibility`` already grants org admins full reflection
visibility regardless of Supervision.

Endpoints (mounted under ``/api/v1/admin/reflections/``):

* ``GET teams/<role>/``                          -- weekly completion roster
* ``GET teams/<role>/export/``                   -- CSV for board reporting
* ``GET teams/<role>/members/<membership_id>/``  -- one member's reflection history

``role`` is a path parameter rather than hard-coded to ``madrich`` so the
same views can serve future grade/role-based orgs without changes.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import TYPE_CHECKING
from typing import Any

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import person_display_name
from bunk_logs.api.leadership_team.common import resolve_period
from bunk_logs.core import audit
from bunk_logs.core.assignment_resolution import resolve_template_for
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection

from .common import resolve_current_program_for_role
from .common import viewer_or_403

if TYPE_CHECKING:
    from datetime import date


class AdminReflectionsTeamView(APIView):
    """``GET teams/<role>/`` -- weekly completion roster for one role."""

    permission_classes = [IsAuthenticated]

    def get(self, request, role: str, *args, **kwargs):
        ctx = viewer_or_403(request)
        _validate_role(role)

        target_date = _parse_date_param(
            request.query_params.get("date"), default=ctx.today,
        )
        if target_date > ctx.today:
            msg = "Future dates are not selectable."
            raise ValidationError(msg)
        grade_levels = _parse_grade_levels(request.query_params.get("grade_level"))

        program = resolve_current_program_for_role(ctx.organization, role, target_date)
        memberships = (
            list(_role_memberships(program, role, grade_levels).select_related("person", "program"))
            if program
            else []
        )
        template = _resolve_role_template(ctx.organization, program, role, target_date)

        if template is None:
            members_payload = _member_rows(memberships, latest_by_subject={})
            return Response({
                "header": _header_payload(
                    role, program, member_count=len(memberships),
                    period=None, target_date=target_date,
                ),
                "template": None,
                "submission_status": None,
                "members": members_payload,
            })

        period_start, period_end = resolve_period(
            template, anchor=target_date, program=program,
        )
        latest_by_subject = _latest_reflections_by_subject(
            request.user, ctx.organization, template, memberships,
            period_start=period_start, period_end=period_end,
        )
        members_payload = _member_rows(memberships, latest_by_subject)

        return Response({
            "header": _header_payload(
                role, program, member_count=len(memberships),
                period=(period_start, period_end, template.cadence),
                target_date=target_date,
            ),
            "template": {"id": template.id, "slug": template.slug},
            "submission_status": _summarize_status(members_payload),
            "members": members_payload,
        })


class AdminReflectionsTeamExportView(APIView):
    """``GET teams/<role>/export/`` -- board-reporting CSV.

    Deliberately excludes free-text answer content -- a board export
    should show completion status, not reflection contents.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, role: str, *args, **kwargs):
        ctx = viewer_or_403(request)
        _validate_role(role)

        target_date = _parse_date_param(
            request.query_params.get("date"), default=ctx.today,
        )
        grade_levels = _parse_grade_levels(request.query_params.get("grade_level"))

        program = resolve_current_program_for_role(ctx.organization, role, target_date)
        memberships = (
            list(_role_memberships(program, role, grade_levels).select_related("person", "program"))
            if program
            else []
        )
        template = _resolve_role_template(ctx.organization, program, role, target_date)

        period_start = period_end = None
        latest_by_subject: dict[int, Reflection] = {}
        if template is not None:
            period_start, period_end = resolve_period(
                template, anchor=target_date, program=program,
            )
            latest_by_subject = _latest_reflections_by_subject(
                request.user, ctx.organization, template, memberships,
                period_start=period_start, period_end=period_end,
            )

        members_payload = _member_rows(memberships, latest_by_subject)
        header = [
            "person_name", "grade_level", "status", "submitted_at",
            "period_start", "period_end",
        ]
        rows = [
            [
                row["person_name"],
                row["grade_level"] if row["grade_level"] is not None else "",
                row["status"],
                row["submitted_at"] or "",
                period_start.isoformat() if period_start else "",
                period_end.isoformat() if period_end else "",
            ]
            for row in members_payload
        ]

        audit.export(
            actor=request.user,
            content_query={
                "endpoint": "admin_flow.reflections_team_export",
                "role": role,
                "date": target_date.isoformat(),
                "grade_level": grade_levels,
            },
            organization=ctx.organization,
        )

        filename_period = period_start.isoformat() if period_start else target_date.isoformat()
        return _csv_response(
            rows, header=header,
            filename=f"{role}-weekly-completion-{filename_period}.csv",
        )


class AdminReflectionsMemberDetailView(APIView):
    """``GET teams/<role>/members/<membership_id>/`` -- one member's history."""

    permission_classes = [IsAuthenticated]

    def get(self, request, role: str, membership_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        _validate_role(role)

        try:
            membership = (
                Membership.objects.filter(
                    program__organization=ctx.organization, role=role,
                )
                .select_related("person", "program")
                .get(pk=membership_id)
            )
        except Membership.DoesNotExist as exc:
            raise NotFound from exc

        person = membership.person
        template = _resolve_role_template(
            ctx.organization, membership.program, role, ctx.today,
        )

        history: list[dict[str, Any]] = []
        if template is not None and person is not None:
            reflections = reflections_visible_for_user(
                request.user,
                Reflection.all_objects.filter(
                    organization=ctx.organization,
                    template__slug=template.slug,
                    subject_id=person.id,
                ).select_related("template"),
            ).order_by("-period_end")
            history = [
                {
                    "reflection_id": r.id,
                    "period_start": r.period_start.isoformat(),
                    "period_end": r.period_end.isoformat(),
                    "status": _row_status(r),
                    "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                    "answers": r.answers,
                }
                for r in reflections
            ]

        return Response({
            "membership_id": membership.id,
            "person_id": person.id if person else None,
            "person_name": person_display_name(person) if person else "",
            "grade_level": membership.grade_level,
            "role": role,
            "role_label": dict(Membership.ROLES).get(role, role.replace("_", " ").title()),
            "history": history,
        })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_role(role: str) -> None:
    if role not in dict(Membership.ROLES):
        msg = f"Unknown role: {role!r}."
        raise NotFound(msg)


def _parse_date_param(raw: str | None, *, default: date) -> date:
    if not raw:
        return default
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid 'date' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


def _parse_grade_levels(raw: str | None) -> list[int] | None:
    """Parse a comma-separated ``grade_level`` filter, e.g. ``"8,9,10"``."""
    if not raw:
        return None
    out: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out or None


def _role_memberships(program, role: str, grade_levels: list[int] | None):
    qs = Membership.objects.filter(
        program=program,
        role=role,
        is_active=True,
    )
    if grade_levels:
        qs = qs.filter(grade_level__in=grade_levels)
    return qs.order_by("person__last_name", "person__first_name")


def _resolve_role_template(organization, program, role: str, as_of: date):
    if program is None:
        return None
    # This is a recurring completion roster (see class docstrings) -- an
    # on-demand template co-assigned to the same role (e.g. a one-off
    # check-in) has no fixed period to track completion against and
    # would otherwise win an ambiguous tie-break, hiding the recurring
    # template's real submissions.
    return resolve_template_for(
        organization=organization,
        program=program,
        as_of=as_of,
        role=role,
        subject_mode="self",
        exclude_cadences=["on_demand"],
    )


def _latest_reflections_by_subject(
    user, organization, template, memberships, *, period_start, period_end,
) -> dict[int, Reflection]:
    person_ids = [m.person_id for m in memberships if m.person_id]
    reflections_qs = Reflection.all_objects.none()
    if person_ids:
        reflections_qs = Reflection.all_objects.filter(
            organization=organization,
            template=template,
            subject_id__in=person_ids,
            period_start=period_start,
            period_end=period_end,
            is_complete=True,
        ).select_related("author")
    visible = list(reflections_visible_for_user(user, reflections_qs))
    latest: dict[int, Reflection] = {}
    for r in visible:
        existing = latest.get(r.subject_id)
        if existing is None or r.submitted_at > existing.submitted_at:
            latest[r.subject_id] = r
    return latest


def _header_payload(role: str, program, *, member_count: int, period, target_date: date) -> dict:
    header: dict[str, Any] = {
        "role": role,
        "role_label": dict(Membership.ROLES).get(role, role.replace("_", " ").title()),
        "program": {"id": program.id, "name": program.name} if program else None,
        "member_count": member_count,
        "date": target_date.isoformat(),
    }
    if period:
        period_start, period_end, cadence = period
        header["period"] = {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
            "cadence": cadence,
        }
    else:
        header["period"] = None
    return header


def _row_status(reflection: Reflection | None) -> str:
    if reflection is None:
        return "not_submitted"
    answers = reflection.answers or {}
    if answers.get("day_off"):
        return "day_off"
    return "submitted"


def _member_rows(memberships, latest_by_subject: dict[int, Reflection]) -> list[dict]:
    rows: list[dict] = []
    for m in memberships:
        person = m.person
        r = latest_by_subject.get(m.person_id)
        rows.append({
            "membership_id": m.id,
            "person_id": person.id if person else None,
            "person_name": person_display_name(person) if person else "",
            "grade_level": m.grade_level,
            "status": _row_status(r),
            "reflection_id": r.id if r else None,
            "submitted_at": r.submitted_at.isoformat() if r and r.submitted_at else None,
        })
    rows.sort(key=lambda row: (row["status"] != "not_submitted", row["person_name"].casefold()))
    return rows


def _summarize_status(rows: list[dict]) -> dict:
    submitted = sum(1 for r in rows if r["status"] == "submitted")
    day_off = sum(1 for r in rows if r["status"] == "day_off")
    not_submitted = sum(1 for r in rows if r["status"] == "not_submitted")
    return {
        "submitted": submitted,
        "day_off": day_off,
        "not_submitted": not_submitted,
        "total": len(rows),
    }


def _csv_response(rows: list[list[Any]], *, header: list[str], filename: str) -> HttpResponse:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for r in rows:
        writer.writerow(r)
    resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

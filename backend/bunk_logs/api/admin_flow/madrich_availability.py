"""Org-admin staffing matrix for Sunday availability — Step 4_7 AC4.

Mirrors ``admin_flow/reflections.py``: gated on the standard ``admin_flow``
org-admin Membership (no Supervision relationship exists over the
``madrich`` role, same reasoning as Step 4_4). Query params ``program``
(slug), ``from``/``to`` (ISO dates) select the session window; default is
the active religious-school program's next 8 sessions.

Rows cover faculty and Madrichim, tagged by ``role``. The summary counts
stay Madrichim-only: it answers "is this Sunday staffed?", and faculty are
not interchangeable with the teens they supervise.
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

from bunk_logs.core import audit
from bunk_logs.core.models import MadrichAvailability
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Program
from bunk_logs.core.scheduling.availability_matrix import build_matrix_rows
from bunk_logs.core.scheduling.availability_matrix import resolve_session_window
from bunk_logs.core.scheduling.availability_matrix import summarize_counts

from .common import resolve_current_program_for_role
from .common import viewer_or_403

if TYPE_CHECKING:
    from datetime import date

MADRICH = "madrich"
FACULTY = "faculty"
ROLES = (FACULTY, MADRICH)


def _resolve_program(ctx, program_slug: str | None) -> Program | None:
    if program_slug:
        program = Program.all_objects.filter(
            organization=ctx.organization, slug=program_slug,
        ).first()
        if program is None:
            msg = f"Unknown program: {program_slug!r}."
            raise NotFound(msg)
        return program
    return resolve_current_program_for_role(
        ctx.organization, "madrich", ctx.today, program_type="religious_school",
    )


def _memberships(program: Program, role: str):
    return (
        Membership.objects.filter(program=program, role=role, is_active=True)
        .select_related("person")
        .order_by("person__last_name", "person__first_name")
    )


def _matrix_rows(program: Program, session_dates: list[date]) -> list[dict]:
    """Faculty block first, then Madrichim -- fewer faculty, and they staff the room."""
    rows: list[dict] = []
    for role in ROLES:
        rows.extend(
            build_matrix_rows(
                program, list(_memberships(program, role)), session_dates, role=role,
            ),
        )
    return rows


def _parse_date_param(raw: str | None, *, label: str) -> date | None:
    if not raw:
        return None
    parsed = parse_date(raw)
    if parsed is None:
        msg = f"Invalid '{label}' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


def _program_payload(program: Program | None) -> dict | None:
    if program is None:
        return None
    return {"id": program.id, "name": program.name, "slug": program.slug}


class AdminMadrichAvailabilityView(APIView):
    """``GET /api/v1/admin/madrich-availability/`` -- staffing matrix."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _resolve_program(ctx, request.query_params.get("program"))
        from_date = _parse_date_param(request.query_params.get("from"), label="from")
        to_date = _parse_date_param(request.query_params.get("to"), label="to")

        if program is None:
            return Response({
                "program": None, "sessions": [], "rows": [],
                "summary": {"available_counts": {}, "unset_counts": {}},
            })

        session_dates = resolve_session_window(
            program, from_date=from_date, to_date=to_date, today=ctx.today,
        )
        rows = _matrix_rows(program, session_dates)
        madrich_rows = [r for r in rows if r["role"] == MADRICH]

        return Response({
            "program": _program_payload(program),
            "sessions": [d.isoformat() for d in session_dates],
            "rows": rows,
            "summary": summarize_counts(madrich_rows, session_dates),
        })


class AdminMadrichAvailabilityExportView(APIView):
    """``GET /api/v1/admin/madrich-availability/export.csv``."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _resolve_program(ctx, request.query_params.get("program"))
        from_date = _parse_date_param(request.query_params.get("from"), label="from")
        to_date = _parse_date_param(request.query_params.get("to"), label="to")

        memberships: list[tuple[str, Membership]] = []
        session_dates: list[date] = []
        if program is not None:
            memberships = [
                (role, m) for role in ROLES for m in _memberships(program, role)
            ]
            session_dates = resolve_session_window(
                program, from_date=from_date, to_date=to_date, today=ctx.today,
            )

        rows = _export_rows(program, memberships, session_dates)

        audit.export(
            actor=request.user,
            content_query={
                "endpoint": "admin_flow.madrich_availability_export",
                "program": program.slug if program else None,
            },
            organization=ctx.organization,
        )

        filename_bit = program.slug if program else "no-program"
        return _csv_response(
            rows,
            header=[
                "session_date", "first_name", "last_name", "role",
                "grade_level", "status", "note", "updated_at",
            ],
            filename=f"madrich-availability-{filename_bit}.csv",
        )


def _export_rows(
    program: Program | None,
    memberships: list[tuple[str, Membership]],
    session_dates: list[date],
) -> list[list[Any]]:
    if program is None or not memberships or not session_dates:
        return []
    person_ids = [m.person_id for _, m in memberships if m.person_id]
    lookup: dict[tuple[int, date], MadrichAvailability] = {}
    if person_ids:
        qs = MadrichAvailability.objects.filter(
            program=program, person_id__in=person_ids, session_date__in=session_dates,
        )
        for row in qs:
            lookup[(row.person_id, row.session_date)] = row

    out: list[list[Any]] = []
    for role, m in memberships:
        person = m.person
        for d in session_dates:
            row = lookup.get((m.person_id, d))
            out.append([
                d.isoformat(),
                person.first_name if person else "",
                person.last_name if person else "",
                role,
                m.grade_level if m.grade_level is not None else "",
                row.status if row else "",
                row.note if row else "",
                row.updated_at.isoformat() if row else "",
            ])
    return out


def _csv_response(rows: list[list[Any]], *, header: list[str], filename: str) -> HttpResponse:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for r in rows:
        writer.writerow(r)
    resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

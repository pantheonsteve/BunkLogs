"""Org-admin Classroom Challenge Log oversight — Step 4_8, MA7.

Mirrors ``admin_flow/madrich_availability.py``: gated on the standard
``admin_flow`` org-admin Membership. No admin reply in Tier 1 -- a
Director follows up via a faculty account or in person.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from django.db.models import Count
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.classroom_challenges.common import challenge_list_item
from bunk_logs.core import audit
from bunk_logs.core.models import ClassroomChallenge

from .common import viewer_or_403


def _filtered_queryset(ctx, params):
    qs = ClassroomChallenge.objects.filter(organization=ctx.organization)

    program_slug = params.get("program")
    if program_slug:
        qs = qs.filter(program__slug=program_slug)

    classroom_param = params.get("classroom")
    if classroom_param:
        try:
            classroom_id = int(classroom_param)
        except (TypeError, ValueError) as exc:
            msg = "Invalid 'classroom' parameter."
            raise ValidationError(msg) from exc
        qs = qs.filter(assignment_group_id=classroom_id)

    status_param = params.get("status")
    if status_param:
        if status_param not in dict(ClassroomChallenge.STATUS_CHOICES):
            msg = "Invalid 'status' parameter."
            raise ValidationError(msg)
        qs = qs.filter(status=status_param)

    category_param = params.get("category")
    if category_param:
        if category_param not in dict(ClassroomChallenge.CATEGORY_CHOICES):
            msg = "Invalid 'category' parameter."
            raise ValidationError(msg)
        qs = qs.filter(category=category_param)

    session_date_param = params.get("session_date")
    if session_date_param:
        parsed = parse_date(session_date_param)
        if parsed is None:
            msg = "Invalid 'session_date' parameter; expected YYYY-MM-DD."
            raise ValidationError(msg)
        qs = qs.filter(session_date=parsed)

    return qs.select_related("author", "assignment_group", "program")


class AdminClassroomChallengesListView(APIView):
    """``GET /api/v1/admin/classroom-challenges/`` -- org-wide list with filters."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        qs = _filtered_queryset(ctx, request.query_params).annotate(
            response_count=Count("responses"),
        )
        results = [
            challenge_list_item(c, redacted=False, response_count=c.response_count, include_group=True)
            for c in qs
        ]
        return Response({"results": results})


class AdminClassroomChallengesExportView(APIView):
    """``GET /api/v1/admin/classroom-challenges/export.csv``."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        qs = _filtered_queryset(ctx, request.query_params).annotate(
            response_count=Count("responses"),
        )
        rows = _export_rows(qs)

        audit.export(
            actor=request.user,
            content_query={
                "endpoint": "admin_flow.classroom_challenges_export",
                "filters": dict(request.query_params),
            },
            organization=ctx.organization,
        )

        return _csv_response(
            rows,
            header=[
                "session_date", "classroom", "category", "status",
                "author_first_name", "author_last_name", "body", "response_count", "created_at",
            ],
            filename="classroom-challenges.csv",
        )


def _export_rows(qs) -> list[list[Any]]:
    out: list[list[Any]] = []
    for c in qs:
        author = c.author
        out.append([
            c.session_date.isoformat(),
            c.assignment_group.name if c.assignment_group else "",
            c.get_category_display(),
            c.get_status_display(),
            author.first_name if author else "",
            author.last_name if author else "",
            c.body,
            c.response_count,
            c.created_at.isoformat(),
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

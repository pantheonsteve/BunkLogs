"""``GET /api/v1/dashboards/bunks/<bunk_id>/?date=<>`` — unified bunk dashboard.

Consolidates the previously role-namespaced
``/api/v1/unit-head/bunks/<id>/`` and ``/api/v1/camper-care/bunks/<id>/``
endpoints into a single role-agnostic surface. Access resolution lives
in :mod:`bunk_logs.api.dashboards.bunk_dashboard_common`; payload
assembly delegates to :func:`build_bunk_dashboard_payload` so the
shape is byte-identical to the per-role endpoints plus a
``role_context`` block the frontend uses to drive role-conditional
chrome (back link, future edit affordances).

The per-role endpoints stay in place for backwards compatibility while
callers migrate; removing them is a follow-up PR.
"""
from __future__ import annotations

from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.dashboards.bunk_dashboard_common import resolve_bunk_dashboard_context
from bunk_logs.api.unit_head.bunk_dashboard import build_bunk_dashboard_payload


class BunkDashboardView(APIView):
    """Per-bunk read payload for any role authorized to see the bunk."""

    permission_classes = [IsAuthenticated]

    def get(self, request, bunk_id: int, *args, **kwargs):
        ctx = resolve_bunk_dashboard_context(request, bunk_id)
        target_date = _parse_date_param(
            request.query_params.get("date"), default=ctx.today,
        )
        if target_date > ctx.today:
            msg = "Future dates are not selectable."
            raise ValidationError(msg)

        payload = build_bunk_dashboard_payload(
            request=request,
            bunk=ctx.bunk,
            target_date=target_date,
            organization=ctx.organization,
            program=ctx.program,
            today=ctx.today,
        )
        payload["role_context"] = {
            "role": ctx.role,
            # Forward-compatible: the unified URL is read-only in v1. The
            # legacy counselor write surface still lives at
            # /bunk/:bunk_id/:date; this flag will gate edit affordances
            # when those are pulled into the unified page in a later PR.
            "can_edit": False,
        }
        return Response(payload)


def _parse_date_param(raw, *, default):
    if not raw:
        return default
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid 'date' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed

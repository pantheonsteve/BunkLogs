"""``GET /api/v1/dashboards/group/<group_id>/`` — unified per-group dashboard.

One endpoint serves every supported ``AssignmentGroup`` type. Access
resolution happens in
:mod:`bunk_logs.api.dashboards.group_dashboard_common`; payload
assembly is dispatched on ``group.group_type`` to one of the
type-specific builders.

For back-compat with the prior bunk-only consolidation, the legacy
``GET /api/v1/dashboards/bunks/<bunk_id>/`` URL is wired to this same
view via a URL alias (see ``api/urls.py``).
"""
from __future__ import annotations

from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.dashboards.group_dashboard_common import resolve_group_dashboard_context
from bunk_logs.api.dashboards.group_payloads import build_classroom_dashboard_payload
from bunk_logs.api.dashboards.group_payloads import build_division_dashboard_payload
from bunk_logs.api.dashboards.group_payloads import build_unit_dashboard_payload
from bunk_logs.api.unit_head.bunk_dashboard import build_bunk_dashboard_payload

# Dispatch table. Group types not represented here surface a 400 with
# a friendly "not yet supported" message so the frontend can render
# its own stub without guessing.
_PAYLOAD_BY_GROUP_TYPE = {
    "bunk": build_bunk_dashboard_payload,
    "unit": build_unit_dashboard_payload,
    "division": build_division_dashboard_payload,
    "classroom": build_classroom_dashboard_payload,
}


class GroupDashboardView(APIView):
    """Per-group read payload for any role authorized to see the group.

    The URL kwarg is named ``group_id`` for the canonical route and
    ``bunk_id`` for the legacy alias. Both flow through the same path
    parameter via ``**kwargs.get(...)`` below.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        group_id = kwargs.get("group_id") or kwargs.get("bunk_id")
        if group_id is None:
            msg = "Group id is required."
            raise ValidationError(msg)

        ctx = resolve_group_dashboard_context(request, int(group_id))
        target_date = _parse_date_param(
            request.query_params.get("date"), default=ctx.today,
        )
        if target_date > ctx.today:
            msg = "Future dates are not selectable."
            raise ValidationError(msg)

        builder = _PAYLOAD_BY_GROUP_TYPE.get(ctx.group.group_type)
        if builder is None:
            msg = (
                f"Dashboard not yet supported for group_type "
                f"'{ctx.group.group_type}'."
            )
            raise ValidationError(msg)

        # Bunk builder still uses the keyword ``bunk=`` (no rename to
        # avoid churn in unit_head/bunk_dashboard.py); everything else
        # takes ``group=``. Branch the call site rather than the helper.
        if ctx.group.group_type == "bunk":
            payload = builder(
                request=request,
                bunk=ctx.group,
                target_date=target_date,
                organization=ctx.organization,
                program=ctx.program,
                today=ctx.today,
            )
        else:
            payload = builder(
                request=request,
                group=ctx.group,
                target_date=target_date,
                organization=ctx.organization,
                program=ctx.program,
                today=ctx.today,
            )

        payload["role_context"] = {
            "role": ctx.role,
            "group_type": ctx.group.group_type,
            # Forward-compatible: the unified URL is read-only in v1.
            # The legacy counselor write surface still lives at
            # /bunk/:bunk_id/:date; this flag will gate edit
            # affordances when those are pulled into the unified page.
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

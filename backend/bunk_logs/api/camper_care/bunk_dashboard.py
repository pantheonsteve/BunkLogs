"""``GET /api/v1/camper-care/bunks/<bunk_id>/?date=<>`` — Story 18 criterion 9.

Camper Care drill-down to the per-bunk dashboard. Delegates payload
construction to :func:`api.unit_head.bunk_dashboard.build_bunk_dashboard_payload`
(extracted in 7_8c) so the view stays focused on viewer resolution
plus the caseload gate. CC's gate uses ``caseload_bunks`` (Supervision
rows with ``target_type='bunk'``) rather than UH's per-counselor
supervision.
"""

from __future__ import annotations

from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.unit_head.bunk_dashboard import build_bunk_dashboard_payload
from bunk_logs.core.models import AssignmentGroup

from .common import caseload_bunks
from .common import viewer_or_403


class CamperCareBunkDashboardView(APIView):
    """Per-bunk read payload for Camper Care."""

    permission_classes = [IsAuthenticated]

    def get(self, request, bunk_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        target_date = _parse_date_param(
            request.query_params.get("date"), default=ctx.today,
        )
        if target_date > ctx.today:
            msg = "Future dates are not selectable."
            raise ValidationError(msg)

        # Caseload gate: viewer must have the bunk on their caseload
        # AS OF TODAY (not the selected date) so history browsing works
        # on currently supervised bunks.
        owned_ids = {b.id for b in caseload_bunks(ctx.membership, today=ctx.today)}
        if int(bunk_id) not in owned_ids:
            msg = "This bunk is not on your caseload."
            raise PermissionDenied(msg)

        bunk = AssignmentGroup.all_objects.filter(
            id=bunk_id, group_type="bunk", is_active=True,
        ).select_related("parent").first()
        if bunk is None:
            msg = "Bunk not found."
            raise NotFound(msg)

        return Response(build_bunk_dashboard_payload(
            request=request,
            bunk=bunk,
            target_date=target_date,
            organization=ctx.organization,
            program=ctx.program,
            today=ctx.today,
        ))


def _parse_date_param(raw, *, default):
    if not raw:
        return default
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid 'date' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed

"""``GET /api/v1/unit-head/staff-reflections/?date=<>`` — supervised bunk staff logs.

Aggregates counselor / JC self-reflections across every bunk the viewer
supervises as Unit Head. Reuses the per-bunk payload from the bunk
dashboard so the frontend can render the same expandable cards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import counselor_self_reflections_for_bunk
from .common import supervised_bunks
from .common import viewer_or_403

if TYPE_CHECKING:
    from datetime import date


def _parse_date_param(raw: str | None, *, default: date) -> date:
    if not raw:
        return default
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid 'date' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


class UnitHeadStaffReflectionsView(APIView):
    """Staff self-reflections for all supervised bunks on a date."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        target_date = _parse_date_param(
            request.query_params.get("date"),
            default=ctx.today,
        )
        if target_date > ctx.today:
            msg = "Future dates are not available."
            raise ValidationError(msg)

        bunks = supervised_bunks(ctx.membership, today=ctx.today)
        payload_bunks = []
        for bunk in bunks:
            entries = counselor_self_reflections_for_bunk(
                request=request,
                bunk=bunk,
                target_date=target_date,
            )
            payload_bunks.append({
                "id": bunk.id,
                "name": bunk.name,
                "slug": bunk.slug,
                "counselor_self_reflections": entries,
            })

        return Response({
            "header": {
                "date": target_date.isoformat(),
                "today": ctx.today.isoformat(),
            },
            "bunks": payload_bunks,
        })

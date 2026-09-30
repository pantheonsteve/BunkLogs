"""Madrich Sunday availability endpoints — Step 4_7, Stories 61-65.

Endpoints
---------
GET    /api/v1/madrich/availability/               -- viewer's upcoming sessions
PUT    /api/v1/madrich/availability/<date>/         -- upsert one session
DELETE /api/v1/madrich/availability/<date>/         -- clear one session

Operational scheduling signal, deliberately separate from ``Reflection``
(Story 62 c3: no day-off toggle on reflections). The payload shape and the
edit-window rules live in ``api/availability_self.py``, shared with the
Faculty calendar so the two roles cannot drift.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.availability_self import EDIT_DEADLINE_RULE
from bunk_logs.api.availability_self import AvailabilityUpsertSerializer
from bunk_logs.api.availability_self import availability_sessions_payload
from bunk_logs.api.availability_self import availability_summary as _summary
from bunk_logs.api.availability_self import clear_commitment
from bunk_logs.api.availability_self import enforce_editable
from bunk_logs.api.availability_self import entry_for
from bunk_logs.api.availability_self import upsert_commitment
from bunk_logs.api.availability_self import validate_session_date
from bunk_logs.core.time_utils import get_org_timezone

from .common import viewer_or_403

CALENDAR_URL = "/madrich/availability"


def availability_summary(ctx) -> dict:
    """Madrich dashboard card payload (AC3.1)."""
    return _summary(ctx, calendar_url=CALENDAR_URL)


class MadrichAvailabilityListView(APIView):
    """``GET /api/v1/madrich/availability/`` -- the viewer's upcoming sessions."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        return Response({
            "program": {
                "id": ctx.program.id,
                "name": ctx.program.display_name,
                "slug": ctx.program.slug,
            },
            "timezone": str(get_org_timezone(ctx.organization)),
            "edit_deadline_rule": EDIT_DEADLINE_RULE,
            "sessions": availability_sessions_payload(ctx),
        })


class MadrichAvailabilityDetailView(APIView):
    """``PUT``/``DELETE /api/v1/madrich/availability/<session_date>/``."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["put", "delete", "head", "options"]

    def put(self, request, session_date: str, *args, **kwargs):
        ctx = viewer_or_403(request)
        target = validate_session_date(ctx, session_date)
        enforce_editable(ctx, target)

        ser = AvailabilityUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        row = upsert_commitment(ctx, target, ser.validated_data)
        return Response(entry_for(ctx, target, row))

    def delete(self, request, session_date: str, *args, **kwargs):
        ctx = viewer_or_403(request)
        target = validate_session_date(ctx, session_date)
        enforce_editable(ctx, target)

        clear_commitment(ctx, target)
        return Response(status=status.HTTP_204_NO_CONTENT)

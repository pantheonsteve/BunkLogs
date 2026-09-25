"""Faculty's own Sunday availability endpoints.

Endpoints
---------
GET    /api/v1/faculty/availability/           -- viewer's upcoming sessions
PUT    /api/v1/faculty/availability/<date>/     -- upsert one session
DELETE /api/v1/faculty/availability/<date>/     -- clear one session

Same rows, horizon, and Saturday-18:00 lock as the Madrich calendar (see
``api/availability_self.py``); only the viewer resolution differs, so a
faculty member answers for themselves here while
``faculty/availability.py`` stays the read-only classroom view of the
Madrichim they supervise. Programs with no ``session_dates`` return an
empty ``sessions`` list, which is what keeps Crane Lake out.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.availability_self import EDIT_DEADLINE_RULE
from bunk_logs.api.availability_self import AvailabilityUpsertSerializer
from bunk_logs.api.availability_self import availability_sessions_payload
from bunk_logs.api.availability_self import clear_commitment
from bunk_logs.api.availability_self import enforce_editable
from bunk_logs.api.availability_self import entry_for
from bunk_logs.api.availability_self import upsert_commitment
from bunk_logs.api.availability_self import validate_session_date
from bunk_logs.core.time_utils import get_org_timezone

from .common import viewer_or_403

CALENDAR_URL = "/faculty/availability"


class FacultyAvailabilityListView(APIView):
    """``GET /api/v1/faculty/availability/`` -- the viewer's upcoming sessions."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        return Response({
            "program": {
                "id": ctx.program.id,
                "name": ctx.program.name,
                "slug": ctx.program.slug,
            },
            "timezone": str(get_org_timezone(ctx.organization)),
            "edit_deadline_rule": EDIT_DEADLINE_RULE,
            "sessions": availability_sessions_payload(ctx),
        })


class FacultyAvailabilityDetailView(APIView):
    """``PUT``/``DELETE /api/v1/faculty/availability/<session_date>/``."""

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

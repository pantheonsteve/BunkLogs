"""Madrich Sunday availability endpoints — Step 4_7, Stories 61-65.

Endpoints
---------
GET    /api/v1/madrich/availability/               -- viewer's upcoming sessions
PUT    /api/v1/madrich/availability/<date>/         -- upsert one session
DELETE /api/v1/madrich/availability/<date>/         -- clear one session

Operational scheduling signal, deliberately separate from ``Reflection``
(Story 62 c3: no day-off toggle on reflections). ``session_dates`` lives on
``Program.settings`` (Step 4_1); the shared helpers here back both this
endpoint and the ``availability`` summary block on the Madrich dashboard
(``dashboard.py``) so the two never disagree on what "upcoming" means.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.dateparse import parse_date
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import MadrichAvailability
from bunk_logs.core.scheduling.availability_windows import is_editable
from bunk_logs.core.scheduling.sessions import program_session_dates
from bunk_logs.core.time_utils import get_org_timezone

from .common import viewer_or_403

if TYPE_CHECKING:
    from datetime import date as date_type

    from .common import ViewerContext


MAX_UPCOMING_SESSIONS = 16
EDIT_DEADLINE_RULE = "saturday_18:00_eastern"


def upcoming_session_dates(ctx: ViewerContext) -> list[date_type]:
    """Configured sessions from today forward, capped at 16 weeks (perf guard)."""
    all_dates = program_session_dates(ctx.program)
    upcoming = [d for d in all_dates if d >= ctx.today]
    return upcoming[:MAX_UPCOMING_SESSIONS]


def _session_label(d: date_type) -> str:
    return f"{d.strftime('%a %b')} {d.day}"


def _commitment_payload(row: MadrichAvailability | None) -> dict | None:
    if row is None:
        return None
    return {
        "status": row.status,
        "note": row.note,
        "updated_at": row.updated_at.isoformat(),
    }


def availability_sessions_payload(ctx: ViewerContext) -> list[dict]:
    """One entry per upcoming session, with the viewer's commitment (or ``None``)."""
    session_dates = upcoming_session_dates(ctx)
    commitments = {
        row.session_date: row
        for row in MadrichAvailability.objects.filter(
            program=ctx.program, person=ctx.person, session_date__in=session_dates,
        )
    }
    return [
        {
            "session_date": d.isoformat(),
            "label": _session_label(d),
            "editable": is_editable(d, ctx.organization),
            "commitment": _commitment_payload(commitments.get(d)),
        }
        for d in session_dates
    ]


def availability_summary(ctx: ViewerContext) -> dict:
    """Dashboard card payload (AC3.1): unset count + next session preview."""
    sessions = availability_sessions_payload(ctx)
    unset_count = sum(1 for s in sessions if s["commitment"] is None)
    next_session = sessions[0] if sessions else None
    return {
        "upcoming_unset_count": unset_count,
        "next_session_date": next_session["session_date"] if next_session else None,
        "next_session_status": (
            next_session["commitment"]["status"]
            if next_session and next_session["commitment"] else None
        ),
        "calendar_url": "/madrich/availability",
    }


class MadrichAvailabilityListView(APIView):
    """``GET /api/v1/madrich/availability/`` -- the viewer's upcoming sessions."""

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


class MadrichAvailabilityUpsertSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=MadrichAvailability.STATUS_CHOICES)
    note = serializers.CharField(max_length=280, required=False, allow_blank=True, default="")

    def validate_note(self, value: str) -> str:
        return value.strip()


class MadrichAvailabilityDetailView(APIView):
    """``PUT``/``DELETE /api/v1/madrich/availability/<session_date>/``."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["put", "delete", "head", "options"]

    def put(self, request, session_date: str, *args, **kwargs):
        ctx = viewer_or_403(request)
        target = _validate_session_date(ctx, session_date)
        _enforce_editable(ctx, target)

        ser = MadrichAvailabilityUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        row, _created = MadrichAvailability.objects.update_or_create(
            organization=ctx.organization,
            program=ctx.program,
            person=ctx.person,
            session_date=target,
            defaults={
                "status": ser.validated_data["status"],
                "note": ser.validated_data["note"],
            },
        )
        return Response(_entry_for(ctx, target, row))

    def delete(self, request, session_date: str, *args, **kwargs):
        ctx = viewer_or_403(request)
        target = _validate_session_date(ctx, session_date)
        _enforce_editable(ctx, target)

        MadrichAvailability.objects.filter(
            organization=ctx.organization,
            program=ctx.program,
            person=ctx.person,
            session_date=target,
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _validate_session_date(ctx: ViewerContext, raw: str) -> date_type:
    parsed = parse_date(raw)
    if parsed is None or parsed.weekday() != 6:
        msg = "Invalid session_date; expected an ISO Sunday (YYYY-MM-DD)."
        raise ValidationError(msg)
    configured = program_session_dates(ctx.program)
    if configured and parsed not in configured:
        msg = "session_date is not a configured session for this program."
        raise ValidationError(msg)
    return parsed


def _enforce_editable(ctx: ViewerContext, target: date_type) -> None:
    if not is_editable(target, ctx.organization):
        msg = "Availability for this Sunday locked Saturday at 6:00 PM."
        raise PermissionDenied(msg)


def _entry_for(ctx: ViewerContext, target: date_type, row: MadrichAvailability) -> dict:
    return {
        "session_date": target.isoformat(),
        "label": _session_label(target),
        "editable": is_editable(target, ctx.organization),
        "commitment": _commitment_payload(row),
    }

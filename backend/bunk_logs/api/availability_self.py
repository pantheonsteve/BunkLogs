"""Self-service Sunday availability, shared by the Madrich and Faculty roles.

Both roles answer the same question ("which program Sundays am I in for?")
against the same rows, so the payload shape, the 16-week horizon, and the
Saturday-18:00 edit lock live here and the per-role modules only differ in
how they resolve the viewer and which calendar route they link to.

``ctx`` is duck-typed: any object with ``person``/``organization``/
``program``/``today`` works, which both roles' ``ViewerContext`` satisfy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.dateparse import parse_date
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError

from bunk_logs.core.models import MadrichAvailability
from bunk_logs.core.scheduling.availability_windows import is_editable
from bunk_logs.core.scheduling.sessions import program_session_dates

if TYPE_CHECKING:
    from datetime import date as date_type


MAX_UPCOMING_SESSIONS = 16
EDIT_DEADLINE_RULE = "saturday_18:00_eastern"


class AvailabilityUpsertSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=MadrichAvailability.STATUS_CHOICES)
    note = serializers.CharField(max_length=280, required=False, allow_blank=True, default="")

    def validate_note(self, value: str) -> str:
        return value.strip()


def upcoming_session_dates(ctx) -> list[date_type]:
    """Configured sessions from today forward, capped at 16 weeks (perf guard)."""
    all_dates = program_session_dates(ctx.program)
    upcoming = [d for d in all_dates if d >= ctx.today]
    return upcoming[:MAX_UPCOMING_SESSIONS]


def session_label(d: date_type) -> str:
    return f"{d.strftime('%a %b')} {d.day}"


def commitment_payload(row: MadrichAvailability | None) -> dict | None:
    if row is None:
        return None
    return {
        "status": row.status,
        "note": row.note,
        "updated_at": row.updated_at.isoformat(),
    }


def availability_sessions_payload(ctx) -> list[dict]:
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
            "label": session_label(d),
            "editable": is_editable(d, ctx.organization),
            "commitment": commitment_payload(commitments.get(d)),
        }
        for d in session_dates
    ]


def availability_summary(ctx, *, calendar_url: str) -> dict:
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
        "calendar_url": calendar_url,
    }


def validate_session_date(ctx, raw: str) -> date_type:
    parsed = parse_date(raw)
    if parsed is None or parsed.weekday() != 6:
        msg = "Invalid session_date; expected an ISO Sunday (YYYY-MM-DD)."
        raise ValidationError(msg)
    configured = program_session_dates(ctx.program)
    if configured and parsed not in configured:
        msg = "session_date is not a configured session for this program."
        raise ValidationError(msg)
    return parsed


def enforce_editable(ctx, target: date_type) -> None:
    if not is_editable(target, ctx.organization):
        msg = "Availability for this Sunday locked Saturday at 6:00 PM."
        raise PermissionDenied(msg)


def entry_for(ctx, target: date_type, row: MadrichAvailability | None) -> dict:
    return {
        "session_date": target.isoformat(),
        "label": session_label(target),
        "editable": is_editable(target, ctx.organization),
        "commitment": commitment_payload(row),
    }


def upsert_commitment(ctx, target: date_type, validated: dict) -> MadrichAvailability:
    row, _created = MadrichAvailability.objects.update_or_create(
        organization=ctx.organization,
        program=ctx.program,
        person=ctx.person,
        session_date=target,
        defaults={"status": validated["status"], "note": validated["note"]},
    )
    return row


def clear_commitment(ctx, target: date_type) -> None:
    MadrichAvailability.objects.filter(
        organization=ctx.organization,
        program=ctx.program,
        person=ctx.person,
        session_date=target,
    ).delete()

"""``GET /api/v1/camper-care/campers/<camper_id>/?date=&range=`` — Story 18 + 21.

Camper Care drill-down to the per-camper dashboard. Delegates to the
shared :func:`api.unit_head.camper_dashboard.build_camper_dashboard_payload`
so the section contract (trend grid, today's reflection, scores,
flags, specialist reports, camper-care notes) stays role-agnostic.

Access gate: the camper must be rostered on a bunk currently on the
viewer's Camper Care caseload. Overlapping caseloads (CC2) are allowed
naturally — any CC member with the bunk on their caseload can open
the camper.
"""

from __future__ import annotations

from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.unit_head.camper_dashboard import build_camper_dashboard_payload
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Flag
from bunk_logs.core.models import Person

from .common import caseload_bunks
from .common import viewer_or_403
from .flags import _flag_payload


class CamperCareCamperDashboardView(APIView):
    """Per-camper read payload for Camper Care."""

    permission_classes = [IsAuthenticated]

    def get(self, request, camper_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        target_date = _parse_date_param(
            request.query_params.get("date"), default=ctx.today,
        )
        if target_date > ctx.today:
            msg = "Future dates are not selectable."
            raise ValidationError(msg)

        camper = Person.all_objects.filter(
            id=camper_id, organization=ctx.organization,
        ).first()
        if camper is None:
            msg = "Camper not found."
            raise NotFound(msg)

        if not _viewer_has_camper_on_caseload(ctx, camper):
            msg = "This camper is not on your caseload."
            raise PermissionDenied(msg)

        payload = build_camper_dashboard_payload(
            request=request,
            camper=camper,
            organization=ctx.organization,
            program=ctx.program,
            target_date=target_date,
            range_key=request.query_params.get("range") or "last_4_weeks",
            date_start_raw=request.query_params.get("date_start"),
            date_end_raw=request.query_params.get("date_end"),
        )
        # CC notes date-range filter (Step 7_8d). When `notes_from` and/or
        # `notes_to` are passed, clamp the notes lists to that window so
        # CC can scope a long retrospective without re-fetching the
        # broader trend data. UH behaviour is intentionally unchanged
        # (this filter lives only on the CC endpoint).
        notes_from = _parse_optional_date(request.query_params.get("notes_from"))
        notes_to = _parse_optional_date(request.query_params.get("notes_to"))
        if notes_from or notes_to:
            for key in ("specialist_reports", "camper_care_notes"):
                section = payload.get(key) or {}
                items = section.get("items") or []
                section["items"] = [
                    item for item in items
                    if _within(item.get("created_at"), notes_from, notes_to)
                ]
                section["filtered_by_date_range"] = True
                payload[key] = section
        payload["notes_filter"] = {
            "from": notes_from.isoformat() if notes_from else None,
            "to": notes_to.isoformat() if notes_to else None,
        }
        payload["flag_history"] = _flag_history_for_camper(
            camper=camper, program=ctx.program, today=ctx.today,
        )
        return Response(payload)


def _within(created_at_iso: str | None, lo, hi) -> bool:
    if not created_at_iso:
        return True
    raw = created_at_iso.split("T", 1)[0]
    when = parse_date(raw)
    if when is None:
        return True
    if lo and when < lo:
        return False
    if hi and when > hi:  # noqa: SIM103
        return False
    return True


def _parse_optional_date(raw):
    if not raw:
        return None
    parsed = parse_date(raw)
    if parsed is None:
        msg = (
            "Invalid date in `notes_from`/`notes_to`; expected YYYY-MM-DD."
        )
        raise ValidationError(msg)
    return parsed


def _flag_history_for_camper(*, camper: Person, program, today) -> list[dict]:
    """All camper-care flags raised on this camper, newest first.

    Includes resolved + reopened flags so the CC reader sees the full
    arc on the camper dashboard. Reuses ``_flag_payload`` for shape
    parity with the workspace list.
    """
    rows = (
        Flag.objects.filter(
            program=program,
            subject_camper=camper,
            flagged_for_role="camper_care",
        )
        .select_related("subject_camper", "raised_by_membership__person")
        .order_by("-created_at")
    )
    return [_flag_payload(f, today=today) for f in rows]


def _viewer_has_camper_on_caseload(ctx, camper: Person) -> bool:
    """True iff ``camper`` is rostered on a bunk in the viewer's caseload."""
    bunk_ids = {b.id for b in caseload_bunks(ctx.membership, today=ctx.today)}
    if not bunk_ids:
        return False
    return AssignmentGroupMembership.objects.filter(
        group_id__in=bunk_ids,
        person=camper,
        role_in_group="subject",
        is_active=True,
    ).exists()


def _parse_date_param(raw, *, default):
    if not raw:
        return default
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid 'date' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed

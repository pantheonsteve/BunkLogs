"""``GET /api/v1/unit-head/campers/<camper_id>/?date=&range=`` — Story 13.

The Camper Dashboard payload is the canonical "what does role X see
about Camper Y on Date Z?" response. It's owned by Unit Head as the
first consumer but the helper layer below is intentionally
role-agnostic so Camper Care (Step 7_8), LT (Step 7_12), and Admin
(Step 7_13) can reuse it.

Visibility is enforced server-side per Story 13 criterion 7:

* reflection content goes through ``reflections_visible_for_user``;
* specialist + camper-care notes go through ``notes_visible_to`` and
  sensitive notes excluded for the viewer are surfaced only as a
  per-content-type count (the spec's *"1 sensitive note (Camper Care)"*
  placeholder).

Trend ranges (criterion 2):

* ``this_week``      — last 7 days inclusive of ``date``.
* ``last_4_weeks``   — last 28 days inclusive.
* ``full_session``   — program ``start_date`` → program ``end_date``,
                       clamped at today on the right.
* ``custom``         — caller passes ``date_start`` / ``date_end``.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from typing import Any

from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import camper_reflection_template
from bunk_logs.api.counselor.common import person_display_name
from bunk_logs.core.filters import notes_visible_to
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Note
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.reflection_scores import iter_scored_fields
from bunk_logs.core.reflection_scores import resolve_rating_cells

from .common import supervised_bunks
from .common import viewer_or_403

RANGE_CHOICES: frozenset[str] = frozenset({
    "this_week", "last_4_weeks", "full_session", "custom",
})


class UnitHeadCamperDashboardView(APIView):
    """Shared Camper Dashboard payload — Unit Head entry point."""

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

        # Supervision gate: viewer must supervise a bunk this camper is
        # rostered to (today's roster — UH retains access across history).
        if not _viewer_supervises_camper(ctx, camper):
            msg = "You do not supervise this camper."
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
        return Response(payload)


# ---------------------------------------------------------------------------
# Shared payload builder (role-agnostic; reused by future role flows)
# ---------------------------------------------------------------------------


def build_camper_dashboard_payload(
    *,
    request,
    camper: Person,
    organization,
    program,
    target_date: date,
    range_key: str = "last_4_weeks",
    date_start_raw: str | None = None,
    date_end_raw: str | None = None,
) -> dict[str, Any]:
    """Compose the Camper Dashboard payload for any role.

    Pulled out of the view so future role flows (LT, Camper Care,
    Admin) can call it with their own viewer-resolution + supervision
    gate but share the visibility-filtered content. Visibility is
    enforced inside the helper via ``request.user`` so the caller
    cannot accidentally widen audience by passing a different Person.
    """
    if range_key not in RANGE_CHOICES:
        msg = f"Unknown range: {range_key}."
        raise ValidationError(msg)

    period_start, period_end = _resolve_range(
        range_key=range_key,
        anchor=target_date,
        program=program,
        date_start_raw=date_start_raw,
        date_end_raw=date_end_raw,
    )

    template = camper_reflection_template(organization, program)

    # Today's full reflection (visibility-filtered for the request user).
    today_reflection = None
    today_payload: dict[str, Any] | None = None
    if template is not None:
        today_reflection = (
            reflections_visible_for_user(
                request.user,
                Reflection.all_objects.filter(
                    template=template,
                    subject=camper,
                    period_start=target_date,
                    period_end=target_date,
                    is_complete=True,
                ).select_related("author", "template"),
            ).order_by("-submitted_at").first()
        )
        if today_reflection is not None:
            today_payload = _serialize_today_reflection(today_reflection, template)

    # Trend data — one numeric per scored cell per date in the period.
    trend_payload = (
        _build_trend_payload(
            request=request,
            template=template,
            camper=camper,
            period_start=period_start,
            period_end=period_end,
        ) if template else {"series": [], "scale_max": 5}
    )

    # Specialist + camper-care notes (visibility-filtered).
    notes_payload = _build_notes_payload(
        request=request, camper=camper, target_date=target_date,
    )

    return {
        "header": {
            "camper": _camper_brief(camper),
            "date": target_date.isoformat(),
        },
        "trend": trend_payload,
        "today_reflection": today_payload,
        "today_scores": _today_scores(today_reflection, template),
        "today_flags": _today_flags(today_reflection, template),
        "specialist_reports": notes_payload["specialist"],
        "camper_care_notes": notes_payload["camper_care"],
    }


# ---------------------------------------------------------------------------
# Range resolution
# ---------------------------------------------------------------------------


def _resolve_range(
    *,
    range_key: str,
    anchor: date,
    program,
    date_start_raw: str | None,
    date_end_raw: str | None,
) -> tuple[date, date]:
    if range_key == "this_week":
        start = anchor - timedelta(days=6)
        return start, anchor
    if range_key == "last_4_weeks":
        start = anchor - timedelta(days=27)
        return start, anchor
    if range_key == "full_session":
        start = program.start_date or (anchor - timedelta(days=27))
        end = min(program.end_date or anchor, anchor)
        if end < start:
            start, end = end, start
        return start, end
    # custom
    start = parse_date(date_start_raw or "") or (anchor - timedelta(days=27))
    end = parse_date(date_end_raw or "") or anchor
    if end < start:
        start, end = end, start
    end = min(end, anchor)
    return start, end


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------


def _build_trend_payload(
    *,
    request,
    template,
    camper: Person,
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    """One series per scored cell across the period.

    Missing days appear as ``None`` values rather than zeros (Story 13
    criterion 4). The returned shape lets the frontend toggle
    individual dimensions on/off via the legend (criterion 3) by
    iterating ``series`` directly.
    """
    refs = list(
        reflections_visible_for_user(
            request.user,
            Reflection.all_objects.filter(
                template=template,
                subject=camper,
                period_start__gte=period_start,
                period_end__lte=period_end,
                is_complete=True,
            ).order_by("period_end", "submitted_at"),
        ),
    )

    # Most-recent-per-day collapse so a re-submission overwrites the cell.
    per_day: dict[date, Reflection] = {}
    for r in refs:
        existing = per_day.get(r.period_end)
        if existing is None or r.submitted_at > existing.submitted_at:
            per_day[r.period_end] = r

    columns = list(iter_scored_fields(template))
    series: list[dict[str, Any]] = []
    days = _date_range(period_start, period_end)
    scale_max_overall = 5
    for field, label, sm in columns:
        scale_max_overall = max(scale_max_overall, sm)
        points: list[dict[str, Any]] = []
        for d in days:
            r = per_day.get(d)
            value: float | None = None
            reflection_id: int | None = None
            if r is not None:
                cells = resolve_rating_cells(field, r.answers or {})
                value = cells.get(label)
                reflection_id = r.id
            points.append({
                "date": d.isoformat(),
                "value": (round(value, 2) if value is not None else None),
                "reflection_id": reflection_id,
            })
        series.append({
            "label": label,
            "field_key": field.get("key"),
            "field_type": field.get("type"),
            "scale_max": sm,
            "points": points,
        })

    return {
        "series": series,
        "scale_max": scale_max_overall,
        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
    }


def _date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


# ---------------------------------------------------------------------------
# Today's reflection + scores + flags
# ---------------------------------------------------------------------------


def _serialize_today_reflection(reflection: Reflection, template) -> dict:
    """Full reflection answers projected through the template field order.

    Story 13 criterion 1 wants the answers shown "in template field
    order" — the consumer renders ``fields`` directly, each carrying
    its answer payload so the frontend doesn't have to dereference
    schema separately.
    """
    answers = reflection.answers or {}
    fields_out: list[dict[str, Any]] = []
    for f in (template.schema or {}).get("fields") or []:
        if not isinstance(f, dict):
            continue
        key = f.get("key")
        if not isinstance(key, str):
            continue
        fields_out.append({
            "key": key,
            "type": f.get("type"),
            "dashboard_role": f.get("dashboard_role"),
            "prompts": f.get("prompts") or {},
            "scale_labels": f.get("scale_labels") or {},
            "scale": f.get("scale"),
            "categories": f.get("categories") or [],
            "options": f.get("options") or [],
            "answer": answers.get(key),
        })
    return {
        "id": reflection.id,
        "author": person_display_name(reflection.author),
        "language": reflection.language,
        "submitted_at": reflection.submitted_at.isoformat() if reflection.submitted_at else None,
        "team_visibility": reflection.team_visibility,
        "fields": fields_out,
    }


def _today_scores(reflection: Reflection | None, template) -> list[dict]:
    """All scored cells for today's reflection."""
    if reflection is None or template is None:
        return []
    cells_out: list[dict] = []
    answers = reflection.answers or {}
    for f in (template.schema or {}).get("fields") or []:
        if not isinstance(f, dict):
            continue
        if f.get("type") not in ("single_rating", "rating_group"):
            continue
        for label, value in resolve_rating_cells(f, answers).items():
            cells_out.append({
                "label": label,
                "value": (round(value, 2) if value is not None else None),
                "scale_max": _scale_max(f),
            })
    return cells_out


def _today_flags(reflection: Reflection | None, template) -> list[dict]:
    """Boolean / yes-no flags surfaced in today's reflection.

    Picks up help-request fields and any ``yes_no`` whose answer is
    truthy. Returns the field key + prompt so the frontend can show
    them without redoing schema lookups.
    """
    if reflection is None or template is None:
        return []
    out: list[dict] = []
    answers = reflection.answers or {}
    for f in (template.schema or {}).get("fields") or []:
        if not isinstance(f, dict):
            continue
        if f.get("type") not in ("yes_no", "single_choice", "multiple_choice"):
            continue
        key = f.get("key")
        if not isinstance(key, str):
            continue
        v = answers.get(key)
        if not _is_truthy_flag(v):
            continue
        out.append({
            "key": key,
            "value": v,
            "prompts": f.get("prompts") or {},
            "dashboard_role": f.get("dashboard_role"),
        })
    return out


def _is_truthy_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "1"}
    if isinstance(value, list):
        return any(_is_truthy_flag(v) for v in value)
    return False


def _scale_max(field: dict) -> int:
    from bunk_logs.core.reflection_scores import scale_max
    return scale_max(field)


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


def _build_notes_payload(
    *, request, camper: Person, target_date: date,
) -> dict[str, dict]:
    """Visibility-filtered specialist + camper-care notes for one camper.

    Sensitive notes that the viewer can't read are NOT serialized;
    instead each content type returns a ``sensitive_count`` so the
    frontend can render the placeholder per Story 13 / Story 15
    criterion 4.
    """
    base = Note.all_objects.filter(subject=camper).select_related("author")
    visible = notes_visible_to(request.user, base)
    visible_ids = set(visible.values_list("id", flat=True))

    return {
        "specialist": _split_notes(
            visible, base, visible_ids,
            Note.NoteType.SPECIALIST, target_date,
        ),
        "camper_care": _split_notes(
            visible, base, visible_ids,
            Note.NoteType.CAMPER_CARE, target_date,
        ),
    }


def _split_notes(
    visible_qs, base_qs, visible_ids: set[int],
    note_type: str, target_date: date,
) -> dict[str, Any]:
    filtered = visible_qs.filter(note_type=note_type).order_by("-created_at")
    items: list[dict] = []
    for n in filtered:
        body = n.body or ""
        preview = body if len(body) <= 200 else (body[:200].rstrip() + "…")
        items.append({
            "id": n.id,
            "author": person_display_name(n.author),
            "created_at": n.created_at.isoformat(),
            "body": body,
            "preview": preview,
            "is_long": len(body) > 200,
            "is_sensitive": bool(n.is_sensitive),
            "is_today": n.created_at.date() == target_date,
        })
    sensitive_excluded = base_qs.exclude(id__in=visible_ids).filter(
        note_type=note_type, is_sensitive=True,
    ).count()
    return {"items": items, "sensitive_excluded_count": sensitive_excluded}


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def _camper_brief(camper: Person) -> dict:
    return {
        "id": camper.id,
        "first_name": camper.first_name,
        "last_name": camper.last_name,
        "preferred_name": camper.preferred_name,
    }


def _viewer_supervises_camper(ctx, camper: Person) -> bool:
    """True iff the camper is rostered on a bunk under the UH's supervision."""
    bunks = supervised_bunks(ctx.membership, today=ctx.today)
    if not bunks:
        return False
    bunk_ids = {b.id for b in bunks}
    return AssignmentGroupMembership.objects.filter(
        group_id__in=bunk_ids,
        person=camper,
        role_in_group="subject",
        is_active=True,
    ).exists()


def _parse_date_param(raw: str | None, *, default: date) -> date:
    if not raw:
        return default
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid 'date' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed

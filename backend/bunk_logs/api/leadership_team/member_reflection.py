"""``GET /api/v1/leadership-team/teams/<team_role>/members/<membership_id>/reflection/``.

Story 47 — individual reflection reader for one team member.

Read-only. Pulls the most-recent reflection for the period, the trend
graph data over the configured window (default 14 days for daily
cadence, 8 periods for non-daily), and the visibility-filtered
reflection payload using the shared
:func:`api.unit_head.camper_dashboard.build_camper_dashboard_payload`
trend helpers.

LT readers see translation embeds for non-English content via the
existing reflection serializer (Story 44); they may NOT edit, comment,
or read prior edit history — only "Edited [time]" indicator (Story
47 c5).
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from typing import Any

from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import person_display_name
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionAttentionMarker
from bunk_logs.core.models import TranslationRecord
from bunk_logs.core.reflection_scores import iter_scored_fields
from bunk_logs.core.reflection_scores import resolve_rating_cells

from .common import resolve_period
from .common import team_memberships
from .common import viewer_or_403
from .dashboard import _team_template_for_role
from .team_dashboard import _ensure_supervised


class LeadershipTeamMemberReflectionView(APIView):
    """One team member's reflection for a period, with trend graph + meta."""

    permission_classes = [IsAuthenticated]

    def get(self, request, team_role: str, membership_id: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        _ensure_supervised(ctx, team_role)

        # Verify the membership is on the team.
        team = list(team_memberships(ctx.membership, team_role, today=ctx.today))
        member = next((m for m in team if m.id == membership_id), None)
        if member is None:
            msg = "This member is not on the supervised team."
            raise NotFound(msg)
        person = member.person
        if person is None:
            msg = "Member has no Person profile."
            raise NotFound(msg)

        template = _team_template_for_role(ctx.organization, ctx.program, team_role)
        period_raw = request.query_params.get("period")
        anchor = _parse_date_param(period_raw, default=ctx.today)
        if anchor > ctx.today:
            msg = "Future periods are not selectable."
            raise ValidationError(msg)

        if template is None:
            return Response({
                "header": _header(person, member, period=None, language_pref=person.preferred_language),
                "metadata": None,
                "content": None,
                "trend": {"series": [], "scale_max": 5, "period": None},
                "attention_markers": [],
            })

        period_start, period_end = resolve_period(
            template, anchor=anchor, program=ctx.program,
        )

        # Visibility-filtered current-period reflection (most recent).
        current_qs = (
            Reflection.all_objects.filter(
                template=template,
                subject=person,
                period_start=period_start,
                period_end=period_end,
                is_complete=True,
            )
            .select_related("author", "template")
        )
        reflection = (
            reflections_visible_for_user(request.user, current_qs)
            .order_by("-submitted_at")
            .first()
        )
        content = _serialize_reflection(reflection, template) if reflection else None
        trend_payload = _build_trend(
            request=request, template=template, person=person,
            anchor=anchor, program=ctx.program,
        )

        marker_rows: list[dict] = []
        if reflection is not None:
            marker_rows = [
                {
                    "id": marker.id,
                    "marker_membership_id": marker.marker_membership_id,
                    "person_name": person_display_name(marker.marker_membership.person)
                                   if marker.marker_membership and marker.marker_membership.person else "",
                    "note": marker.note,
                    "created_at": marker.created_at.isoformat(),
                }
                for marker in ReflectionAttentionMarker.objects.filter(
                    reflection=reflection,
                ).select_related("marker_membership__person").order_by("-created_at")
            ]

        return Response({
            "header": _header(
                person, member,
                period={"start": period_start.isoformat(),
                        "end": period_end.isoformat(),
                        "cadence": template.cadence},
                language_pref=person.preferred_language,
            ),
            "metadata": _metadata(reflection),
            "content": content,
            "trend": trend_payload,
            "attention_markers": marker_rows,
        })


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------


def _parse_date_param(raw: str | None, *, default: date) -> date:
    if not raw:
        return default
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid 'period' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


def _header(person, membership: Membership, *, period, language_pref: str) -> dict:
    return {
        "person": {
            "id": person.id,
            "name": person_display_name(person),
            "first_name": person.first_name,
            "last_name": person.last_name,
            "preferred_name": person.preferred_name,
        },
        "role": membership.role,
        "membership_id": membership.id,
        "language_preference": language_pref,
        "period": period,
    }


def _metadata(reflection: Reflection | None) -> dict | None:
    if reflection is None:
        return None
    edited = (
        reflection.updated_at is not None
        and reflection.submitted_at is not None
        and (reflection.updated_at - reflection.submitted_at).total_seconds() > 1
    )
    return {
        "reflection_id": reflection.id,
        "submitted_at": reflection.submitted_at.isoformat() if reflection.submitted_at else None,
        "last_edited_at": reflection.updated_at.isoformat() if edited else None,
        "language_of_authorship": reflection.language,
        "team_visibility": reflection.team_visibility,
    }


def _serialize_reflection(reflection: Reflection, template) -> dict:
    """Render answers in template field order with translation embed."""
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
    translation = None
    if reflection.language != "en":
        record = TranslationRecord.latest_for("reflection", reflection.pk)
        if record is None:
            translation = {
                "status": "pending",
                "source_language": reflection.language,
                "target_language": "en",
                "translated_text": "",
            }
        else:
            translation = {
                "id": str(record.id),
                "status": record.status,
                "source_language": record.source_language,
                "target_language": record.target_language,
                "translated_text": record.translated_text,
            }
    return {
        "fields": fields_out,
        "translation": translation,
    }


def _build_trend(
    *, request, template, person, anchor: date, program,
) -> dict:
    """Trend payload over the configured window.

    Default windows (Story 47 c1):
    * daily cadence -> last 14 days inclusive.
    * non-daily cadences -> last 8 periods inclusive.
    """
    cadence = (template.cadence or "daily").lower()
    if cadence == "daily":
        period_end = anchor
        period_start = anchor - timedelta(days=13)
        periods = [
            (period_start + timedelta(days=i), period_start + timedelta(days=i))
            for i in range(14)
        ]
    else:
        # Walk back N periods of the same cadence.
        periods = []
        cursor = anchor
        for _ in range(8):
            ps, pe = resolve_period(template, anchor=cursor, program=program)
            periods.append((ps, pe))
            cursor = ps - timedelta(days=1)
        periods.reverse()
        period_start, period_end = periods[0][0], periods[-1][1]

    qs = (
        Reflection.all_objects.filter(
            template=template,
            subject=person,
            period_start__gte=period_start,
            period_end__lte=period_end,
            is_complete=True,
        )
        .order_by("period_end", "submitted_at")
    )
    reflections = list(reflections_visible_for_user(request.user, qs))

    by_period: dict[tuple[date, date], Reflection] = {}
    for r in reflections:
        key = (r.period_start, r.period_end)
        existing = by_period.get(key)
        if existing is None or r.submitted_at > existing.submitted_at:
            by_period[key] = r

    series: list[dict[str, Any]] = []
    scale_max_overall = 5
    for field, label, sm in iter_scored_fields(template):
        scale_max_overall = max(scale_max_overall, sm)
        points: list[dict[str, Any]] = []
        for ps, pe in periods:
            r = by_period.get((ps, pe))
            value: float | None = None
            reflection_id = None
            if r is not None:
                cells = resolve_rating_cells(field, r.answers or {})
                value = cells.get(label)
                reflection_id = r.id
            points.append({
                "period_start": ps.isoformat(),
                "period_end": pe.isoformat(),
                "value": round(value, 2) if value is not None else None,
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
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
            "cadence": cadence,
        },
    }

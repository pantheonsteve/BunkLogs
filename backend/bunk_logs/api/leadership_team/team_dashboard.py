"""``GET /api/v1/leadership-team/teams/<team_role>/`` — Story 46.

Per-team dashboard for one team the LT viewer supervises:

* Header: team name, supervisors, member count, current period, date.
* Submission status: grouped submitted / not submitted / day-off counts
  + per-member status rows.
* Flagged reflections: current-period low ratings (concerning) +
  user-flagged ``ReflectionAttentionMarker`` rows.
* Member list: row per active team member with status + one-line
  preview.

Date selector defaults to current period; navigating to a prior
period adjusts ``period_start``/``period_end`` per the team's template
cadence. Future dates are rejected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.dateparse import parse_date

if TYPE_CHECKING:
    from datetime import date
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import person_display_name
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionAttentionMarker
from bunk_logs.core.models import Supervision

from .common import resolve_period
from .common import team_memberships
from .common import viewer_or_403
from .dashboard import _team_template_for_role


class LeadershipTeamTeamDashboardView(APIView):
    """Team dashboard payload for one supervised role."""

    permission_classes = [IsAuthenticated]

    def get(self, request, team_role: str, *args, **kwargs):
        ctx = viewer_or_403(request)
        _ensure_supervised(ctx, team_role)

        target_date = _parse_date_param(
            request.query_params.get("date"), default=ctx.today,
        )
        if target_date > ctx.today:
            msg = "Future dates are not selectable."
            raise ValidationError(msg)

        memberships = list(team_memberships(ctx.membership, team_role, today=target_date))
        template = _team_template_for_role(ctx.organization, ctx.program, team_role)
        if template is None:
            period_start, period_end = target_date, target_date
        else:
            period_start, period_end = resolve_period(
                template, anchor=target_date, program=ctx.program,
            )

        # Pull current-period reflections for the team in one query,
        # then map back per member.
        reflections_qs = Reflection.all_objects.none()
        person_ids = [m.person_id for m in memberships if m.person_id]
        if template is not None and person_ids:
            reflections_qs = Reflection.all_objects.filter(
                template=template,
                subject_id__in=person_ids,
                period_start=period_start,
                period_end=period_end,
                is_complete=True,
            ).select_related("author", "template")
        visible_reflections = list(
            reflections_visible_for_user(request.user, reflections_qs)
            if template is not None else [],
        )
        latest_by_subject: dict[int, Reflection] = {}
        for r in visible_reflections:
            existing = latest_by_subject.get(r.subject_id)
            if existing is None or r.submitted_at > existing.submitted_at:
                latest_by_subject[r.subject_id] = r

        # Per-row attention-marker counts for current period.
        marker_counts: dict[int, int] = {}
        if visible_reflections:
            from collections import Counter
            rows = ReflectionAttentionMarker.objects.filter(
                reflection_id__in=[r.id for r in visible_reflections],
            ).values_list("reflection_id", flat=True)
            marker_counts = Counter(rows)

        # Co-supervisors of THIS team — used in the header.
        supervision = (
            Supervision.objects.active(today=target_date)
            .for_supervisor(ctx.membership)
            .filter(target_type=Supervision.TargetType.ROLE_IN_PROGRAM, target_role=team_role)
            .first()
        )
        co_supervisors = []
        if supervision:
            co_supervisors = list(
                Supervision.objects.co_supervisors(supervision, today=target_date)
                .select_related("supervisor_membership__person"),
            )

        members_payload = _build_member_rows(
            memberships=memberships,
            latest_by_subject=latest_by_subject,
            marker_counts=marker_counts,
        )
        submission_status = _summarize_status(members_payload)
        flagged = _build_flagged_section(
            memberships=memberships,
            latest_by_subject=latest_by_subject,
            template=template,
            marker_counts=marker_counts,
        )

        return Response({
            "header": {
                "team_role": team_role,
                "team_role_label": dict(Membership.ROLES).get(
                    team_role, team_role.replace("_", " ").title(),
                ),
                "program": {
                    "id": ctx.program.id,
                    "name": ctx.program.name,
                },
                "member_count": len(memberships),
                "supervisors": _supervisors_payload(ctx, supervision, co_supervisors),
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat(),
                    "cadence": template.cadence if template else None,
                },
                "date": target_date.isoformat(),
            },
            "submission_status": submission_status,
            "flagged": flagged,
            "members": members_payload,
        })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_supervised(ctx, team_role: str) -> None:
    """Raise 403 / 404 if the viewer doesn't supervise ``team_role``."""
    qs = (
        Supervision.objects.active(today=ctx.today)
        .for_supervisor(ctx.membership)
        .filter(
            target_type=Supervision.TargetType.ROLE_IN_PROGRAM,
            target_role=team_role,
        )
    )
    if not qs.exists():
        if team_role not in dict(Membership.ROLES):
            msg = f"Unknown team role: {team_role!r}."
            raise NotFound(msg)
        msg = "You do not supervise this team."
        raise PermissionDenied(msg)


def _parse_date_param(raw: str | None, *, default: date) -> date:
    if not raw:
        return default
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid 'date' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


def _supervisors_payload(ctx, supervision, co_supervisors) -> list[dict]:
    """LT viewer + co-supervisors as compact name dicts."""
    out: list[dict] = [{
        "membership_id": ctx.membership.id,
        "person_name": person_display_name(ctx.person),
        "is_viewer": True,
    }]
    for s in co_supervisors:
        member = s.supervisor_membership
        if member is None or member.person is None:
            continue
        out.append({
            "membership_id": member.id,
            "person_name": person_display_name(member.person),
            "is_viewer": False,
        })
    return out


def _build_member_rows(
    *, memberships, latest_by_subject: dict[int, Reflection],
    marker_counts: dict[int, int],
) -> list[dict]:
    """One row per active team member with status, preview, marker count."""
    rows: list[dict] = []
    for m in memberships:
        person = m.person
        r = latest_by_subject.get(m.person_id)
        rows.append({
            "membership_id": m.id,
            "person_id": person.id if person else None,
            "person_name": person_display_name(person) if person else "",
            "language_preference": (person.preferred_language if person else "en"),
            "status": _row_status(r),
            "reflection_id": r.id if r else None,
            "submitted_at": r.submitted_at.isoformat() if r and r.submitted_at else None,
            "language_of_authorship": r.language if r else None,
            "preview": _preview_from_reflection(r),
            "attention_marker_count": marker_counts.get(r.id, 0) if r else 0,
        })
    rows.sort(key=lambda row: (row["status"] != "not_submitted",
                               row["person_name"].casefold()))
    return rows


def _row_status(reflection: Reflection | None) -> str:
    if reflection is None:
        return "not_submitted"
    answers = reflection.answers or {}
    if answers.get("day_off"):
        return "day_off"
    return "submitted"


def _preview_from_reflection(r: Reflection | None) -> str:
    if r is None or not r.answers:
        return ""
    for value in r.answers.values():
        if isinstance(value, str) and value.strip():
            text = value.strip()
            return text if len(text) <= 120 else text[:119] + "\u2026"
    return ""


def _summarize_status(rows: list[dict]) -> dict:
    submitted = sum(1 for r in rows if r["status"] == "submitted")
    day_off = sum(1 for r in rows if r["status"] == "day_off")
    not_submitted = sum(1 for r in rows if r["status"] == "not_submitted")
    return {
        "submitted": submitted,
        "day_off": day_off,
        "not_submitted": not_submitted,
        "total": len(rows),
    }


def _build_flagged_section(
    *, memberships, latest_by_subject, template, marker_counts,
) -> list[dict]:
    """Reflections with low ratings OR attention markers (current period)."""
    if not latest_by_subject:
        return []
    flagged: list[dict] = []
    person_by_id = {m.person_id: m.person for m in memberships if m.person_id}

    # Scale-min check for concerning ratings.
    scale_mins: dict[str, int] = {}
    if template is not None:
        from bunk_logs.core.reflection_scores import iter_scored_fields
        for field, label, _ in iter_scored_fields(template):
            scale = field.get("scale")
            if isinstance(scale, list) and scale:
                try:
                    scale_mins[label] = int(scale[0])
                except (TypeError, ValueError):
                    continue
        schema_fields = (template.schema or {}).get("fields") or []
        field_by_key = {
            f["key"]: f for f in schema_fields
            if isinstance(f, dict) and isinstance(f.get("key"), str)
        }
    else:
        field_by_key = {}

    from bunk_logs.core.reflection_scores import resolve_rating_cells

    for subject_id, r in latest_by_subject.items():
        reasons: list[str] = []
        if marker_counts.get(r.id):
            reasons.append("needs_attention")
        for label, min_val in scale_mins.items():
            field_key = label.split("__", 1)[0]
            field = field_by_key.get(field_key)
            if field is None:
                continue
            cells = resolve_rating_cells(field, r.answers or {})
            value = cells.get(label)
            if value is not None and value <= min_val:
                reasons.append("low_rating")
                break
        if not reasons:
            continue
        person = person_by_id.get(subject_id)
        flagged.append({
            "reflection_id": r.id,
            "person_name": person_display_name(person) if person else "",
            "reasons": reasons,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "language_of_authorship": r.language,
            "preview": _preview_from_reflection(r),
        })
    flagged.sort(key=lambda row: row["submitted_at"] or "", reverse=True)
    return flagged

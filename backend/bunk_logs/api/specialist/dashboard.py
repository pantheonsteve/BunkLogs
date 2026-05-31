"""``GET /api/v1/specialist/dashboard/`` — Story 24.

Exactly three top-level sections (criterion 3):
  1. ``write_camper_note`` — entry point to the camper picker / note form.
  2. ``self_reflection`` — state card for the specialist's daily self-reflection.
  3. ``recent_notes`` — chronological top-10 observations the specialist authored.

Sort: ``recent_notes`` newest-first. ``my_reflection`` state follows
the "missing / complete / day_off / no_template" pattern from other flows.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import is_day_off_answer
from bunk_logs.api.counselor.common import latest_self_reflection
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Flag
from bunk_logs.notes.models import Observation

from .common import specialist_label
from .common import specialist_self_template
from .common import viewer_or_403

RECENT_NOTES_LIMIT = 10
EDIT_WINDOW = timedelta(hours=24)
NOTE_PREVIEW_MAX_LEN = 120


class SpecialistDashboardView(APIView):
    """Minimal Specialist dashboard — Story 24."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        today = ctx.today

        template = specialist_self_template(org, ctx.program)
        self_state = "missing"
        self_reflection_id: int | None = None
        editable = False
        if template is None:
            self_state = "no_template"
        else:
            existing = latest_self_reflection(viewer, template, today, today)
            if existing is not None:
                self_state = "day_off" if is_day_off_answer(existing) else "complete"
                self_reflection_id = existing.id
                editable = True

        recent_obs_qs = (
            Observation.objects.filter(
                organization=org,
                program=ctx.program,
                author=viewer,
            )
            .prefetch_related("subject_links__subject")
            .order_by("-created_at")[:RECENT_NOTES_LIMIT]
        )
        recent_obs_list = list(recent_obs_qs)
        obs_ids = [o.id for o in recent_obs_list]

        flagged_obs_ids = set(
            Flag.all_objects.filter(
                trigger_content_type="specialist_note",
                trigger_content_id__in=[str(oid) for oid in obs_ids],
            ).values_list("trigger_content_id", flat=True),
        )

        subject_ids: set[int] = set()
        for obs in recent_obs_list:
            for link in obs.subject_links.all():
                if link.subject_id:
                    subject_ids.add(link.subject_id)
        bunk_names = _bunk_names_for_subjects(subject_ids)

        now = timezone.now()
        payload = {
            "today": today.isoformat(),
            "header": {
                "name": _display_name(viewer),
                "role_label": specialist_label(ctx.membership),
                "program_name": ctx.program.name,
            },
            "write_camper_note": {
                "url": "/specialist/observations/new",
            },
            "self_reflection": {
                "state": self_state,
                "reflection_id": self_reflection_id,
                "template_id": template.id if template else None,
                "editable": editable,
            },
            "recent_notes": [
                _observation_row(o, bunk_names, flagged_obs_ids, now)
                for o in recent_obs_list
            ],
        }
        return Response(payload)


def _display_name(person) -> str:
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first} {last}".strip() if (first or last) else ""


def _bunk_names_for_subjects(subject_ids: set[int]) -> dict[int, str]:
    """Return {person_id: bunk_name} for the given subject IDs."""
    if not subject_ids:
        return {}
    rows = (
        AssignmentGroupMembership.objects.filter(
            person_id__in=subject_ids,
            role_in_group="subject",
            is_active=True,
            group__group_type="bunk",
            group__is_active=True,
        )
        .select_related("group")
        .values("person_id", "group__name")
    )
    out: dict[int, str] = {}
    for row in rows:
        out.setdefault(row["person_id"], row["group__name"] or "")
    return out


def _primary_subject(obs: Observation):
    link = obs.subject_links.first()
    return link.subject if link else None


def _observation_row(
    obs: Observation,
    bunk_names: dict[int, str],
    flagged_obs_ids: set[str],
    now,
) -> dict:
    subject = _primary_subject(obs)
    subject_id = subject.id if subject else None
    first = (
        (subject.preferred_name or subject.first_name or "").strip()
        if subject else ""
    )
    last_initial = ((subject.last_name or "").strip()[:1] if subject else "")
    subject_name = (
        f"{first} {last_initial}." if (first and last_initial) else (first or last_initial or "")
    )
    body = obs.body or ""
    preview = body if len(body) <= NOTE_PREVIEW_MAX_LEN else body[:NOTE_PREVIEW_MAX_LEN - 1] + "…"
    return {
        "id": obs.id,
        "subject_id": subject_id,
        "subject_name": subject_name,
        "bunk_name": bunk_names.get(subject_id, "") if subject_id else "",
        "category": obs.context or "",
        "body_preview": preview,
        "is_sensitive": obs.sensitivity != Observation.Sensitivity.NORMAL,
        "flag_raised": str(obs.id) in flagged_obs_ids,
        "created_at": obs.created_at.isoformat(),
        "is_within_edit_window": (now - obs.created_at) <= EDIT_WINDOW,
    }

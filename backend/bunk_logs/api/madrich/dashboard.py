"""``GET /api/v1/madrich/dashboard/`` — Story 61.

Weekly-reflection-focused dashboard scoped to the active TBE
``religious_school`` Program. Three sections per Story 61 criterion 3:

* ``header`` — name, role label, grade level (8-12), program name.
* ``my_reflection`` — current-week card per criterion 5 with states
  ``missing`` (not yet started) / ``complete`` (submitted for this week).
  Daily incompleteness states are intentionally NOT modelled per
  criterion 5.iii — weekly cadence frames a missing submission as a
  gap, not a "draft" or "day off".
* ``history_entry`` — shortcut URL to the reflection history view.

Operational signals (rosters, faculty submissions, other Madrichim,
camp-side data) are intentionally omitted per criterion 4.
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Reflection

from .common import current_week_period
from .common import madrich_template
from .common import viewer_or_403


class MadrichDashboardView(APIView):
    """Minimal Madrich weekly dashboard — Story 61."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        today = ctx.today

        template = madrich_template(org, ctx.program)
        period_start, period_end = current_week_period(
            ctx.program, org, today=today,
        )

        self_state = "missing"
        self_reflection_id: int | None = None
        editable = False

        if template is None:
            self_state = "no_template"
        else:
            existing = (
                Reflection.all_objects.filter(
                    author=viewer,
                    subject=viewer,
                    template=template,
                    period_start=period_start,
                    period_end=period_end,
                    is_complete=True,
                )
                .order_by("-submitted_at")
                .first()
            )
            if existing is not None:
                self_state = "complete"
                self_reflection_id = existing.id
                editable = True

        return Response({
            "today": today.isoformat(),
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "cadence": "weekly",
            },
            "header": {
                "name": _display_name(viewer),
                "role_label": "Madrich",
                "grade_level": ctx.membership.grade_level,
                "program_name": ctx.program.name,
                "preferred_language": viewer.preferred_language or "en",
            },
            "my_reflection": {
                "state": self_state,
                "reflection_id": self_reflection_id,
                "template_id": template.id if template else None,
                "editable": editable,
            },
            "history_entry": {
                "url": "/madrich/history",
            },
        })


def _display_name(person) -> str:
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first} {last}".strip() if (first or last) else ""

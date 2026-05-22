"""``GET /api/v1/kitchen-staff/dashboard/`` — Story 37.

Three top-level sections (criterion 3):
  1. ``header`` — name, role_label, program_name, preferred_language.
  2. ``my_reflection`` — today's state card + edit affordance (Story 37 criterion 3).
  3. ``history_entry`` — shortcut URL to the reflection history view.
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import is_day_off_answer
from bunk_logs.api.counselor.common import latest_self_reflection

from .common import kitchen_staff_template
from .common import viewer_or_403


class KitchenStaffDashboardView(APIView):
    """Minimal Kitchen Staff dashboard — Story 37."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        today = ctx.today

        template = kitchen_staff_template(org, ctx.program)
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

        return Response({
            "today": today.isoformat(),
            "header": {
                "name": _display_name(viewer),
                "role_label": "Kitchen Staff",
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
                "url": "/kitchen-staff/history",
            },
        })


def _display_name(person) -> str:
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first} {last}".strip() if (first or last) else ""

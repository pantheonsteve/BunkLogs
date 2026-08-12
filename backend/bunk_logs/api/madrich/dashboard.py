"""``GET /api/v1/madrich/dashboard/`` — Stories 61 and 63.

Reflection-focused dashboard scoped to the active TBE
``religious_school`` Program. Three sections per Story 61 criterion 3:

* ``header`` — name, role label, grade level (8-12), program name.
* ``my_reflections`` — one card per template the Madrich currently owes
  (Story 63), each with its own cadence, period, and ``missing`` /
  ``complete`` state. Daily incompleteness states are intentionally NOT
  modelled per Story 61 criterion 5.iii — a missing submission is a gap,
  not a "draft" or "day off". An empty list is the "nothing assigned yet"
  state the client renders as Director-will-set-this-up copy.
* ``history_entry`` — shortcut URL to the reflection history view.
* ``availability`` — Step 4_7 summary card (unset count, next session,
  calendar link). The dedicated ``/madrich/availability/`` endpoint
  (``availability.py``) remains the source of truth for the full calendar;
  this is a lightweight card only.

Operational signals about *other* people (rosters, faculty submissions,
peer Madrichim, camp-side data) are intentionally omitted per Story 61
criterion 4 -- the viewer's own availability commitment is not one of
those, since Step 4_7 is explicitly a self-service staffing signal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Reflection

from .availability import availability_summary
from .common import assigned_reflections
from .common import current_week_period
from .common import viewer_or_403

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Person

    from .common import AssignedReflection


def _submitted_by_period(
    viewer: Person, entries: list[AssignedReflection],
) -> dict[tuple[int, date], Reflection]:
    """Map ``(template_id, period_start)`` to the viewer's completed row.

    One query for every card rather than one per card, since a Madrich
    with several concurrent assignments would otherwise fan out.
    """
    if not entries:
        return {}
    lookup = Q()
    for entry in entries:
        lookup |= Q(
            template_id=entry.template.id,
            period_start=entry.period_start,
            period_end=entry.period_end,
        )
    rows = Reflection.all_objects.filter(
        lookup, author=viewer, subject=viewer, is_complete=True,
    ).order_by("-submitted_at")
    submitted: dict[tuple[int, date], Reflection] = {}
    for row in rows:
        submitted.setdefault((row.template_id, row.period_start), row)
    return submitted


class MadrichDashboardView(APIView):
    """Madrich reflection dashboard — Stories 61 and 63."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        today = ctx.today

        entries = assigned_reflections(ctx)
        submitted = _submitted_by_period(viewer, entries)
        period_start, period_end = current_week_period(
            ctx.program, org, today=today,
        )

        cards = []
        for entry in entries:
            existing = submitted.get((entry.template.id, entry.period_start))
            cards.append({
                "template_id": entry.template.id,
                "template_name": entry.template.name,
                "cadence": entry.cadence,
                "recurring": entry.is_recurring,
                "period": {
                    "start": entry.period_start.isoformat(),
                    "end": entry.period_end.isoformat(),
                },
                "state": "complete" if existing else "missing",
                "reflection_id": existing.id if existing else None,
                # The period bounds already scope the lookup, so anything
                # we found is by definition still inside its edit window
                # (Story 62 c5).
                "editable": existing is not None,
            })

        availability = availability_summary(ctx)
        # AC5.3: lightweight Wednesday nudge -- the reflection Wednesday
        # reminder email is unaffected (MA2); this is client-rendered only.
        availability_nudge = (
            today.weekday() == 2 and availability["upcoming_unset_count"] > 0
        )

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
            "my_reflections": cards,
            "history_entry": {
                "url": "/madrich/history",
            },
            "availability": availability,
            "availability_nudge": availability_nudge,
        })


def _display_name(person) -> str:
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first} {last}".strip() if (first or last) else ""

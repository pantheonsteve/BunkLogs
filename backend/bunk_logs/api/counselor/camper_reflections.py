"""``GET /api/v1/counselor/camper-reflections/?date=YYYY-MM-DD`` — Story 3.

Returns the bunk roster(s) for the viewer with each camper's submitted /
not-submitted status for the requested date. Off-camp campers (per
``CamperDayState``) appear in a dedicated sub-section and don't count
toward "expected".

The view of past dates is read-only (Story 6 criterion 4 — extended to
camper reflections per Story 4): the ``editable`` flag on the response
and on each row tells the client whether to render the Edit affordance.
"""

from __future__ import annotations

from datetime import date as date_type

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Membership

from .common import bunk_camper_persons
from .common import camper_reflection_template
from .common import latest_camper_reflection_per_subject
from .common import off_camp_camper_ids
from .common import person_display_name
from .common import viewer_bunk_groups
from .common import viewer_or_403


def _parse_iso_date(value: str | None, default: date_type) -> date_type | None:
    if not value:
        return default
    try:
        return date_type.fromisoformat(value)
    except (TypeError, ValueError):
        return None


class CamperReflectionListView(APIView):
    """Bunk roster with per-camper submission state for a date."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        today = ctx.today

        target = _parse_iso_date(request.query_params.get("date"), today)
        if target is None:
            return Response(
                {"detail": "Invalid 'date' query parameter; expected YYYY-MM-DD."},
                status=400,
            )

        primary_membership = (
            Membership.objects.filter(person=viewer, is_active=True)
            .select_related("program")
            .order_by("-created_at")
            .first()
        )
        if primary_membership is None or primary_membership.program is None:
            return Response({
                "date": target.isoformat(),
                "editable": target == today,
                "bunks": [],
            })
        program = primary_membership.program

        bunks = viewer_bunk_groups(viewer)
        if not bunks:
            return Response({
                "date": target.isoformat(),
                "editable": target == today,
                "bunks": [],
            })

        template = camper_reflection_template(org, program)
        roster_by_bunk = bunk_camper_persons(bunks)
        all_camper_ids: set[int] = set()
        for campers in roster_by_bunk.values():
            all_camper_ids.update(p.id for p in campers)

        off_camp_ids = off_camp_camper_ids(org, target, camper_ids=all_camper_ids)
        reflections_by_subject = (
            latest_camper_reflection_per_subject(template, bunks, target, target)
            if template is not None
            else {}
        )

        date_is_today = target == today
        bunks_payload = []
        for bunk in bunks:
            campers = roster_by_bunk.get(bunk.id, [])
            row_campers = []
            off_camp_rows = []
            covered = 0
            for camper in campers:
                base = {
                    "id": camper.id,
                    "name": person_display_name(camper),
                    "preferred_name": camper.preferred_name or camper.first_name,
                    "first_name": camper.first_name,
                    "last_initial": (camper.last_name or "")[:1],
                }
                if camper.id in off_camp_ids:
                    # Off-camp rows are surfaced separately and don't get
                    # status / submitter / editable fields — they aren't
                    # actionable in this UI.
                    off_camp_rows.append(base)
                    continue

                reflection = reflections_by_subject.get(camper.id)
                submitted = reflection is not None
                if submitted:
                    covered += 1
                    author_person = reflection.author
                    is_self = author_person == viewer if author_person else False
                    submitter = {
                        "is_self": is_self,
                        # Per Story 3 criterion 3 — show submitter name only when
                        # it isn't the viewer themself.
                        "name": person_display_name(author_person) if not is_self else None,
                    }
                else:
                    submitter = None

                row = {
                    **base,
                    "submitted": submitted,
                    "reflection_id": reflection.id if reflection else None,
                    "submitted_at": (
                        reflection.submitted_at.isoformat()
                        if reflection and reflection.submitted_at
                        else None
                    ),
                    "submitter": submitter,
                    "editable": submitted and date_is_today,
                }
                row_campers.append(row)

            bunks_payload.append({
                "id": bunk.id,
                "slug": bunk.slug,
                "name": bunk.name,
                "covered": covered,
                "total": len(row_campers),
                "campers": row_campers,
                "off_camp": off_camp_rows,
            })

        return Response({
            "date": target.isoformat(),
            "editable": date_is_today,
            "template": (
                {
                    "id": template.id,
                    "slug": template.slug,
                    "name": template.name,
                    "version": template.version,
                }
                if template is not None
                else None
            ),
            "bunks": bunks_payload,
        })

"""``GET /api/v1/unit-head/dashboard/`` — Story 10.

Returns the supervised bunk list with completion + attention badges
and the UH's own "My reflection" section state.

Sort order (Story 10 criterion 7):
  badged bunks first, in ``ATTENTION_BADGE_ORDER`` priority, then
  unbadged bunks alphabetical.

Caching: a 30s per-(org, viewer, day) entry mirrors the counselor
dashboard contract — writes to UH/counselor reflections bump the
same generation key the counselor flow uses so cross-role
freshness stays consistent.
"""

from __future__ import annotations

from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import camper_reflection_template
from bunk_logs.api.counselor.common import is_day_off_answer
from bunk_logs.api.counselor.common import latest_self_reflection

from .common import ATTENTION_BADGE_ORDER
from .common import build_score_grid  # noqa: F401 — re-exported for downstream tests
from .common import bunk_camper_ids
from .common import bunk_concerns_referencing
from .common import compute_attention_badges
from .common import counselor_self_reflection_counts
from .common import expected_by_passed
from .common import help_requested_camper_ids_from
from .common import off_camp_camper_ids
from .common import supervised_bunks
from .common import unit_head_self_period
from .common import unit_head_self_template
from .common import viewer_or_403

DASHBOARD_CACHE_TTL_SECONDS = 30
LOW_COMPLETION_THRESHOLD = 0.5  # Story 10 criterion 6.iv


def _cache_key(*, viewer_id: int, organization_id: int, today) -> str:
    return f"unit_head_dashboard:{organization_id}:{viewer_id}:{today.isoformat()}"


class UnitHeadDashboardView(APIView):
    """Supervised bunks + self-reflection state."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        program = ctx.program
        today = ctx.today

        bypass = (request.query_params.get("nocache") or "").lower() in {"1", "true"}
        cache_key = _cache_key(viewer_id=viewer.id, organization_id=org.id, today=today)
        if not bypass:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        bunks = supervised_bunks(ctx.membership, today=today)
        camper_template = camper_reflection_template(org, program)
        uh_template = unit_head_self_template(org, program)

        # Bunk-concerns surface (Story 11 criterion 1.iv): which bunk IDs
        # have AT LEAST one reflection referencing them today? We need this
        # union to set the per-bunk badge.
        bc_map = bunk_concerns_referencing(
            organization=org, program=program, target_date=today,
        )
        bc_bunk_ids = set(bc_map.keys())

        bunks_payload: list[dict] = []
        expected_passed = expected_by_passed(org, today)

        for bunk in bunks:
            camper_ids = bunk_camper_ids(bunk)
            off_camp = off_camp_camper_ids(org, today, camper_ids)
            submitted_ids: set[int] = set()
            help_ids: set[int] = set()
            if camper_template and camper_ids:
                from bunk_logs.core.models import Reflection
                reflections = {
                    r.subject_id: r
                    for r in Reflection.all_objects.filter(
                        template=camper_template,
                        assignment_group=bunk,
                        period_start=today,
                        period_end=today,
                        is_complete=True,
                    ).select_related("template")
                }
                submitted_ids = set(reflections.keys())
                help_ids = help_requested_camper_ids_from(reflections)

            badges = compute_attention_badges(
                bunk=bunk,
                bunk_camper_ids_list=camper_ids,
                off_camp_ids=off_camp,
                submitted_camper_ids=submitted_ids,
                help_requested_camper_ids=help_ids,
                bunk_concerns_referenced_bunk_ids=bc_bunk_ids,
                low_completion_threshold=LOW_COMPLETION_THRESHOLD,
                expected_by_passed=expected_passed,
            )

            on_camp_total = len([c for c in camper_ids if c not in off_camp])
            submitted_on_camp = len([
                c for c in camper_ids if c in submitted_ids and c not in off_camp
            ])

            bunks_payload.append({
                "id": bunk.id,
                "name": bunk.name,
                "slug": bunk.slug,
                "unit_name": (bunk.parent.name if bunk.parent_id else None),
                "counselor_names": _counselor_names(bunk),
                "completion": {
                    "submitted": submitted_on_camp,
                    "expected": on_camp_total,
                    "off_camp": len(off_camp),
                },
                "counselor_self_reflections": counselor_self_reflection_counts(
                    bunk, today,
                ),
                "badges": badges,
            })

        bunks_payload.sort(key=_bunk_sort_key)

        # My self-reflection section. The cadence is whatever the admin
        # assigned (daily / weekly / biweekly / monthly); the period bounds
        # come from unit_head_self_period so non-daily templates resolve the
        # current window rather than today-only.
        self_state = "missing"
        self_reflection_id: int | None = None
        editable = False
        self_period_start = None
        self_period_end = None
        self_cadence = uh_template.cadence if uh_template else None
        if uh_template is not None:
            self_period_start, self_period_end = unit_head_self_period(
                uh_template, org, program, today=today,
            )
            existing = latest_self_reflection(
                viewer, uh_template, self_period_start, self_period_end,
            )
            if existing is not None:
                self_state = "day_off" if is_day_off_answer(existing) else "complete"
                self_reflection_id = existing.id
                editable = True  # within the current period by definition

        payload = {
            "today": today.isoformat(),
            "bunks": bunks_payload,
            "self_reflection": {
                "state": self_state,
                "reflection_id": self_reflection_id,
                "template_id": uh_template.id if uh_template else None,
                "editable": editable,
                "cadence": self_cadence,
                "period_start": (
                    self_period_start.isoformat() if self_period_start else None
                ),
                "period_end": (
                    self_period_end.isoformat() if self_period_end else None
                ),
            },
        }
        cache.set(cache_key, payload, DASHBOARD_CACHE_TTL_SECONDS)
        return Response(payload)


def _counselor_names(bunk) -> list[str]:
    """Active counselor display names for the bunk."""
    from bunk_logs.api.counselor.common import person_display_name
    from bunk_logs.core.models import AssignmentGroupMembership

    rows = (
        AssignmentGroupMembership.objects.filter(
            group=bunk, role_in_group="author", is_active=True,
        )
        .select_related("person")
        .order_by("person__last_name", "person__first_name")
    )
    return [person_display_name(agm.person) for agm in rows if agm.person]


def _bunk_sort_key(bunk_row: dict) -> tuple:
    """Story 10 criterion 7 sort order.

    Badged bunks first, ordered by the priority of their *highest*
    badge in ATTENTION_BADGE_ORDER. Within the same band, alphabetical
    by bunk name (case-insensitive). Unbadged bunks come last, also
    alphabetical.
    """
    badges = bunk_row.get("badges") or []
    name_key = (bunk_row.get("name") or "").casefold()
    if not badges:
        return (1, 99, name_key)
    priority = min(
        (ATTENTION_BADGE_ORDER.index(b) for b in badges if b in ATTENTION_BADGE_ORDER),
        default=99,
    )
    return (0, priority, name_key)

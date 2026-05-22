"""``GET /api/v1/camper-care/dashboard/`` — Story 18.

Returns the caseload tree (Unit -> Bunks), a caseload-wide reflection
completion summary (Story 19), the unresolved flag count, the open
order count, and the viewer's "My reflection" state for the
Camper-Care self-reflection template.

Caching mirrors the unit-head dashboard: 30s per (org, viewer, day)
entry. Writes elsewhere bust the same generation surface so cross-role
freshness stays bounded.
"""

from __future__ import annotations

from django.core.cache import cache
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import camper_reflection_template
from bunk_logs.api.counselor.common import is_day_off_answer
from bunk_logs.api.counselor.common import latest_self_reflection
from bunk_logs.api.unit_head.common import bunk_concerns_referencing
from bunk_logs.api.unit_head.common import compute_attention_badges
from bunk_logs.api.unit_head.common import expected_by_passed
from bunk_logs.api.unit_head.common import help_requested_camper_ids_from
from bunk_logs.api.unit_head.common import off_camp_camper_ids
from bunk_logs.core.models import Flag
from bunk_logs.core.models import Order

from .common import bunk_camper_ids
from .common import camper_care_self_template
from .common import caseload_bunks_with_unit
from .common import viewer_or_403

DASHBOARD_CACHE_TTL_SECONDS = 30
LOW_COMPLETION_THRESHOLD = 0.5


def _cache_key(*, viewer_id: int, organization_id: int, today) -> str:
    return f"camper_care_dashboard:{organization_id}:{viewer_id}:{today.isoformat()}"


class CamperCareDashboardView(APIView):
    """Caseload tree + unresolved flag count + open order count + self section."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        target_date = _resolve_target_date(
            request.query_params.get("date"), default=ctx.today,
        )
        if target_date > ctx.today:
            msg = "Future dates are not selectable."
            raise ValidationError(msg)

        bypass = (request.query_params.get("nocache") or "").lower() in {"1", "true"}
        cache_key = _cache_key(
            viewer_id=ctx.person.id, organization_id=ctx.organization.id,
            today=target_date,
        )
        if not bypass and target_date == ctx.today:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        units_payload = _build_caseload_tree(ctx, target_date=target_date)

        flag_count = Flag.objects.filter(
            program=ctx.program,
            flagged_for_role="camper_care",
            status__in=(Flag.Status.ACTIVE, Flag.Status.FOLLOWED_UP),
        ).count()

        order_count = Order.objects.filter(
            program=ctx.program,
            status__in=(Order.Status.NEW, Order.Status.IN_PROGRESS),
        ).count()

        self_state, self_id, self_template_id, editable = _self_reflection_state(ctx)

        # Caseload-wide rollup (Story 19 criterion 1).
        submitted = sum(b["completion"]["submitted"] for u in units_payload for b in u["bunks"])
        expected = sum(b["completion"]["expected"] for u in units_payload for b in u["bunks"])

        payload = {
            "date": target_date.isoformat(),
            "today": ctx.today.isoformat(),
            "units": units_payload,
            "summary": {
                "submitted": submitted,
                "expected": expected,
                "flag_count": flag_count,
                "order_count": order_count,
            },
            "self_reflection": {
                "state": self_state,
                "reflection_id": self_id,
                "template_id": self_template_id,
                "editable": editable,
            },
        }
        if target_date == ctx.today:
            cache.set(cache_key, payload, DASHBOARD_CACHE_TTL_SECONDS)
        return Response(payload)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_target_date(raw, *, default):
    if not raw:
        return default
    parsed = parse_date(raw)
    if parsed is None:
        msg = "Invalid 'date' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


def _self_reflection_state(ctx):
    template = camper_care_self_template(ctx.organization, ctx.program)
    if template is None:
        return "missing", None, None, False
    existing = latest_self_reflection(
        ctx.person, template, ctx.today, ctx.today,
    )
    if existing is None:
        return "missing", None, template.id, False
    state = "day_off" if is_day_off_answer(existing) else "complete"
    return state, existing.id, template.id, True


def _build_caseload_tree(ctx, *, target_date) -> list[dict]:
    """Caseload as ``[{unit:..., bunks:[...] }, ...]`` for Story 18.

    Unit ordering: alphabetical by unit name; the "Unassigned" bucket
    (bunks with no parent unit) goes last so the named units stay
    visually anchored at the top.
    """
    from bunk_logs.core.models import AssignmentGroup

    by_unit = caseload_bunks_with_unit(ctx.membership, today=target_date)
    if not by_unit:
        return []

    camper_template = camper_reflection_template(ctx.organization, ctx.program)
    expected_passed = expected_by_passed(ctx.organization, target_date)
    bc_map = bunk_concerns_referencing(
        organization=ctx.organization, program=ctx.program, target_date=target_date,
    )
    bc_bunk_ids = set(bc_map.keys())

    # Resolve unit Person/Group rows once for naming.
    unit_ids = [uid for uid in by_unit if uid is not None]
    units = {
        u.id: u for u in AssignmentGroup.all_objects.filter(id__in=unit_ids)
    } if unit_ids else {}

    # Camper-Care attention: per-camper unresolved flags + open orders.
    bunk_to_camper_ids: dict[int, list[int]] = {}
    all_camper_ids: set[int] = set()
    for bunks in by_unit.values():
        for bunk in bunks:
            ids = bunk_camper_ids(bunk)
            bunk_to_camper_ids[bunk.id] = ids
            all_camper_ids.update(ids)

    flagged_camper_ids = (
        set(
            Flag.objects.filter(
                program=ctx.program,
                subject_camper_id__in=all_camper_ids,
                flagged_for_role="camper_care",
                status__in=(Flag.Status.ACTIVE, Flag.Status.FOLLOWED_UP),
            ).values_list("subject_camper_id", flat=True),
        ) if all_camper_ids else set()
    )
    ordered_camper_ids = (
        set(
            Order.objects.filter(
                program=ctx.program,
                subject_id__in=all_camper_ids,
                status__in=(Order.Status.NEW, Order.Status.IN_PROGRESS),
            ).values_list("subject_id", flat=True),
        ) if all_camper_ids else set()
    )

    out: list[dict] = []
    sorted_unit_keys = sorted(by_unit.keys(), key=lambda uid: (
        1 if uid is None else 0, (units.get(uid).name if uid in units else "").casefold(),
    ))
    for unit_id in sorted_unit_keys:
        bunks = by_unit[unit_id]
        bunks_payload: list[dict] = []
        for bunk in bunks:
            camper_ids = bunk_to_camper_ids.get(bunk.id, [])
            off_camp = off_camp_camper_ids(ctx.organization, target_date, camper_ids)
            submitted_ids: set[int] = set()
            help_ids: set[int] = set()
            if camper_template and camper_ids:
                from bunk_logs.core.models import Reflection
                reflections = {
                    r.subject_id: r
                    for r in Reflection.all_objects.filter(
                        template=camper_template,
                        assignment_group=bunk,
                        period_start=target_date,
                        period_end=target_date,
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
            cc_flagged = any(cid in flagged_camper_ids for cid in camper_ids)
            cc_pending_order = any(cid in ordered_camper_ids for cid in camper_ids)
            if cc_flagged and "cc_flagged" not in badges:
                badges.insert(0, "cc_flagged")
            if cc_pending_order and "cc_pending_order" not in badges:
                badges.insert(0, "cc_pending_order")

            on_camp_total = len([c for c in camper_ids if c not in off_camp])
            submitted_on_camp = len([
                c for c in camper_ids if c in submitted_ids and c not in off_camp
            ])

            bunks_payload.append({
                "id": bunk.id,
                "name": bunk.name,
                "slug": bunk.slug,
                "counselor_names": _counselor_names(bunk),
                "completion": {
                    "submitted": submitted_on_camp,
                    "expected": on_camp_total,
                    "off_camp": len(off_camp),
                },
                "badges": badges,
                "camper_count": len(camper_ids),
            })

        # Sort: bunks with any badge first (alphabetical within band).
        bunks_payload.sort(key=lambda b: (
            0 if b["badges"] else 1, (b["name"] or "").casefold(),
        ))

        unit_name = units[unit_id].name if unit_id in units else "Unassigned"
        unit_payload = {
            "id": unit_id,
            "name": unit_name,
            "bunks": bunks_payload,
            "completion": {
                "submitted": sum(b["completion"]["submitted"] for b in bunks_payload),
                "expected": sum(b["completion"]["expected"] for b in bunks_payload),
            },
        }
        out.append(unit_payload)
    return out


def _counselor_names(bunk):
    """Active counselor display names for the bunk (shared with UH dashboard shape)."""
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

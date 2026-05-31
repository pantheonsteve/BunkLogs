"""``GET /api/v1/leadership-team/dashboard/`` — Story 45.

Returns per-team cards (one per ROLE_IN_PROGRAM supervision the LT
viewer holds), an entry to the Bunks-and-Units side (Story 49), the
LT's "My reflection" state for the current period, and a tiny
templates-and-assignments summary (Stories 51, 53 — full list lives on
its own page).

Caching mirrors the UH/CC dashboards: 30s per (org, viewer, day).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.cache import cache

if TYPE_CHECKING:
    from datetime import date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.counselor.common import camper_reflection_template
from bunk_logs.api.counselor.common import is_day_off_answer
from bunk_logs.api.counselor.common import latest_self_reflection
from bunk_logs.api.unit_head.common import expected_by_passed
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import Supervision
from bunk_logs.notes.models import Observation

from .common import leadership_team_self_template
from .common import resolve_period
from .common import supervised_role_supervisions
from .common import team_memberships
from .common import viewer_or_403

DASHBOARD_CACHE_TTL_SECONDS = 30
LOW_COMPLETION_THRESHOLD = 0.5  # Story 45 c5: <50% by configured time

ATTENTION_BADGE_ORDER: tuple[str, ...] = (
    "low_completion",
    "concerning_ratings",
    "sensitive_content",
)


def _cache_key(*, viewer_id: int, organization_id: int, today: date) -> str:
    return f"leadership_team_dashboard:{organization_id}:{viewer_id}:{today.isoformat()}"


class LeadershipTeamDashboardView(APIView):
    """Supervised teams + bunks-and-units entry + self-reflection state."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        today = ctx.today

        bypass = (request.query_params.get("nocache") or "").lower() in {"1", "true"}
        cache_key = _cache_key(viewer_id=viewer.id, organization_id=org.id, today=today)
        if not bypass:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        teams_payload = _build_team_cards(ctx)
        bunks_units = _build_bunks_units_summary(ctx)
        self_section = _build_self_section(ctx)
        templates_summary = _build_templates_summary(ctx)

        payload = {
            "today": today.isoformat(),
            "teams": teams_payload,
            "bunks_and_units": bunks_units,
            "self_reflection": self_section,
            "templates_and_assignments": templates_summary,
        }
        cache.set(cache_key, payload, DASHBOARD_CACHE_TTL_SECONDS)
        return Response(payload)


# ---------------------------------------------------------------------------
# Per-team cards (Story 45 c3-c6)
# ---------------------------------------------------------------------------


def _build_team_cards(ctx) -> list[dict]:
    """One card per ROLE_IN_PROGRAM supervision held by the LT viewer.

    Each card carries member counts, today's completion, co-supervisor
    names, and the attention badges in dashboard-sort order.
    """
    supervisions = supervised_role_supervisions(ctx.membership, today=ctx.today)
    if not supervisions:
        return []

    expected_passed = expected_by_passed(ctx.organization, ctx.today)
    cards: list[dict] = []
    for supervision in supervisions:
        role = supervision.target_role
        program = supervision.target_program
        memberships = team_memberships(ctx.membership, role, today=ctx.today)
        member_count = memberships.count()
        member_person_ids = list(memberships.values_list("person_id", flat=True))

        completion, concerning = _team_completion(
            organization=ctx.organization,
            program=program,
            target_role=role,
            person_ids=member_person_ids,
            today=ctx.today,
        )

        sensitive_count = _team_sensitive_notes_count(
            organization=ctx.organization,
            program=program,
            today=ctx.today,
            role=role,
            person_ids=member_person_ids,
        )

        badges = _compute_team_badges(
            completion=completion,
            concerning=concerning,
            sensitive_count=sensitive_count,
            expected_passed=expected_passed,
            low_completion_threshold=LOW_COMPLETION_THRESHOLD,
        )

        co_supervisors = list(
            Supervision.objects.co_supervisors(supervision, today=ctx.today)
            .select_related("supervisor_membership__person"),
        )

        cards.append({
            "team_role": role,
            "team_role_label": dict(_role_labels()).get(role, role.replace("_", " ").title()),
            "program_id": program.id if program else None,
            "program_name": program.name if program else None,
            "member_count": member_count,
            "completion": completion,
            "co_supervisors": [
                {
                    "membership_id": s.supervisor_membership_id,
                    "person_name": _person_brief(s.supervisor_membership.person),
                }
                for s in co_supervisors
                if s.supervisor_membership and s.supervisor_membership.person
            ],
            "badges": badges,
        })

    cards.sort(key=_team_card_sort_key)
    return cards


def _team_completion(
    *, organization, program, target_role: str, person_ids: list[int], today: date,
) -> tuple[dict, bool]:
    """Today's submission count vs expected for a team.

    Returns ``(completion_dict, has_concerning_rating)``. The concerning
    rating flag fires when any answer in any submission equals the
    template's lowest scale value (Story 45 c5 — LT4).
    """
    if not person_ids:
        return {"submitted": 0, "expected": 0}, False

    # Resolve the team's active self-reflection template for the given role.
    # Org-shadows-global resolver; cadence is whatever the template carries.
    template = _team_template_for_role(organization, program, target_role)
    if template is None:
        return {"submitted": 0, "expected": len(person_ids)}, False

    period_start, period_end = resolve_period(
        template, anchor=today, program=program,
    )

    reflections = list(
        Reflection.all_objects.filter(
            template=template,
            subject_id__in=person_ids,
            period_start=period_start,
            period_end=period_end,
            is_complete=True,
        ),
    )
    submitted_subject_ids = {r.subject_id for r in reflections}

    concerning = _has_concerning_rating(template, reflections)
    return (
        {"submitted": len(submitted_subject_ids), "expected": len(person_ids)},
        concerning,
    )


def _team_template_for_role(organization, program, target_role: str):
    """Active self-reflection template for ``target_role`` in this program."""
    from bunk_logs.api.counselor.common import _resolve_template
    from bunk_logs.core.models import ReflectionTemplate

    qs = ReflectionTemplate.all_objects.filter(
        role=target_role, subject_mode="self",
    )
    return _resolve_template(
        qs, organization=organization, program_type=program.program_type if program else None,
    )


def _has_concerning_rating(template, reflections) -> bool:
    """True iff any answer == ``min(scale)`` of any scored field in ``template``."""
    from bunk_logs.core.reflection_scores import iter_scored_fields
    from bunk_logs.core.reflection_scores import resolve_rating_cells

    if not reflections:
        return False
    scale_mins: dict[str, int] = {}
    for field, label, _scale_max in iter_scored_fields(template):
        scale = field.get("scale")
        if isinstance(scale, list) and scale:
            try:
                scale_mins[label] = int(scale[0])
            except (TypeError, ValueError):
                continue
    if not scale_mins:
        return False
    schema_fields = (template.schema or {}).get("fields") or []
    field_by_key = {
        f["key"]: f for f in schema_fields
        if isinstance(f, dict) and isinstance(f.get("key"), str)
    }
    for r in reflections:
        for label, min_val in scale_mins.items():
            field_key = label.split("__", 1)[0]
            field = field_by_key.get(field_key)
            if field is None:
                continue
            cells = resolve_rating_cells(field, r.answers or {})
            value = cells.get(label)
            if value is not None and value <= min_val:
                return True
    return False


def _team_sensitive_notes_count(
    *, organization, program, today: date, role: str, person_ids: list[int],
) -> int:
    """Sensitive Specialist / Camper-Care notes about team members today.

    LT3 visibility for sensitive content extends to LT supervisors only
    when the content is in their supervised scope. We use the union of
    the supervised team's person ids as the scope for this card.
    Counting sensitive notes about LT members themselves is unusual but
    not impossible; the count is most meaningful for teams of campers /
    counselors that LT supervises transitively. Today the scope is
    direct-team; further transitive expansion is deferred.
    """
    if not person_ids:
        return 0
    return (
        Observation.all_objects.filter(
            organization=organization,
            program=program,
            subject_links__subject_id__in=person_ids,
            sensitivity__in=[
                Observation.Sensitivity.SENSITIVE,
                Observation.Sensitivity.DOMAIN,
                Observation.Sensitivity.CONFIDENTIAL,
            ],
            created_at__date=today,
        )
        .distinct()
        .count()
    )


def _compute_team_badges(
    *, completion: dict, concerning: bool, sensitive_count: int,
    expected_passed: bool, low_completion_threshold: float,
) -> list[str]:
    """Compute attention badges in dashboard-sort order for one team card."""
    badges: list[str] = []
    expected = completion.get("expected") or 0
    submitted = completion.get("submitted") or 0
    if expected_passed and expected:
        ratio = submitted / expected
        if ratio < low_completion_threshold:
            badges.append("low_completion")
    if concerning:
        badges.append("concerning_ratings")
    if sensitive_count > 0:
        badges.append("sensitive_content")
    return badges


def _team_card_sort_key(card: dict) -> tuple:
    """Story 45 c6 sort order.

    Badged cards first, in ATTENTION_BADGE_ORDER priority of the
    HIGHEST badge. Within the same band, alphabetical by team role
    (case-insensitive). Unbadged cards come last, also alphabetical.
    """
    badges = card.get("badges") or []
    name_key = (card.get("team_role") or "").casefold()
    if not badges:
        return (1, 99, name_key)
    priority = min(
        (ATTENTION_BADGE_ORDER.index(b) for b in badges if b in ATTENTION_BADGE_ORDER),
        default=99,
    )
    return (0, priority, name_key)


# ---------------------------------------------------------------------------
# Bunks-and-units summary (Story 49 entry)
# ---------------------------------------------------------------------------


def _build_bunks_units_summary(ctx) -> dict:
    """Org-wide unit + bunk counts plus today's completion."""
    org = ctx.organization
    program = ctx.program
    today = ctx.today

    units = list(
        AssignmentGroup.objects.filter(
            program=program, group_type="unit", is_active=True,
        ).order_by("name"),
    )
    bunks = list(
        AssignmentGroup.objects.filter(
            program=program, group_type="bunk", is_active=True,
        ),
    )
    camper_template = camper_reflection_template(org, program)
    submitted = 0
    expected = 0
    if camper_template and bunks:
        # Expected = active subjects across all bunks (today's roster).
        from bunk_logs.core.models import AssignmentGroupMembership
        subject_ids = list(
            AssignmentGroupMembership.objects.filter(
                group__in=bunks, role_in_group="subject", is_active=True,
            ).values_list("person_id", flat=True),
        )
        expected = len(subject_ids)
        submitted = (
            Reflection.all_objects.filter(
                template=camper_template,
                assignment_group__in=bunks,
                subject_id__in=subject_ids,
                period_start=today,
                period_end=today,
                is_complete=True,
            ).values("subject_id").distinct().count()
        )
    return {
        "unit_count": len(units),
        "bunk_count": len(bunks),
        "completion": {"submitted": submitted, "expected": expected},
    }


# ---------------------------------------------------------------------------
# Self-reflection section (Story 50)
# ---------------------------------------------------------------------------


def _build_self_section(ctx) -> dict:
    template = leadership_team_self_template(ctx.organization, ctx.program)
    if template is None:
        return {
            "state": "missing",
            "reflection_id": None,
            "template_id": None,
            "editable": False,
            "period_start": None,
            "period_end": None,
        }
    period_start, period_end = resolve_period(
        template, anchor=ctx.today, program=ctx.program,
    )
    existing = latest_self_reflection(
        ctx.person, template, period_start, period_end,
    )
    state = "missing"
    reflection_id = None
    editable = period_start <= ctx.today <= period_end
    if existing is not None:
        state = "day_off" if is_day_off_answer(existing) else "complete"
        reflection_id = existing.id
    return {
        "state": state,
        "reflection_id": reflection_id,
        "template_id": template.id,
        "editable": editable,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "cadence": template.cadence,
    }


# ---------------------------------------------------------------------------
# Templates-and-assignments summary (Stories 51, 53)
# ---------------------------------------------------------------------------


def _build_templates_summary(ctx) -> dict:
    """Tiny "Templates & assignments" preview for the dashboard.

    PR A keeps this minimal — just counts of templates the viewer
    authored / can clone. PR B fills in the full library + active
    assignment counts.
    """
    from bunk_logs.core.models import ReflectionTemplate

    owned = ReflectionTemplate.objects.filter(
        organization=ctx.organization,
        metadata__contains={"created_by_membership_id": ctx.membership.id},
    ).count() if _template_metadata_supported() else 0
    return {
        "owned_template_count": owned,
        "assignment_count": 0,  # filled in PR B
    }


def _template_metadata_supported() -> bool:
    """Whether ReflectionTemplate has the LT-builder ``metadata`` column.

    PR A doesn't add the column yet — PR B does. The dashboard accepts
    that ``owned_template_count`` is 0 until then; this keeps the API
    shape stable across PRs.
    """
    from bunk_logs.core.models import ReflectionTemplate
    return "metadata" in {f.name for f in ReflectionTemplate._meta.get_fields()}


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


def _role_labels() -> list[tuple[str, str]]:
    from bunk_logs.core.models import Membership
    return list(Membership.ROLES)


def _person_brief(person) -> str:
    if person is None:
        return ""
    name = (person.preferred_name or person.first_name or "").strip()
    last_initial = (person.last_name or "").strip()[:1]
    if name and last_initial:
        return f"{name} {last_initial}."
    return name or last_initial or ""

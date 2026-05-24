"""Shared helpers for Unit Head read + write endpoints.

UH endpoints share a viewer-resolution contract (UH Membership + active
counselor supervisions), a Bunk resolution path (via
:func:`Supervision.objects.bunks_for_uh`), and a handful of Story 11/12
projections (score grid columns, attention badges, bunk-concerns
surfacing). They live here so the per-endpoint modules can stay focused
on shaping the payload and the rules can be tested once.

Reuse from the counselor common module is deliberate: ``get_today``,
``is_editable_today``, ``enforce_edit_window``, ``is_day_off_answer``,
``off_camp_camper_ids``, and ``_resolve_template`` aren't UH-specific and
behave identically here. Importing them keeps the rollover-aware "today"
contract and edit-window semantics consistent across role flows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rest_framework.exceptions import PermissionDenied

from bunk_logs.api.counselor.common import enforce_edit_window
from bunk_logs.api.counselor.common import is_day_off_answer
from bunk_logs.api.counselor.common import is_editable_today
from bunk_logs.api.counselor.common import off_camp_camper_ids
from bunk_logs.core.assignment_resolution import resolve_template_for
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
from bunk_logs.core.reflection_scores import iter_scored_fields
from bunk_logs.core.reflection_scores import resolve_rating_cells
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date
    from datetime import datetime

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program


__all__ = [
    "ATTENTION_BADGE_ORDER",
    "UH_TEMPLATE_SLUG",
    "ViewerContext",
    "build_score_grid",
    "bunk_camper_ids",
    "compute_attention_badges",
    "enforce_edit_window",
    "is_day_off_answer",
    "is_editable_today",
    "off_camp_camper_ids",
    "supervised_bunk_ids",
    "supervised_bunks",
    "unit_head_self_template",
    "viewer_or_403",
]


UH_TEMPLATE_SLUG = "unit-head-self-reflection"

# Story 10 criterion 7 sort priority: bunks with badges go first in this
# order, then alphabetical for unbadged bunks.
ATTENTION_BADGE_ORDER: tuple[str, ...] = (
    "help_requested",
    "bunk_concerns",
    "off_camp",
    "low_completion",
)


@dataclass(frozen=True)
class ViewerContext:
    """Resolved request context for a Unit Head endpoint."""

    person: Person
    organization: Organization
    membership: Membership
    program: Program
    today: date


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org + active UH Membership, or raise 403.

    UH endpoints require all of: authenticated user, an organization in
    request context (set by middleware), a Person profile in that org,
    and at least one active ``unit_head`` Membership. The "current"
    program is the Membership's program — UHs in multiple programs hit
    a separate program-picker (out of scope here; pick the newest).
    """
    org = getattr(request, "organization", None)
    if org is None:
        msg = "Organization context required."
        raise PermissionDenied(msg)
    if not request.user.is_authenticated:
        msg = "Authentication required."
        raise PermissionDenied(msg)
    person = Person.objects.filter(user=request.user).first()
    if person is None:
        msg = "Person profile required."
        raise PermissionDenied(msg)
    membership = (
        Membership.objects.filter(
            person=person, role="unit_head", is_active=True,
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        msg = "Unit Head role required."
        raise PermissionDenied(msg)
    program = membership.program
    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=program,
        today=get_today(org),
    )


# ---------------------------------------------------------------------------
# Bunk resolution (Story 10 criterion 5)
# ---------------------------------------------------------------------------


def supervised_bunks(
    membership: Membership, *, today: date | None = None,
) -> list[AssignmentGroup]:
    """Active bunk AssignmentGroups under the UH's supervision.

    Wraps :func:`Supervision.objects.bunks_for_uh` so endpoints can
    treat the result as a stable, ordered list (the manager returns a
    distinct queryset). Order is alphabetical by group name so the
    badge-sort in Story 10 criterion 7 has a deterministic tie-breaker.
    """
    qs = Supervision.objects.bunks_for_uh(membership, today=today).order_by("name")
    return list(qs.select_related("organization"))


def supervised_bunk_ids(
    membership: Membership, *, today: date | None = None,
) -> set[int]:
    """IDs only — useful for membership / inclusion checks."""
    return set(
        Supervision.objects.bunks_for_uh(membership, today=today)
        .values_list("id", flat=True),
    )


def bunk_camper_ids(bunk: AssignmentGroup) -> list[int]:
    """Active camper Person IDs assigned to a bunk as ``subject``.

    The unit-head dashboard never needs the full Person rows (the
    Camper Dashboard endpoint loads those when drilled into), so we
    return IDs to keep the bunk-list endpoint cheap.
    """
    return list(
        AssignmentGroupMembership.objects.filter(
            group=bunk, role_in_group="subject", is_active=True,
        )
        .order_by("person__last_name", "person__first_name")
        .values_list("person_id", flat=True),
    )


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


def unit_head_self_template(
    organization: Organization,
    program: Program,
    *,
    viewer: Person | None = None,
    as_of: date | None = None,
) -> ReflectionTemplate | None:
    """Daily self-reflection template for the UH role.

    Resolves via :func:`resolve_template_for` (Step 7_21): returns the
    template bound by an active ``TemplateAssignment`` for the
    (org, program, ``unit_head``, ``self``, ``daily``) tuple, or
    ``None`` when no assignment is active.
    """
    return resolve_template_for(
        organization=organization,
        program=program,
        as_of=as_of or get_today(organization),
        role="unit_head",
        subject_mode="self",
        cadence="daily",
        viewer=viewer,
    )


# ---------------------------------------------------------------------------
# Attention badges (Story 10 criterion 6)
# ---------------------------------------------------------------------------


def compute_attention_badges(
    *,
    bunk: AssignmentGroup,
    bunk_camper_ids_list: list[int],
    off_camp_ids: set[int],
    submitted_camper_ids: set[int],
    help_requested_camper_ids: set[int],
    bunk_concerns_referenced_bunk_ids: set[int],
    low_completion_threshold: float,
    expected_by_passed: bool,
) -> list[str]:
    """Compute attention badges for one bunk on one date.

    Returns the badge codes in dashboard-sort order
    (``help_requested`` first, then ``bunk_concerns``, ``off_camp``,
    ``low_completion``). The wider dashboard view applies the
    ``ATTENTION_BADGE_ORDER`` tuple to sort BETWEEN bunks; this helper
    is concerned only with WHICH badges apply to one bunk.

    Inputs:

    * ``bunk_camper_ids_list``: ordered camper IDs in the bunk.
    * ``off_camp_ids``: set of camper IDs flagged ``is_off_camp`` today
      (Story 10 — surfaced as the ``off_camp`` badge regardless of
      reflection state).
    * ``submitted_camper_ids``: campers with a ``is_complete=True``
      reflection for today; used to compute completion ratio.
    * ``help_requested_camper_ids``: camper IDs whose reflection asked
      for UH help — surfaces the ``help_requested`` badge (Story 10
      criterion 6.i).
    * ``bunk_concerns_referenced_bunk_ids``: the union of bunk IDs
      referenced by ANY counselor or UH bunk-concerns surface today.
      We only check membership; the caller does the resolution.
    * ``low_completion_threshold``: ratio (0.0-1.0) below which the
      ``low_completion`` badge fires. Default 0.5 (Story 10 criterion
      6.iv: "under 50%").
    * ``expected_by_passed``: whether the org-configured "expected by"
      time has passed (Story 58). Only check ``low_completion`` after
      that boundary; before the boundary, low completion is normal.
    """
    badges: list[str] = []
    if help_requested_camper_ids:
        badges.append("help_requested")
    if bunk.id in bunk_concerns_referenced_bunk_ids:
        badges.append("bunk_concerns")
    if off_camp_ids:
        badges.append("off_camp")

    expected = [cid for cid in bunk_camper_ids_list if cid not in off_camp_ids]
    if expected_by_passed and expected:
        covered = sum(1 for cid in expected if cid in submitted_camper_ids)
        ratio = covered / len(expected)
        if ratio < low_completion_threshold:
            badges.append("low_completion")

    return badges


# ---------------------------------------------------------------------------
# Score grid (Story 12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoreGridColumn:
    """One scored cell column in the Story 12 grid.

    ``label`` matches the key emitted by ``resolve_rating_cells`` so a
    consumer can directly index per-camper score dicts. ``field_key``
    is the schema field this column belongs to; for a ``rating_group``
    column ``category_key`` is the category, ``None`` for single
    ratings. ``scale_max`` drives the frontend palette selection.
    """

    label: str
    field_key: str
    field_type: str
    category_key: str | None
    scale_max: int


def score_grid_columns(template: ReflectionTemplate) -> list[ScoreGridColumn]:
    """Ordered list of cell columns for the Story 12 grid.

    Order matches the template ``schema['fields']`` sequence (Story 12
    criterion 7 forbids viewer reordering). Each rating_group expands
    to one column per declared category in the template's category
    order.
    """
    columns: list[ScoreGridColumn] = []
    for field, label, sm in iter_scored_fields(template):
        ftype = field.get("type")
        fkey = field.get("key")
        if not isinstance(fkey, str):
            continue
        category_key: str | None = None
        if ftype == "rating_group" and "__" in label:
            category_key = label.split("__", 1)[1]
        columns.append(
            ScoreGridColumn(
                label=label,
                field_key=fkey,
                field_type=ftype or "",
                category_key=category_key,
                scale_max=sm,
            ),
        )
    return columns


def build_score_grid(
    *,
    template: ReflectionTemplate,
    campers: list[Person],
    reflections_by_subject: dict[int, Reflection],
) -> dict:
    """Build the Story 12 score-grid payload.

    Returns ``{"columns": [...], "rows": [...]}`` where each row has a
    ``camper`` projection plus a ``cells`` dict keyed by the column
    label. Missing reflections produce a row of ``None`` cells (the
    frontend renders these visually distinct from low scores per
    Story 12 criterion 3).
    """
    columns = score_grid_columns(template)
    column_payload = [
        {
            "label": col.label,
            "field_key": col.field_key,
            "field_type": col.field_type,
            "category_key": col.category_key,
            "scale_max": col.scale_max,
        }
        for col in columns
    ]
    rows: list[dict] = []
    schema_fields = (template.schema or {}).get("fields") or []
    field_by_key = {
        f["key"]: f for f in schema_fields
        if isinstance(f, dict) and isinstance(f.get("key"), str)
    }
    for camper in campers:
        reflection = reflections_by_subject.get(camper.id)
        cells: dict[str, float | None] = {col.label: None for col in columns}
        if reflection is not None and reflection.answers:
            for col in columns:
                field = field_by_key.get(col.field_key)
                if field is None:
                    continue
                cells.update(resolve_rating_cells(field, reflection.answers or {}))
        rows.append(
            {
                "camper": {
                    "id": camper.id,
                    "first_name": camper.first_name,
                    "last_name": camper.last_name,
                    "preferred_name": camper.preferred_name,
                },
                "reflection_id": reflection.id if reflection else None,
                "cells": cells,
            },
        )
    return {"columns": column_payload, "rows": rows}


# ---------------------------------------------------------------------------
# Bunk concerns surfacing (Story 11 criterion 1.iv, UH2)
# ---------------------------------------------------------------------------


def bunk_concerns_referencing(
    *,
    organization: Organization,
    program: Program,
    target_date: date,
) -> dict[int, list[Reflection]]:
    """Map ``bunk_id -> [Reflection, ...]`` for today's bunk-concern flags.

    Both the counselor self-reflection and the UH self-reflection may
    flag specific bunks via the ``bunk_concerns_bunks`` field
    (``option_source="supervised_bunks"``). We materialize those
    references so the bunk dashboard can surface them in its "Bunk
    concerns" section regardless of WHICH supervisor wrote them.

    Empty values in ``bunk_concerns_bunks`` (missing key, ``None``,
    empty list) are skipped — only positive references count.
    """
    rows = (
        Reflection.all_objects.filter(
            organization=organization,
            program=program,
            period_start__lte=target_date,
            period_end__gte=target_date,
            is_complete=True,
        )
        .select_related("author", "template")
    )
    out: dict[int, list[Reflection]] = {}
    for r in rows:
        ids = (r.answers or {}).get("bunk_concerns_bunks") or []
        if not isinstance(ids, list):
            continue
        for raw in ids:
            try:
                bid = int(raw)
            except (ValueError, TypeError):
                continue
            out.setdefault(bid, []).append(r)
    return out


def help_requested_camper_ids_from(
    reflections: dict[int, Reflection],
) -> set[int]:
    """Subject IDs whose reflection asked for UH help today.

    Looks for either ``request_unit_head_help`` (canonical Crane Lake
    key per the rbac-seed template) or any field tagged
    ``dashboard_role="help_request_unit_head"`` (forward-compatible
    convention). Treats string ``"yes"`` / ``true`` / boolean ``True``
    as positive.
    """
    out: set[int] = set()
    for camper_id, refl in reflections.items():
        answers = refl.answers or {}
        if _is_truthy_yes_no(answers.get("request_unit_head_help")):
            out.add(camper_id)
            continue
        for field in (refl.template.schema or {}).get("fields") or []:
            if not isinstance(field, dict):
                continue
            if field.get("dashboard_role") != "help_request_unit_head":
                continue
            key = field.get("key")
            if isinstance(key, str) and _is_truthy_yes_no(answers.get(key)):
                out.add(camper_id)
                break
    return out


def _is_truthy_yes_no(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "1"}
    return False


# ---------------------------------------------------------------------------
# Bunk-concerns id validation (Stories 16.7 / UH2 write surface)
# ---------------------------------------------------------------------------


def validate_bunk_concerns_ids(
    raw: object, supervised: set[int],
) -> list[int]:
    """Coerce a submitted ``bunk_concerns_bunks`` value to ``[int]``.

    Used by the UH self-reflection write endpoint to ensure a viewer
    can't flag bunks they don't supervise. Returns the list of valid
    bunk IDs (de-duplicated, preserving submission order); raises
    ``PermissionDenied`` when any submitted ID is outside the viewer's
    supervised set. An empty / missing input returns ``[]``.
    """
    if raw is None or raw == "":
        return []
    if not isinstance(raw, list):
        msg = "bunk_concerns_bunks must be a list of bunk IDs."
        raise PermissionDenied(msg)
    seen: list[int] = []
    for item in raw:
        try:
            bid = int(item)
        except (ValueError, TypeError) as e:
            msg = "bunk_concerns_bunks entries must be integer bunk IDs."
            raise PermissionDenied(msg) from e
        if bid not in supervised:
            msg = "You can only flag bunks you supervise."
            raise PermissionDenied(msg)
        if bid not in seen:
            seen.append(bid)
    return seen


# ---------------------------------------------------------------------------
# Datetime helpers (Story 10 criterion 6.iv expected-by gate)
# ---------------------------------------------------------------------------


def expected_by_passed(
    organization: Organization,
    target_date: date,
    *,
    now: datetime | None = None,
) -> bool:
    """Whether the org-configured "expected by" time has passed today.

    Reads ``organization.settings.dashboards.expected_by_hour`` (an int
    in [0, 23], local time). Default ``18`` (6pm) per Story 58 best
    practice. Returns ``True`` when the supplied / current time is at
    or past that hour on ``target_date``; ``False`` otherwise (so low
    completion doesn't fire in the morning).
    """
    settings = (organization.settings or {}).get("dashboards") or {}
    hour = settings.get("expected_by_hour", 18)
    try:
        hour_int = int(hour)
    except (ValueError, TypeError):
        hour_int = 18
    hour_int = max(0, min(23, hour_int))

    from django.utils import timezone

    from bunk_logs.core.time_utils import get_org_timezone

    tz = get_org_timezone(organization)
    current = (now or timezone.now()).astimezone(tz)
    if current.date() < target_date:
        return False
    if current.date() > target_date:
        return True
    return current.hour >= hour_int

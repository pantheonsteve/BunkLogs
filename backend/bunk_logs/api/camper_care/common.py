"""Shared helpers for Camper Care endpoints (Step 7_8).

Mirrors the structure of ``api/unit_head/common.py`` so reading either
module reveals the same shape: viewer resolution + caseload helpers +
small projections shared across endpoints. Camper Care's caseload is
``Supervision.target_type='bunk'`` rather than the UH's per-counselor
target, so we reuse :func:`Supervision.objects.caseload_campers` and
add a thin ``caseload_bunks`` wrapper for the dashboard tree.

Per CC7 (Story 22 decision), Camper Care orders are team-shared across
the program -- *not* caseload-scoped -- so the order helper here scopes
by program rather than by supervised bunks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from bunk_logs.api.counselor.common import _resolve_template
from bunk_logs.api.counselor.common import enforce_edit_window  # noqa: F401 (re-export)
from bunk_logs.api.counselor.common import is_day_off_answer  # noqa: F401 (re-export)
from bunk_logs.api.counselor.common import is_editable_today  # noqa: F401 (re-export)
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program


CC_SELF_TEMPLATE_SLUGS = (
    "camper-care-self-reflection",
    "wellness-self-reflection",
)


__all__ = [
    "CC_SELF_TEMPLATE_SLUGS",
    "ViewerContext",
    "camper_care_self_template",
    "caseload_bunk_ids",
    "caseload_bunks",
    "caseload_bunks_with_unit",
    "caseload_camper_ids",
    "caseload_campers",
    "viewer_or_403",
]


@dataclass(frozen=True)
class ViewerContext:
    """Resolved request context for a Camper Care endpoint."""

    person: Person
    organization: Organization
    membership: Membership
    program: Program
    today: date


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org + active Camper Care Membership, or 403.

    Camper Care endpoints require all of: organization context, an
    authenticated user, a Person profile in that org, and at least one
    active ``camper_care`` Membership. When a user has CC memberships in
    multiple programs we pick the newest by ``created_at`` -- a
    program-picker UI is out of scope for Tier 1.
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
            person=person, role="camper_care", is_active=True,
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        msg = "Camper Care role required."
        raise PermissionDenied(msg)
    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
        today=get_today(org),
    )


# ---------------------------------------------------------------------------
# Caseload (Story 18 + CC1)
# ---------------------------------------------------------------------------


def caseload_bunks(
    membership: Membership, *, today: date | None = None,
) -> list[AssignmentGroup]:
    """Active bunk AssignmentGroups on the Camper Care member's caseload.

    Returns bunks targeted by an active BUNK supervision row for the
    given membership, ordered alphabetically so the dashboard tree has
    a stable tie-breaker after the badge-based sort.
    """
    bunk_ids = list(
        Supervision.objects.active(today=today)
        .for_supervisor(membership)
        .filter(target_type="bunk", target_bunk__isnull=False)
        .values_list("target_bunk_id", flat=True),
    )
    if not bunk_ids:
        return []
    return list(
        AssignmentGroup.objects.filter(id__in=bunk_ids, is_active=True)
        .select_related("parent", "organization")
        .order_by("name"),
    )


def caseload_bunks_with_unit(
    membership: Membership, *, today: date | None = None,
) -> dict[int | None, list[AssignmentGroup]]:
    """Group caseload bunks by their parent ``unit`` AssignmentGroup id.

    Story 18 wants the caseload rendered as Unit -> Bunks. Bunks with
    no parent unit fall under ``None``; the dashboard view treats that
    bucket as an "Unassigned" section so they still render.
    """
    out: dict[int | None, list[AssignmentGroup]] = {}
    for bunk in caseload_bunks(membership, today=today):
        out.setdefault(bunk.parent_id, []).append(bunk)
    return out


def caseload_campers(
    membership: Membership, *, today: date | None = None,
):
    """Pass-through to the shipped Supervision.caseload_campers helper.

    Re-exposed under the api/camper_care namespace so callers don't
    need to import from ``core.managers`` directly.
    """
    return Supervision.objects.caseload_campers(membership, today=today)


def caseload_camper_ids(
    membership: Membership, *, today: date | None = None,
) -> set[int]:
    """Person IDs of campers on the viewer's caseload (today)."""
    return set(caseload_campers(membership, today=today).values_list("id", flat=True))


def bunk_camper_ids(bunk: AssignmentGroup) -> list[int]:
    """Active camper Person IDs assigned to a bunk as ``subject``.

    Mirrors :func:`api.unit_head.common.bunk_camper_ids` so the
    dashboard payload shape stays consistent across UH and CC.
    """
    return list(
        AssignmentGroupMembership.objects.filter(
            group=bunk, role_in_group="subject", is_active=True,
        )
        .order_by("person__last_name", "person__first_name")
        .values_list("person_id", flat=True),
    )


def caseload_bunk_ids(
    membership: Membership, *, today: date | None = None,
) -> set[int]:
    """Bunk IDs on the Camper Care member's caseload (today).

    Equivalent to ``supervised_bunk_ids`` for UH — used by write
    endpoints that need to validate user-supplied bunk IDs against the
    viewer's authority (e.g. ``bunk_concerns_bunks`` in a CC
    self-reflection answer payload).
    """
    return {b.id for b in caseload_bunks(membership, today=today)}


def camper_care_self_template(
    organization: Organization, program: Program,
) -> ReflectionTemplate | None:
    """Daily Camper Care self-reflection template, org-shadowing-global.

    Uses the same fallback resolver the counselor / UH flows use so a
    customer can ship a single template targeting multiple supervisor
    roles via ``author_role_filter``. Returns ``None`` when no template
    is configured for the program type — callers must handle that case
    (the dashboard renders a "no template configured" placeholder).
    """
    qs = ReflectionTemplate.all_objects.filter(
        Q(role="camper_care") | Q(author_role_filter__contains=["camper_care"]),
        subject_mode="self",
        cadence="daily",
    )
    return _resolve_template(
        qs, organization=organization, program_type=program.program_type,
    )

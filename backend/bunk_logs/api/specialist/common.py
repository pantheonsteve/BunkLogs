"""Shared helpers for Specialist endpoints (Step 7_9).

Mirrors the structure of ``api/camper_care/common.py``. Key differences
from other role flows:

* Specialists have no caseload — they can note any camper in the
  programs they are a Member of (Story 25 criterion 1 + 7).
* Sub-type label comes from ``membership.tags`` e.g. ``specialist:waterfront``
  → "Waterfront Specialist" (Story 24 criterion 5).
* Cross-program: a Specialist may have active memberships in multiple programs;
  the dashboard shows the newest (primary), but the camper picker spans all.
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
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program


__all__ = [
    "ViewerContext",
    "specialist_label",
    "specialist_program_ids",
    "specialist_self_template",
    "viewer_or_403",
]


@dataclass(frozen=True)
class ViewerContext:
    """Resolved request context for a Specialist endpoint."""

    person: Person
    organization: Organization
    membership: Membership
    program: Program
    today: date


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org + active Specialist Membership, or 403.

    Picks the newest active ``specialist`` Membership as the "primary"
    program for dashboard scoping. The camper picker uses all programs
    via :func:`specialist_program_ids`.
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
            person=person, role="specialist", is_active=True,
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        msg = "Specialist role required."
        raise PermissionDenied(msg)
    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
        today=get_today(org),
    )


def specialist_label(membership: Membership) -> str:
    """Human-readable role label from membership tags.

    A tag of the form ``specialist:waterfront`` → "Waterfront Specialist".
    Falls back to "Specialist" when no sub-type tag is present.
    """
    for tag in membership.tags or []:
        if isinstance(tag, str) and tag.startswith("specialist:"):
            sub = tag[len("specialist:"):]
            if sub:
                return f"{sub.replace('-', ' ').title()} Specialist"
    return "Specialist"


def specialist_program_ids(person: Person) -> list[int]:
    """All active program IDs where ``person`` has a specialist membership."""
    return list(
        Membership.objects.filter(
            person=person, role="specialist", is_active=True,
        ).values_list("program_id", flat=True),
    )


def specialist_self_template(
    organization: Organization,
    program: Program,
) -> ReflectionTemplate | None:
    """Active daily specialist self-reflection template for the program.

    Uses the shared org-shadow resolver. Returns ``None`` when no template
    is configured (dashboard shows a placeholder).
    """
    qs = ReflectionTemplate.all_objects.filter(
        Q(role="specialist") | Q(author_role_filter__contains=["specialist"]),
        subject_mode="self",
        cadence="daily",
    )
    return _resolve_template(
        qs, organization=organization, program_type=program.program_type,
    )

"""Shared helpers for Kitchen Staff endpoints (Step 7_11).

Key invariants
--------------
* A Kitchen Staff viewer must have an active ``kitchen_staff`` Membership.
* Template resolution uses the ``kitchen_staff`` role filter with daily cadence.
* Edit window: until rollover boundary (same as specialist/counselor).
* Preferred language is read from ``Person.preferred_language`` and forwarded
  to the template localizer so prompts arrive in the user's preferred language.
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
    "kitchen_staff_template",
    "viewer_or_403",
]


@dataclass(frozen=True)
class ViewerContext:
    """Resolved request context for a Kitchen Staff endpoint."""

    person: Person
    organization: Organization
    membership: Membership
    program: Program
    today: date


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org + active Kitchen Staff Membership, or 403."""
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
            person=person, role="kitchen_staff", is_active=True,
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        msg = "Kitchen Staff role required."
        raise PermissionDenied(msg)
    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
        today=get_today(org),
    )


def kitchen_staff_template(
    organization: Organization,
    program: Program,
) -> ReflectionTemplate | None:
    """Active daily kitchen_staff self-reflection template for the program."""
    qs = ReflectionTemplate.all_objects.filter(
        Q(role="kitchen_staff") | Q(author_role_filter__contains=["kitchen_staff"]),
        subject_mode="self",
        cadence="daily",
    )
    return _resolve_template(
        qs, organization=organization, program_type=program.program_type,
    )

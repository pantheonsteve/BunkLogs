"""Shared helpers for Kitchen Staff endpoints (Step 7_11).

Key invariants
--------------
* A Kitchen Staff viewer must have an active ``kitchen_staff`` Membership.
* Template resolution flows through
  :func:`bunk_logs.core.assignment_resolution.resolve_template_for`
  (Step 7_21) instead of inline ``ReflectionTemplate`` queries, so the
  active template is whichever one the Leadership Team has assigned
  to the program for the day.
* Edit window: until rollover boundary (same as specialist/counselor).
* Preferred language is read from ``Person.preferred_language`` and forwarded
  to the template localizer so prompts arrive in the user's preferred language.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rest_framework.exceptions import PermissionDenied

from bunk_logs.api.counselor.common import enforce_edit_window  # noqa: F401 (re-export)
from bunk_logs.api.counselor.common import is_day_off_answer  # noqa: F401 (re-export)
from bunk_logs.api.counselor.common import is_editable_today  # noqa: F401 (re-export)
from bunk_logs.core.assignment_resolution import resolve_template_for
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program
    from bunk_logs.core.models import ReflectionTemplate


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
    *,
    viewer: Person | None = None,
    as_of: date | None = None,
) -> ReflectionTemplate | None:
    """Active daily kitchen_staff self-reflection template for the program.

    Resolves via :func:`resolve_template_for` (Step 7_21): the template
    is the one bound by an active ``TemplateAssignment`` for this
    (org, program) targeting the ``kitchen_staff`` role. Returns
    ``None`` when no assignment is active — the dashboard surfaces that
    as the ``no_template`` empty state.
    """
    return resolve_template_for(
        organization=organization,
        program=program,
        as_of=as_of or get_today(organization),
        role="kitchen_staff",
        subject_mode="self",
        cadence="daily",
        viewer=viewer,
    )

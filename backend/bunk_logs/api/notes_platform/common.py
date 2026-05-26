"""Shared helpers for the Notes platform API endpoints (Step 7_19).

Notes endpoints require an authenticated user with a Person profile and at
least one active v1-enabled Membership (Counselor or Unit Head). The
viewer_or_403 helper resolves all of this from the request and caches the
person on request._notes_person for serializer use.
"""

from __future__ import annotations

from dataclasses import dataclass

from rest_framework.exceptions import PermissionDenied

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.notes.audience import V1_AUTHOR_ROLES


@dataclass(frozen=True)
class ViewerContext:
    person: Person
    organization: Organization
    membership: Membership
    program: Program


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer context for Notes endpoints, or raise 403.

    Requires: authenticated user, org context, Person profile, and at least one
    active Membership in a v1-enabled role (counselor, junior_counselor, unit_head).
    """
    org = getattr(request, "organization", None)
    if org is None:
        raise PermissionDenied("Organization context required.")
    if not request.user.is_authenticated:
        raise PermissionDenied("Authentication required.")
    person = Person.objects.filter(user=request.user).first()
    if person is None:
        raise PermissionDenied("Person profile required.")

    membership = (
        Membership.all_objects.filter(
            person=person,
            role__in=V1_AUTHOR_ROLES,
            is_active=True,
            program__organization=org,
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        raise PermissionDenied(
            "Notes not yet enabled for this role. Active Counselor or Unit Head role required."
        )

    # Cache person on request for serializer use
    request._notes_person = person  # noqa: SLF001

    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
    )

"""Shared helpers for the Notes platform API endpoints (Step 7_19).

Notes are open to every authenticated person with an active Membership in
the requesting organization. Audience options differ per role (see
``audience_options_for``), but read/compose/reply are not role-gated.
"""

from __future__ import annotations

from dataclasses import dataclass

from rest_framework.exceptions import PermissionDenied

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program


@dataclass(frozen=True)
class ViewerContext:
    person: Person
    organization: Organization
    membership: Membership
    program: Program


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer context for Notes endpoints, or raise 403.

    Requires: authenticated user, org context, Person profile, and at least one
    active Membership in any role for a Program inside the requesting org.
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
        Membership.all_objects.filter(
            person=person,
            is_active=True,
            program__organization=org,
        )
        .select_related("program", "program__organization")
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        msg = "Active membership required to use Notes."
        raise PermissionDenied(msg)

    request._notes_person = person

    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
    )

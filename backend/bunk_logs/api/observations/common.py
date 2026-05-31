"""Shared helpers for Observations API endpoints (Step 7_23)."""

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
    """Resolve viewer context for Observations endpoints, or raise 403."""
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
        msg = "Active membership required."
        raise PermissionDenied(msg)

    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
    )

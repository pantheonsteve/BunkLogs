"""Shared viewer resolution for Faculty (TBE) endpoints — Step 4_8.

Mirrors ``api/madrich/common.py``'s ``viewer_or_403``, scoped to the
``faculty`` role instead of ``madrich``. Extracted here (rather than
duplicated inline, as ``availability.py`` did for its single classroom
view) because the Challenge Log needs the same resolution across
several endpoints that aren't scoped to one classroom up front.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rest_framework.exceptions import PermissionDenied

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.program_scope import primary_membership
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program

ROLE = "faculty"


@dataclass(frozen=True)
class ViewerContext:
    """Resolved request context for a Faculty endpoint."""

    person: Person
    organization: Organization
    membership: Membership
    program: Program
    today: date


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org + Faculty Membership, or raise 403.

    Prefers a membership on a currently running program, but falls back
    to any active faculty membership so the home page still loads in the
    gap before a program starts (same rule as auth routing).
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
    membership = primary_membership(
        person, today=get_today(org), role=ROLE,
    )
    if membership is None:
        msg = "Faculty role required."
        raise PermissionDenied(msg)
    return ViewerContext(
        person=person,
        organization=org,
        membership=membership,
        program=membership.program,
        today=get_today(org),
    )

"""Operational program scoping for dashboard group lists.

A program is *operational* on a given day when ``is_active`` is true and
``start_date <= today <= end_date``. Default dashboards only surface groups
and memberships tied to operational programs; historical views opt in explicitly.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django.db.models import Q

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Person


def operational_program_q(*, today: date, prefix: str = "program") -> Q:
    """Return a ``Q`` matching programs running on ``today``."""
    if prefix:
        return Q(**{
            f"{prefix}__is_active": True,
            f"{prefix}__start_date__lte": today,
            f"{prefix}__end_date__gte": today,
        })
    return Q(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
    )


def is_program_operational(program, *, today: date) -> bool:
    """True when ``program`` is active and ``today`` falls in its date window."""
    return (
        program.is_active
        and program.start_date <= today <= program.end_date
    )


def operational_memberships_qs(
    person: Person,
    *,
    today: date,
    **filters,
):
    """Active ``Membership`` rows whose program is operational on ``today``."""
    return (
        Membership.objects.filter(
            person=person,
            is_active=True,
            **filters,
        )
        .filter(operational_program_q(today=today, prefix="program"))
    )


def primary_operational_membership(
    person: Person,
    *,
    today: date,
    **filters,
) -> Membership | None:
    """Newest operational membership for ``person``, or ``None``."""
    return (
        operational_memberships_qs(person, today=today, **filters)
        .select_related("program")
        .order_by("-created_at")
        .first()
    )


def operational_author_groups_qs(
    person: Person,
    *,
    today: date,
    **filters,
):
    """Author ``AssignmentGroupMembership`` rows in operational programs."""
    return (
        AssignmentGroupMembership.objects.filter(
            person=person,
            role_in_group="author",
            is_active=True,
            group__is_active=True,
            **filters,
        )
        .filter(operational_program_q(today=today, prefix="group__program"))
    )


def operational_assignment_groups_qs(
    *,
    today: date,
    organization: Organization | None = None,
    **filters,
):
    """Active ``AssignmentGroup`` rows whose program is operational on ``today``."""
    qs = AssignmentGroup.objects.filter(is_active=True, **filters)
    if organization is not None:
        qs = qs.filter(organization=organization)
    return qs.filter(operational_program_q(today=today, prefix="program"))

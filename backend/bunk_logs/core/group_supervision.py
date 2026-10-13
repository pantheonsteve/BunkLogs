"""Create and end Supervision rows from group placement.

A role marked ``supervises_group`` for a group type gets an active
``Supervision(target_type=assignment_group)`` when that person is placed
in the group, and the row is end-dated when the placement ends. Camper
care caseloads are not in the default config, so those bunk rows are
left alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from django.db import transaction
from django.db.models import Q

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Supervision
from bunk_logs.core.org_config import group_type_config
from bunk_logs.core.time_utils import get_today


@dataclass
class SupervisionPlan:
    creates: list[tuple[Membership, AssignmentGroup]] = field(default_factory=list)
    ends: list[Supervision] = field(default_factory=list)


def supervising_memberships(agm: AssignmentGroupMembership) -> list[Membership]:
    """Active memberships of this person that should supervise this placement."""
    group = agm.group
    org = group.organization
    cfg = group_type_config(org).get(group.group_type) or {}
    if not cfg.get("enabled", True):
        return []
    roles = [
        member["role"]
        for member in cfg.get("members") or []
        if member.get("placed_as") == agm.role_in_group and member.get("supervises_group")
    ]
    if not roles:
        return []
    return list(
        Membership.all_objects.filter(
            person_id=agm.person_id,
            program_id=group.program_id,
            role__in=roles,
            is_active=True,
        ),
    )


def sync_placement(agm: AssignmentGroupMembership, *, active: bool) -> None:
    """Ensure supervision matches this placement. ``active=False`` end-dates it."""
    today = get_today(agm.group.organization)
    for membership in supervising_memberships(agm):
        if active and agm.is_active:
            _ensure(membership, agm.group, today)
        else:
            _end(membership, agm.group, today)


def plan_group_supervision(org, *, today=None) -> SupervisionPlan:
    """What ``--apply`` would write. Reads only."""
    today = today or get_today(org)
    plan = SupervisionPlan()
    config = group_type_config(org)
    wanted: list[tuple[str, str, str]] = []
    for group_type, cfg in config.items():
        if not cfg.get("enabled", True):
            continue
        for member in cfg.get("members") or []:
            if member.get("supervises_group"):
                wanted.append((group_type, member["placed_as"], member["role"]))

    covered: set[tuple[int, int]] = set()
    for group_type, placed_as, role in wanted:
        # The membership has to be in the group's program. A person who
        # holds the role in another program does not supervise this one.
        placements = (
            AssignmentGroupMembership.all_objects.filter(
                is_active=True,
                role_in_group=placed_as,
                group__organization=org,
                group__is_active=True,
                group__group_type=group_type,
            )
            .select_related("group")
        )
        memberships = {
            (m.person_id, m.program_id): m
            for m in Membership.all_objects.filter(
                program__organization=org,
                role=role,
                is_active=True,
            )
        }
        for agm in placements:
            membership = memberships.get((agm.person_id, agm.group.program_id))
            if membership is None:
                continue
            covered.add((membership.id, agm.group_id))
            if not _active_qs(membership, agm.group, today).exists():
                plan.creates.append((membership, agm.group))

    open_rows = (
        Supervision.all_objects.filter(
            target_type=Supervision.TargetType.ASSIGNMENT_GROUP,
            target_group__organization=org,
            start_date__lte=today,
        )
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
        .select_related("supervisor_membership", "target_group")
    )
    for row in open_rows:
        key = (row.supervisor_membership_id, row.target_group_id)
        if key in covered or row.end_date == today:
            continue
        plan.ends.append(row)
    return plan


def apply_group_supervision(plan: SupervisionPlan, *, today) -> None:
    """Write ``plan``. A second call with a fresh plan is a no-op."""
    with transaction.atomic():
        for membership, group in plan.creates:
            _ensure(membership, group, today)
        for row in plan.ends:
            _end_row(row, today)


def _active_qs(membership: Membership, group: AssignmentGroup, today):
    return Supervision.all_objects.filter(
        supervisor_membership=membership,
        target_type=Supervision.TargetType.ASSIGNMENT_GROUP,
        target_group=group,
        start_date__lte=today,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))


def _ensure(membership: Membership, group: AssignmentGroup, today) -> Supervision | None:
    existing = _active_qs(membership, group, today).first()
    if existing is not None:
        return existing
    row = Supervision(
        supervisor_membership=membership,
        target_type=Supervision.TargetType.ASSIGNMENT_GROUP,
        target_group=group,
        start_date=today,
    )
    row.save()
    return row


def _end(membership: Membership, group: AssignmentGroup, today) -> None:
    for row in _active_qs(membership, group, today):
        _end_row(row, today)


def _end_row(row: Supervision, today) -> None:
    end = today if row.start_date <= today else row.start_date
    if row.end_date == end:
        return
    row.end_date = end
    row.save(update_fields=["end_date"])

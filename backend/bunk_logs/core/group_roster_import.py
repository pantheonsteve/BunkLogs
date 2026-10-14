"""Helpers for group-scoped roster CSV imports."""

from __future__ import annotations

from django.core.management.base import CommandError

from bunk_logs.core.models import SUBJECT_ROLES
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program
from bunk_logs.core.org_config import group_type_config


def load_target_group(
    *,
    target_group_id: int | None,
    org: Organization,
    program: Program,
) -> AssignmentGroup | None:
    if target_group_id is None:
        return None
    try:
        group = AssignmentGroup.all_objects.get(pk=target_group_id)
    except AssignmentGroup.DoesNotExist:
        msg = f"AssignmentGroup not found: {target_group_id}"
        raise CommandError(msg)
    if group.organization_id != org.pk or group.program_id != program.pk:
        msg = "Target group must belong to the import organization and program."
        raise CommandError(msg)
    return group


def infer_role_in_group_from_program_role(program_role: str) -> str:
    return "subject" if program_role in SUBJECT_ROLES else "author"


def _single_configured_seat(group: AssignmentGroup, program_role: str) -> str | None:
    """The one seat this role holds in the group's type, or None when it isn't exactly one."""
    cfg = group_type_config(group.organization).get(group.group_type) or {}
    if not cfg.get("enabled", True):
        return None
    seats: list[str] = []
    for member in cfg.get("members") or []:
        placed = member.get("placed_as")
        if member.get("role") == program_role and placed in {"author", "subject"} and placed not in seats:
            seats.append(placed)
    if len(seats) == 1:
        return seats[0]
    return None


def resolve_role_in_group(
    row: dict,
    program_role: str,
    *,
    bulk_role_in_group: str | None = None,
    group: AssignmentGroup | None = None,
) -> str:
    """Column wins. One configured seat is used. Two seats still need a choice."""
    explicit = (row.get("role_in_group") or "").strip().lower()
    if explicit in {"subject", "author"}:
        return explicit
    if group is not None:
        seat = _single_configured_seat(group, program_role)
        if seat is not None:
            return seat
    if bulk_role_in_group in {"subject", "author"}:
        return bulk_role_in_group
    return infer_role_in_group_from_program_role(program_role)

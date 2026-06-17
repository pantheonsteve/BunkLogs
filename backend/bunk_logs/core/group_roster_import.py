"""Helpers for group-scoped roster CSV imports."""

from __future__ import annotations

from django.core.management.base import CommandError

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program


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
    return "subject" if program_role == "camper" else "author"


def resolve_role_in_group(
    row: dict,
    program_role: str,
    *,
    bulk_role_in_group: str | None = None,
) -> str:
    explicit = (row.get("role_in_group") or "").strip().lower()
    if explicit in {"subject", "author"}:
        return explicit
    if bulk_role_in_group in {"subject", "author"}:
        return bulk_role_in_group
    return infer_role_in_group_from_program_role(program_role)

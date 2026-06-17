"""Clone an assignment group (structure + roster) to another program."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from django.utils.text import slugify

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program


class GroupCloneError(Exception):
    """Raised when clone preconditions fail."""

    def __init__(self, message: str, *, field_name: str | None = None):
        super().__init__(message)
        self.field_name = field_name
        self.message = message


def unique_group_slug(program: Program, base_slug: str) -> str:
    """Return a slug unique within the program, suffixing -2, -3, … on collision."""
    slug = (base_slug or "group").strip("-")[:100] or "group"
    if not AssignmentGroup.all_objects.filter(program=program, slug=slug).exists():
        return slug
    stem = slug[:95] if len(slug) > 95 else slug
    for n in range(2, 1000):
        candidate = f"{stem}-{n}"
        if not AssignmentGroup.all_objects.filter(program=program, slug=candidate).exists():
            return candidate
    msg = "Could not generate a unique slug for this program."
    raise GroupCloneError(msg, field_name="slug")


@dataclass
class CloneResult:
    group: AssignmentGroup
    memberships_copied: int = 0
    program_memberships_copied: int = 0
    warnings: list[str] = field(default_factory=list)


def clone_assignment_group(
    *,
    source: AssignmentGroup,
    target_program: Program,
    organization: Organization,
) -> CloneResult:
    """Copy group structure and active roster to another program in the same org."""
    if target_program.organization_id != organization.pk:
        msg = "Target program must belong to your organization."
        raise GroupCloneError(msg, field_name="target_program")
    if source.organization_id != organization.pk:
        msg = "Source group must belong to your organization."
        raise GroupCloneError(msg, field_name="source")
    if source.program_id == target_program.pk:
        msg = "Target program must differ from the source group's program."
        raise GroupCloneError(msg, field_name="target_program")

    warnings: list[str] = []

    if AssignmentGroup.all_objects.filter(
        program=target_program,
        name=source.name,
        is_active=True,
    ).exists():
        warnings.append(
            f"Target program already has an active group named '{source.name}'.",
        )

    parent = None
    if source.parent_id:
        parent_match = AssignmentGroup.all_objects.filter(
            program=target_program,
            slug=source.parent.slug,
            is_active=True,
        ).first()
        if parent_match:
            parent = parent_match
        else:
            warnings.append(
                f"Parent group '{source.parent.name}' was not found in the target program; "
                "cloned group has no parent.",
            )

    metadata = {**(source.metadata or {})}
    metadata["cloned_from"] = {
        "group_id": source.pk,
        "program_id": source.program_id,
    }

    base_slug = source.slug or slugify(source.name)[:100]
    slug = unique_group_slug(target_program, base_slug)

    cloned_group = AssignmentGroup.all_objects.create(
        organization=organization,
        program=target_program,
        name=source.name,
        slug=slug,
        group_type=source.group_type,
        parent=parent,
        metadata=metadata,
        is_active=True,
    )

    source_memberships = AssignmentGroupMembership.all_objects.filter(
        group=source,
        is_active=True,
    ).select_related("person")

    roster_person_ids: set[int] = set()
    memberships_copied = 0

    for src_mem in source_memberships:
        roster_person_ids.add(src_mem.person_id)
        membership, created = AssignmentGroupMembership.all_objects.get_or_create(
            group=cloned_group,
            person=src_mem.person,
            role_in_group=src_mem.role_in_group,
            defaults={
                "is_active": True,
                "start_date": src_mem.start_date,
                "end_date": src_mem.end_date,
                "metadata": dict(src_mem.metadata or {}),
            },
        )
        if not created:
            membership.is_active = True
            membership.start_date = src_mem.start_date
            membership.end_date = src_mem.end_date
            membership.metadata = dict(src_mem.metadata or {})
            membership.save(
                update_fields=["is_active", "start_date", "end_date", "metadata"],
            )
        memberships_copied += 1

    program_memberships_copied = 0
    if roster_person_ids:
        source_program_memberships = Membership.all_objects.filter(
            program=source.program,
            person_id__in=roster_person_ids,
            is_active=True,
        )
        for src_prog_mem in source_program_memberships:
            prog_mem, created = Membership.all_objects.get_or_create(
                program=target_program,
                person=src_prog_mem.person,
                role=src_prog_mem.role,
                defaults={
                    "is_active": True,
                    "start_date": src_prog_mem.start_date,
                    "end_date": src_prog_mem.end_date,
                    "tags": list(src_prog_mem.tags or []),
                    "metadata": dict(src_prog_mem.metadata or {}),
                    "grade_level": src_prog_mem.grade_level,
                },
            )
            if not created:
                prog_mem.is_active = True
                prog_mem.start_date = src_prog_mem.start_date
                prog_mem.end_date = src_prog_mem.end_date
                prog_mem.tags = list(src_prog_mem.tags or [])
                prog_mem.metadata = dict(src_prog_mem.metadata or {})
                prog_mem.grade_level = src_prog_mem.grade_level
                prog_mem.save(
                    update_fields=[
                        "is_active",
                        "start_date",
                        "end_date",
                        "tags",
                        "metadata",
                        "grade_level",
                    ],
                )
            program_memberships_copied += 1

    return CloneResult(
        group=cloned_group,
        memberships_copied=memberships_copied,
        program_memberships_copied=program_memberships_copied,
        warnings=warnings,
    )

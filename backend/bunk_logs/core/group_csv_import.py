"""CSV import for AssignmentGroup records (structure only, no roster).

One row == one group. Parent groups may appear in the same file or already exist
in the program. Groups are upserted by (program, group_type, slugified name).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils.text import slugify

from bunk_logs.core.models import AssignmentGroup

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program

GROUP_IMPORT_COLUMNS: tuple[str, ...] = (
    "name",
    "group_type",
    "parent_name",
    "parent_group_type",
    "is_active",
)

VALID_GROUP_TYPES = frozenset(choice[0] for choice in AssignmentGroup.GROUP_TYPES)

# Process parents before children when both appear in the same file.
GROUP_TYPE_ORDER: dict[str, int] = {
    "division": 0,
    "cohort": 1,
    "unit": 2,
    "bunk": 3,
    "classroom": 4,
    "caseload": 5,
    "team": 6,
    "specialty": 7,
    "custom": 8,
}

_TRUE = frozenset({"1", "true", "yes", "y", "t"})
_FALSE = frozenset({"0", "false", "no", "n", "f", ""})


@dataclass
class GroupImportRow:
    name: str
    group_type: str
    parent_name: str = ""
    parent_group_type: str = ""
    is_active: bool = True


@dataclass
class ParseResult:
    rows: list[GroupImportRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ImportSummary:
    row_count: int = 0
    groups_created: int = 0
    groups_updated: int = 0
    parents_linked: int = 0


def _coerce_bool(raw: str, *, default: bool) -> bool:
    value = (raw or "").strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False if value else default
    return default


def build_group_import_template_csv() -> tuple[str, str]:
    """Return ``(filename, csv_text)`` for a downloadable starter template."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(GROUP_IMPORT_COLUMNS)
    writer.writerow(["Upper Camp", "division", "", "", "true"])
    writer.writerow(["Sophomores", "unit", "Upper Camp", "division", "true"])
    writer.writerow(["Bunk Maple", "bunk", "Sophomores", "unit", "true"])
    return "assignment_groups_import_template.csv", buf.getvalue()


def parse_group_import_csv(text: str) -> ParseResult:
    """Parse + validate a groups CSV. Never raises on row-level issues."""
    result = ParseResult()
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        result.errors.append("CSV is empty or has no header row.")
        return result

    normalized_headers = {(h or "").strip().lower() for h in reader.fieldnames}
    missing = {"name", "group_type"} - normalized_headers
    if missing:
        result.errors.append(
            f"Missing required column(s): {', '.join(sorted(missing))}.",
        )
        return result

    for idx, raw in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        name = row.get("name", "")
        group_type = row.get("group_type", "").lower()
        parent_name = row.get("parent_name", "")
        parent_group_type = row.get("parent_group_type", "").lower()
        is_active = _coerce_bool(row.get("is_active", ""), default=True)

        row_errors: list[str] = []
        if not name:
            row_errors.append("name is required")
        if not group_type:
            row_errors.append("group_type is required")
        elif group_type not in VALID_GROUP_TYPES:
            row_errors.append(f"unknown group_type {group_type!r}")
        if parent_name and parent_group_type and parent_group_type not in VALID_GROUP_TYPES:
            row_errors.append(f"unknown parent_group_type {parent_group_type!r}")

        if row_errors:
            result.errors.append(f"Row {idx}: {'; '.join(row_errors)}")
            continue

        result.rows.append(
            GroupImportRow(
                name=name,
                group_type=group_type,
                parent_name=parent_name,
                parent_group_type=parent_group_type,
                is_active=is_active,
            ),
        )

    return result


def _sort_rows(rows: list[GroupImportRow]) -> list[GroupImportRow]:
    return sorted(
        rows,
        key=lambda row: (GROUP_TYPE_ORDER.get(row.group_type, 99), row.name.lower()),
    )


def _group_lookup_key(group_type: str, slug: str) -> tuple[str, str]:
    return (group_type, slug)


def _resolve_parent(
    *,
    program: Program,
    parent_name: str,
    parent_group_type: str,
    lookup: dict[tuple[str, str], AssignmentGroup],
) -> AssignmentGroup | None:
    slug = slugify(parent_name)[:100]
    if parent_group_type:
        return lookup.get(_group_lookup_key(parent_group_type, slug))

    matches = [
        group
        for (group_type, group_slug), group in lookup.items()
        if group_slug == slug and group.program_id == program.pk
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return None
    return None


def apply_group_import(
    organization: Organization,
    program: Program,
    rows: list[GroupImportRow],
    *,
    dry_run: bool = False,
) -> tuple[ImportSummary, list[str]]:
    """Upsert groups for a program. Returns summary and row-level errors."""
    summary = ImportSummary(row_count=len(rows))
    errors: list[str] = []
    if not rows:
        return summary, errors

    if program.organization_id != organization.pk:
        errors.append("Program must belong to your organization.")
        return summary, errors

    sorted_rows = _sort_rows(rows)
    lookup: dict[tuple[str, str], AssignmentGroup] = {}

    for existing in AssignmentGroup.all_objects.filter(program=program):
        lookup[_group_lookup_key(existing.group_type, existing.slug)] = existing

    pending_parents: list[tuple[GroupImportRow, AssignmentGroup]] = []

    def upsert_group(row: GroupImportRow) -> AssignmentGroup:
        nonlocal summary
        slug = slugify(row.name)[:100]
        key = _group_lookup_key(row.group_type, slug)
        group = lookup.get(key)
        if group is None:
            if dry_run:
                group = AssignmentGroup(
                    organization=organization,
                    program=program,
                    name=row.name,
                    slug=slug,
                    group_type=row.group_type,
                    is_active=row.is_active,
                )
                lookup[key] = group
                summary.groups_created += 1
                return group

            group = AssignmentGroup.all_objects.create(
                organization=organization,
                program=program,
                name=row.name,
                slug=slug,
                group_type=row.group_type,
                is_active=row.is_active,
            )
            lookup[key] = group
            summary.groups_created += 1
            return group

        changed: list[str] = []
        if group.name != row.name:
            group.name = row.name
            changed.append("name")
        if group.is_active != row.is_active:
            group.is_active = row.is_active
            changed.append("is_active")
        if changed and not dry_run:
            group.save(update_fields=changed)
        if changed:
            summary.groups_updated += 1
        return group

    for row in sorted_rows:
        group = upsert_group(row)
        if row.parent_name:
            pending_parents.append((row, group))

    for row, group in pending_parents:
        parent = _resolve_parent(
            program=program,
            parent_name=row.parent_name,
            parent_group_type=row.parent_group_type,
            lookup=lookup,
        )
        if parent is None:
            if row.parent_group_type:
                errors.append(
                    f"Row with {row.name!r}: parent {row.parent_name!r} "
                    f"({row.parent_group_type}) not found.",
                )
            else:
                parent_slug = slugify(row.parent_name)[:100]
                matches = [
                    group_type
                    for group_type, group_slug in lookup
                    if group_slug == parent_slug
                ]
                if len(matches) > 1:
                    errors.append(
                        f"Row with {row.name!r}: parent {row.parent_name!r} is ambiguous; "
                        "set parent_group_type.",
                    )
                else:
                    errors.append(
                        f"Row with {row.name!r}: parent {row.parent_name!r} not found.",
                    )
            continue
        if parent is group or (
            parent.pk is not None
            and group.pk is not None
            and parent.pk == group.pk
        ):
            errors.append(f"Row with {row.name!r}: group cannot be its own parent.")
            continue
        if group.parent_id != parent.pk:
            if not dry_run:
                group.parent = parent
                group.save(update_fields=["parent"])
            summary.parents_linked += 1

    return summary, errors


def import_groups_from_csv_text(
    *,
    organization: Organization,
    program: Program,
    csv_text: str,
    dry_run: bool = False,
) -> dict:
    """Parse a CSV and import groups. Convenience wrapper for API views."""
    parsed = parse_group_import_csv(csv_text)
    if parsed.errors:
        return {
            "mode": "preview" if dry_run else "commit",
            "valid": False,
            "row_count": len(parsed.rows),
            "errors": parsed.errors,
        }

    if dry_run:
        with transaction.atomic():
            summary, link_errors = apply_group_import(
                organization,
                program,
                parsed.rows,
                dry_run=True,
            )
            transaction.set_rollback(True)
    else:
        with transaction.atomic():
            summary, link_errors = apply_group_import(
                organization,
                program,
                parsed.rows,
                dry_run=False,
            )

    all_errors = list(parsed.errors) + link_errors
    return {
        "mode": "preview" if dry_run else "commit",
        "valid": not all_errors,
        "row_count": summary.row_count,
        "summary": {
            "groups_created": summary.groups_created,
            "groups_updated": summary.groups_updated,
            "parents_linked": summary.parents_linked,
        },
        "errors": all_errors,
    }

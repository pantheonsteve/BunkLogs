"""Import a Campminder CSV export into Person/Membership/AssignmentGroup records.

Extends the staff-only import_campminder_staff command to handle camper rosters
and bunk hierarchy (bunk → unit → division) as well as caseloads.

Idempotent: re-running with the same CSV does not create duplicates.
Person records are keyed by campminder_id stored in Person.external_ids.
AssignmentGroups are keyed by (program, group_type, slugified-name).
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils.text import slugify

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import RosterImportLog

logger = logging.getLogger(__name__)

VALID_ROLES: set[str] = {choice[0] for choice in Membership.ROLES}

COUNSELOR_ROLES: set[str] = {
    "counselor",
    "junior_counselor",
    "specialist",
    "general_counselor",
    "unit_head",
    "leadership_team",
}


def _normalize_tags(raw: str) -> list[str]:
    return sorted({t.strip().lower() for t in raw.split(",") if t.strip()})


def _get_or_create_group(
    program: Program,
    group_type: str,
    name: str,
    parent: AssignmentGroup | None = None,
) -> AssignmentGroup:
    slug = slugify(name)[:100]
    group, _ = AssignmentGroup.all_objects.get_or_create(
        program=program,
        group_type=group_type,
        slug=slug,
        defaults={
            "organization": program.organization,
            "name": name,
            "parent": parent,
            "is_active": True,
        },
    )
    if parent is not None and group.parent_id != parent.pk:
        group.parent = parent
        group.save(update_fields=["parent"])
    return group


def _ensure_membership(
    group: AssignmentGroup,
    person: Person,
    role_in_group: str,
) -> AssignmentGroupMembership:
    membership, _ = AssignmentGroupMembership.all_objects.get_or_create(
        group=group,
        person=person,
        role_in_group=role_in_group,
        defaults={"is_active": True},
    )
    if not membership.is_active:
        membership.is_active = True
        membership.save(update_fields=["is_active"])
    return membership


def _upsert_person(org: Organization, row: dict, campminder_id: str) -> tuple[Person, bool, bool]:
    """Return (person, created, updated)."""
    first_name = (row.get("first_name") or "").strip()
    last_name = (row.get("last_name") or "").strip()
    email = (row.get("email") or "").strip()

    person = Person.all_objects.filter(
        organization=org,
        external_ids__campminder_id=campminder_id,
    ).first()

    if person is None:
        person = Person.all_objects.create(
            organization=org,
            first_name=first_name,
            last_name=last_name,
            email=email,
            external_ids={"campminder_id": campminder_id},
        )
        return person, True, False

    changed: list[str] = []
    for field, value in [("first_name", first_name), ("last_name", last_name), ("email", email)]:
        if getattr(person, field) != value:
            setattr(person, field, value)
            changed.append(field)
    merged_ids = {**person.external_ids, "campminder_id": campminder_id}
    if merged_ids != person.external_ids:
        person.external_ids = merged_ids
        changed.append("external_ids")
    if changed:
        person.save(update_fields=changed)
        return person, False, True
    return person, False, False


class Command(BaseCommand):
    help = (
        "Import a Campminder CSV export into Person/Membership/AssignmentGroup records. "
        "Supports both staff-only and full roster (campers + bunk hierarchy) formats."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--csv-path", required=True, help="Path to the Campminder CSV export.")
        parser.add_argument("--org-slug", required=True, help="Organization slug (e.g. 'clc').")
        parser.add_argument("--program-slug", required=True, help="Program slug (e.g. 'summer-2026').")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report without writing to the database.",
        )
        parser.add_argument(
            "--reconcile",
            action="store_true",
            help=(
                "In addition to creating new memberships, deactivate AssignmentGroupMemberships "
                "for (group, role_in_group) pairs that appear in the DB but not in the CSV."
            ),
        )

    def handle(self, *args, **options) -> None:
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            msg = f"CSV file not found: {csv_path}"
            raise CommandError(msg)

        try:
            org = Organization.objects.get(slug=options["org_slug"])
        except Organization.DoesNotExist:
            msg = f"Organization not found: {options['org_slug']!r}"
            raise CommandError(msg)

        try:
            program = Program.all_objects.get(organization=org, slug=options["program_slug"])
        except Program.DoesNotExist:
            msg = f"Program not found: {options['program_slug']!r} under org {options['org_slug']!r}"
            raise CommandError(
                msg,
            )

        dry_run: bool = options["dry_run"]
        reconcile: bool = options["reconcile"]

        with csv_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        log: RosterImportLog | None = None
        if not dry_run:
            log = RosterImportLog.all_objects.create(
                organization=org,
                program=program,
                importer_type="campminder",
                status="running",
                csv_filename=csv_path.name,
            )

        persons_created = persons_updated = persons_skipped = 0
        memberships_created = memberships_reactivated = 0
        memberships_deactivated = 0
        warnings: list[str] = []

        # Track (group_pk, role_in_group) → set of person_pks seen in this CSV
        seen_group_members: dict[tuple[int, str], set[int]] = {}

        for i, row in enumerate(rows, start=2):
            campminder_id = (row.get("campminder_id") or "").strip()
            if not campminder_id:
                warnings.append(f"Row {i}: missing campminder_id — skipped")
                continue

            role = (row.get("role") or "").strip()
            if role not in VALID_ROLES:
                warnings.append(f"Row {i} (campminder_id={campminder_id}): unknown role {role!r} — skipped")
                continue

            bunk_name = (row.get("bunk_name") or "").strip()
            unit_name = (row.get("unit_name") or "").strip()
            division_name = (row.get("division_name") or "").strip()
            caseload_name = (row.get("caseload_name") or "").strip()
            caseload_owner_id = (row.get("caseload_owner_campminder_id") or "").strip()
            lang_pref = (row.get("language_preference") or "").strip()
            tags = _normalize_tags(row.get("tags") or "")

            if dry_run:
                self.stdout.write(
                    f"[dry-run] Row {i}: campminder_id={campminder_id} role={role} "
                    f"bunk={bunk_name or '—'} unit={unit_name or '—'} "
                    f"division={division_name or '—'} caseload={caseload_name or '—'}",
                )
                continue

            with transaction.atomic():
                person, created, updated = _upsert_person(org, row, campminder_id)
                if created:
                    persons_created += 1
                elif updated:
                    persons_updated += 1
                else:
                    persons_skipped += 1

                membership, mem_created = Membership.all_objects.get_or_create(
                    program=program,
                    person=person,
                    role=role,
                )
                meta = {**membership.metadata}
                if lang_pref:
                    meta["language_preference"] = lang_pref
                membership.metadata = meta
                membership.tags = tags
                membership.save(update_fields=["tags", "metadata"])

                if bunk_name:
                    division_group: AssignmentGroup | None = None
                    unit_group: AssignmentGroup | None = None

                    if division_name:
                        division_group = _get_or_create_group(program, "division", division_name)

                    if unit_name:
                        unit_group = _get_or_create_group(program, "unit", unit_name, parent=division_group)

                    bunk_group = _get_or_create_group(program, "bunk", bunk_name, parent=unit_group)

                    role_in_group = "subject" if role == "camper" else "author"
                    _, bunk_mem_created = AssignmentGroupMembership.all_objects.get_or_create(
                        group=bunk_group,
                        person=person,
                        role_in_group=role_in_group,
                        defaults={"is_active": True},
                    )
                    key = (bunk_group.pk, role_in_group)
                    seen_group_members.setdefault(key, set()).add(person.pk)
                    if bunk_mem_created:
                        memberships_created += 1

                if caseload_name:
                    if not caseload_owner_id:
                        warnings.append(
                            f"Row {i}: caseload_name set but caseload_owner_campminder_id missing — skipped",
                        )
                    else:
                        owner = Person.all_objects.filter(
                            organization=org,
                            external_ids__campminder_id=caseload_owner_id,
                        ).first()
                        if owner is None:
                            warnings.append(
                                f"Row {i}: caseload owner with campminder_id={caseload_owner_id!r} not found — skipped",
                            )
                        else:
                            caseload_group = _get_or_create_group(program, "caseload", caseload_name)
                            AssignmentGroupMembership.all_objects.get_or_create(
                                group=caseload_group,
                                person=owner,
                                role_in_group="author",
                                defaults={"is_active": True},
                            )
                            _, case_mem_created = AssignmentGroupMembership.all_objects.get_or_create(
                                group=caseload_group,
                                person=person,
                                role_in_group="subject",
                                defaults={"is_active": True},
                            )
                            key = (caseload_group.pk, "subject")
                            seen_group_members.setdefault(key, set()).add(person.pk)
                            if case_mem_created:
                                memberships_created += 1

        if reconcile and not dry_run:
            for (group_pk, role_in_group), present_person_ids in seen_group_members.items():
                stale = AssignmentGroupMembership.all_objects.filter(
                    group_id=group_pk,
                    role_in_group=role_in_group,
                    is_active=True,
                ).exclude(person_id__in=present_person_ids)
                deactivated = stale.update(is_active=False)
                memberships_deactivated += deactivated

        summary: dict[str, Any] = {
            "persons_created": persons_created,
            "persons_updated": persons_updated,
            "persons_unchanged": persons_skipped,
            "memberships_created": memberships_created,
            "memberships_reactivated": memberships_reactivated,
            "memberships_deactivated": memberships_deactivated,
            "warnings": warnings,
        }

        if log is not None:
            log.status = "completed"
            log.summary = summary
            from django.utils import timezone
            log.completed_at = timezone.now()
            log.save(update_fields=["status", "summary", "completed_at"])

        if dry_run:
            self.stdout.write(self.style.NOTICE(f"[dry-run] Rows inspected: {len(rows)}"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Persons created: {persons_created}  updated: {persons_updated}  "
                    f"unchanged: {persons_skipped} | "
                    f"Group memberships created: {memberships_created}  "
                    f"deactivated: {memberships_deactivated}",
                ),
            )
        for w in warnings:
            self.stdout.write(self.style.WARNING(w))

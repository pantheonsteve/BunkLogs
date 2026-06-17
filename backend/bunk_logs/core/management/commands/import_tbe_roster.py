"""Import a TBE ShulCloud CSV export into Person/Membership/AssignmentGroup records.

TBE uses a lighter format than Campminder. Madrichim are added as *subjects* of
the classroom (so faculty can observe them) AND as *authors* of their own
self-reflection group membership.  Faculty are authors of the classroom.

Idempotent: re-running with the same CSV does not create duplicates.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils.text import slugify

from bunk_logs.core.group_roster_import import load_target_group
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import RosterImportLog

logger = logging.getLogger(__name__)

VALID_ROLES: set[str] = {choice[0] for choice in Membership.ROLES}


def _get_or_create_classroom(program: Program, classroom_name: str) -> AssignmentGroup:
    slug = slugify(classroom_name)[:100]
    group, _ = AssignmentGroup.all_objects.get_or_create(
        program=program,
        group_type="classroom",
        slug=slug,
        defaults={
            "organization": program.organization,
            "name": classroom_name,
            "is_active": True,
        },
    )
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


def _upsert_person(
    org: Organization,
    first_name: str,
    last_name: str,
    email: str,
) -> tuple[Person, bool, bool]:
    """Match on (org, first_name, last_name) since TBE CSVs have no external ID.

    Returns (person, created, updated).
    """
    person = Person.all_objects.filter(
        organization=org,
        first_name__iexact=first_name,
        last_name__iexact=last_name,
    ).first()

    if person is None:
        person = Person.all_objects.create(
            organization=org,
            first_name=first_name,
            last_name=last_name,
            email=email or "",
        )
        return person, True, False

    changed: list[str] = []
    if email and person.email != email:
        person.email = email
        changed.append("email")
    if changed:
        person.save(update_fields=changed)
        return person, False, True
    return person, False, False


class Command(BaseCommand):
    help = (
        "Import a TBE ShulCloud CSV export into Person/Membership/AssignmentGroup records. "
        "Creates classrooms with Madrichim as subjects and faculty as authors."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--csv-path", required=True, help="Path to the TBE ShulCloud CSV export.")
        parser.add_argument("--org-slug", required=True, help="Organization slug (e.g. 'tbe').")
        parser.add_argument("--program-slug", required=True, help="Program slug.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report without writing to the database.",
        )
        parser.add_argument(
            "--log-id",
            type=int,
            default=None,
            help="Existing RosterImportLog PK to update (API import path).",
        )
        parser.add_argument(
            "--target-group-id",
            type=int,
            default=None,
            help="Add each imported row to this AssignmentGroup (group detail import path).",
        )
        parser.add_argument(
            "--bulk-role-in-group",
            default="",
            help="Default role_in_group for target-group imports (subject or author).",
        )

    def _resolve_import_log(
        self,
        *,
        org: Organization,
        program: Program,
        csv_path: Path,
        log_id: int | None,
        dry_run: bool,
    ) -> RosterImportLog | None:
        if dry_run:
            return None
        if log_id is not None:
            try:
                log = RosterImportLog.all_objects.get(pk=log_id)
            except RosterImportLog.DoesNotExist:
                msg = f"RosterImportLog not found: {log_id}"
                raise CommandError(msg)
            if log.organization_id != org.pk or log.program_id != program.pk:
                msg = "RosterImportLog organization/program does not match import target."
                raise CommandError(msg)
            updates: list[str] = []
            if log.csv_filename != csv_path.name:
                log.csv_filename = csv_path.name
                updates.append("csv_filename")
            if log.status != "running":
                log.status = "running"
                updates.append("status")
            if updates:
                log.save(update_fields=updates)
            return log
        return RosterImportLog.all_objects.create(
            organization=org,
            program=program,
            importer_type="tbe_shulcloud",
            status="running",
            csv_filename=csv_path.name,
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
        target_group = load_target_group(
            target_group_id=options.get("target_group_id"),
            org=org,
            program=program,
        )
        bulk_role_in_group = (options.get("bulk_role_in_group") or "").strip().lower()
        if bulk_role_in_group and bulk_role_in_group not in {"subject", "author"}:
            msg = f"Invalid bulk_role_in_group: {bulk_role_in_group!r}"
            raise CommandError(msg)

        with csv_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        log = self._resolve_import_log(
            org=org,
            program=program,
            csv_path=csv_path,
            log_id=options.get("log_id"),
            dry_run=dry_run,
        )

        persons_created = persons_updated = persons_skipped = 0
        memberships_created = 0
        warnings: list[str] = []

        for i, row in enumerate(rows, start=2):
            first_name = (row.get("first_name") or "").strip()
            last_name = (row.get("last_name") or "").strip()
            role = (row.get("role") or "").strip()
            classroom_name = (row.get("classroom_name") or "").strip()
            grade_level_raw = (row.get("grade_level") or "").strip()
            email = (row.get("email") or "").strip()

            if not first_name or not last_name:
                warnings.append(f"Row {i}: missing first_name or last_name — skipped")
                continue
            if not role:
                warnings.append(f"Row {i} ({first_name} {last_name}): missing role — skipped")
                continue
            if role not in VALID_ROLES:
                warnings.append(f"Row {i} ({first_name} {last_name}): unknown role {role!r} — skipped")
                continue
            if not classroom_name and target_group is None:
                warnings.append(f"Row {i} ({first_name} {last_name}): missing classroom_name — skipped")
                continue

            grade_level: int | None = None
            if grade_level_raw:
                try:
                    grade_level = int(grade_level_raw)
                except ValueError:
                    warnings.append(f"Row {i}: invalid grade_level {grade_level_raw!r} — ignored")

            if dry_run:
                self.stdout.write(
                    f"[dry-run] Row {i}: {first_name} {last_name} role={role} "
                    f"classroom={classroom_name} grade={grade_level or '—'}",
                )
                continue

            with transaction.atomic():
                person, created, updated = _upsert_person(org, first_name, last_name, email)
                if created:
                    persons_created += 1
                elif updated:
                    persons_updated += 1
                else:
                    persons_skipped += 1

                membership, _ = Membership.all_objects.get_or_create(
                    program=program,
                    person=person,
                    role=role,
                    defaults={"grade_level": grade_level},
                )
                if grade_level is not None and membership.grade_level != grade_level:
                    membership.grade_level = grade_level
                    membership.save(update_fields=["grade_level"])

                classroom = target_group if target_group is not None else _get_or_create_classroom(program, classroom_name)

                if bulk_role_in_group in {"subject", "author"}:
                    _, created_flag = AssignmentGroupMembership.all_objects.get_or_create(
                        group=classroom,
                        person=person,
                        role_in_group=bulk_role_in_group,
                        defaults={"is_active": True},
                    )
                    if created_flag:
                        memberships_created += 1
                elif role == "madrich":
                    # Madrichim: subject in the classroom (faculty observes them)
                    _, sub_created = AssignmentGroupMembership.all_objects.get_or_create(
                        group=classroom,
                        person=person,
                        role_in_group="subject",
                        defaults={"is_active": True},
                    )
                    if sub_created:
                        memberships_created += 1
                    # Also author in their own self-reflection context.
                    _, auth_created = AssignmentGroupMembership.all_objects.get_or_create(
                        group=classroom,
                        person=person,
                        role_in_group="author",
                        defaults={"is_active": True},
                    )
                    if auth_created:
                        memberships_created += 1
                elif role == "faculty":
                    _, auth_created = AssignmentGroupMembership.all_objects.get_or_create(
                        group=classroom,
                        person=person,
                        role_in_group="author",
                        defaults={"is_active": True},
                    )
                    if auth_created:
                        memberships_created += 1
                else:
                    # Other roles (e.g. admin helpers): add as subjects
                    _, other_created = AssignmentGroupMembership.all_objects.get_or_create(
                        group=classroom,
                        person=person,
                        role_in_group="subject",
                        defaults={"is_active": True},
                    )
                    if other_created:
                        memberships_created += 1

        summary = {
            "persons_created": persons_created,
            "persons_updated": persons_updated,
            "persons_unchanged": persons_skipped,
            "memberships_created": memberships_created,
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
                    f"unchanged: {persons_skipped} | Memberships created: {memberships_created}",
                ),
            )
        for w in warnings:
            self.stdout.write(self.style.WARNING(w))

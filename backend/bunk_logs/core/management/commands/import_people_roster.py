"""Import a generic spreadsheet roster CSV into Person/Membership records.

For orgs with no Campminder or ShulCloud export -- just a spreadsheet of
names. A blank ``role`` cell defaults to ``student``, and group placement is
inferred from the program role, so subject roles (camper/student) land as
subjects and everyone else as authors.

Idempotent: rows are matched to an existing Person by email, then by first and
last name, so re-running the same CSV does not create duplicates.
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from bunk_logs.core.campminder_csv import read_campminder_csv_rows
from bunk_logs.core.campminder_user_link import UserLinkAction
from bunk_logs.core.campminder_user_link import ensure_user_for_imported_person
from bunk_logs.core.group_roster_import import load_target_group
from bunk_logs.core.group_roster_import import resolve_role_in_group
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import RosterImportLog
from bunk_logs.core.people_csv import default_group_type
from bunk_logs.core.people_csv import normalize_people_row
from bunk_logs.core.people_csv import parse_optional_int

logger = logging.getLogger(__name__)

IMPORTER_TYPE = "spreadsheet"
VALID_ROLES: set[str] = {choice[0] for choice in Membership.ROLES}
VALID_GROUP_TYPES: set[str] = {choice[0] for choice in AssignmentGroup.GROUP_TYPES}


def _get_or_create_group(
    program: Program,
    group_name: str,
    group_type: str,
) -> AssignmentGroup:
    """Groups are keyed on (program, slug), so group_type only seeds new rows."""
    group, _ = AssignmentGroup.all_objects.get_or_create(
        program=program,
        slug=slugify(group_name)[:100],
        defaults={
            "organization": program.organization,
            "name": group_name,
            "group_type": group_type,
            "is_active": True,
        },
    )
    return group


def _upsert_person(
    org: Organization,
    *,
    first_name: str,
    last_name: str,
    preferred_name: str,
    email: str,
) -> tuple[Person, bool, bool]:
    """Match on email first, then on (org, first_name, last_name).

    Returns (person, created, updated).
    """
    person = None
    if email:
        person = Person.all_objects.filter(
            organization=org, email__iexact=email,
        ).first()
    if person is None:
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
            preferred_name=preferred_name or "",
            email=email or "",
        )
        return person, True, False

    changed: list[str] = []
    if email and person.email != email:
        person.email = email
        changed.append("email")
    if preferred_name and person.preferred_name != preferred_name:
        person.preferred_name = preferred_name
        changed.append("preferred_name")
    if changed:
        person.save(update_fields=changed)
        return person, False, True
    return person, False, False


class Command(BaseCommand):
    help = (
        "Import a generic spreadsheet roster CSV into Person/Membership records. "
        "Role defaults to student; group_name placement is optional."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--csv-path", required=True, help="Path to the roster CSV.")
        parser.add_argument("--org-slug", required=True, help="Organization slug.")
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
                raise CommandError(msg) from None
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
            importer_type=IMPORTER_TYPE,
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
            raise CommandError(msg) from None

        try:
            program = Program.all_objects.get(organization=org, slug=options["program_slug"])
        except Program.DoesNotExist:
            msg = f"Program not found: {options['program_slug']!r} under org {options['org_slug']!r}"
            raise CommandError(msg) from None

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

        rows = read_campminder_csv_rows(csv_path)
        fallback_group_type = default_group_type(program.program_type)

        log = self._resolve_import_log(
            org=org,
            program=program,
            csv_path=csv_path,
            log_id=options.get("log_id"),
            dry_run=dry_run,
        )

        persons_created = persons_updated = persons_unchanged = 0
        memberships_created = 0
        group_memberships_created = 0
        users_created = users_linked = 0
        warnings: list[str] = []

        for i, raw_row in enumerate(rows, start=2):
            row = normalize_people_row(raw_row)
            first_name = row["first_name"]
            last_name = row["last_name"]
            role = row["role"]
            group_name = row["group_name"]

            if not first_name or not last_name:
                warnings.append(f"Row {i}: missing first_name or last_name -- skipped")
                continue
            if role not in VALID_ROLES:
                warnings.append(
                    f"Row {i} ({first_name} {last_name}): unknown role {role!r} -- skipped",
                )
                continue

            group_type = row["group_type"] or fallback_group_type
            if group_name and group_type not in VALID_GROUP_TYPES:
                warnings.append(
                    f"Row {i} ({first_name} {last_name}): unknown group_type "
                    f"{group_type!r} -- skipped",
                )
                continue

            grade_level = parse_optional_int(row["grade_level"])
            if row["grade_level"] and grade_level is None:
                warnings.append(
                    f"Row {i}: invalid grade_level {row['grade_level']!r} -- ignored",
                )

            if dry_run:
                self.stdout.write(
                    f"[dry-run] Row {i}: {first_name} {last_name} role={role} "
                    f"group={group_name or '--'} grade={grade_level or '--'}",
                )
                continue

            with transaction.atomic():
                person, created, updated = _upsert_person(
                    org,
                    first_name=first_name,
                    last_name=last_name,
                    preferred_name=row["preferred_name"],
                    email=row["email"],
                )
                if created:
                    persons_created += 1
                elif updated:
                    persons_updated += 1
                else:
                    persons_unchanged += 1

                membership, membership_created = Membership.all_objects.get_or_create(
                    program=program,
                    person=person,
                    role=role,
                    defaults={"grade_level": grade_level},
                )
                if membership_created:
                    memberships_created += 1
                if grade_level is not None and membership.grade_level != grade_level:
                    membership.grade_level = grade_level
                    membership.save(update_fields=["grade_level"])

                # A no-op for subject roles; students never get a login.
                user_link = ensure_user_for_imported_person(person, membership_role=role)
                if user_link.action == UserLinkAction.CREATED:
                    users_created += 1
                elif user_link.action == UserLinkAction.LINKED:
                    users_linked += 1
                elif user_link.action == UserLinkAction.CONFLICT:
                    warnings.append(
                        f"Row {i} ({first_name} {last_name}): could not link user "
                        f"-- {user_link.message}",
                    )

                group = target_group
                if group is None and group_name:
                    group = _get_or_create_group(program, group_name, group_type)
                if group is None:
                    continue

                _, group_member_created = AssignmentGroupMembership.all_objects.get_or_create(
                    group=group,
                    person=person,
                    role_in_group=resolve_role_in_group(
                        row, role, bulk_role_in_group=bulk_role_in_group,
                    ),
                    defaults={"is_active": True},
                )
                if group_member_created:
                    group_memberships_created += 1

        summary = {
            "persons_created": persons_created,
            "persons_updated": persons_updated,
            "persons_unchanged": persons_unchanged,
            "memberships_created": memberships_created,
            "group_memberships_created": group_memberships_created,
            "users_created": users_created,
            "users_linked": users_linked,
            "warnings": warnings,
        }

        if log is not None:
            log.status = "completed"
            log.summary = summary
            log.completed_at = timezone.now()
            log.save(update_fields=["status", "summary", "completed_at"])

        if dry_run:
            self.stdout.write(self.style.NOTICE(f"[dry-run] Rows inspected: {len(rows)}"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Persons created: {persons_created}  updated: {persons_updated}  "
                    f"unchanged: {persons_unchanged} | Memberships created: "
                    f"{memberships_created} | Group memberships created: "
                    f"{group_memberships_created} | Users created: {users_created}  "
                    f"linked: {users_linked}",
                ),
            )
        for w in warnings:
            self.stdout.write(self.style.WARNING(w))

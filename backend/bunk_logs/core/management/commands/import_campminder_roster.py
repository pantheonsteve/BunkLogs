"""Import a Campminder CSV export into Person/Membership/AssignmentGroup records.

Extends the staff-only import_campminder_staff command to handle camper rosters
and bunk hierarchy (bunk → unit → division) as well as caseloads.

Idempotent: re-running with the same CSV does not create duplicates.
Person records are keyed by campminder_id stored in Person.external_ids.
AssignmentGroups are keyed by (program, group_type, slugified-name).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from datetime import date

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils.text import slugify

from bunk_logs.core.campminder_csv import format_csv_headers
from bunk_logs.core.campminder_csv import normalize_campminder_row
from bunk_logs.core.campminder_csv import parse_optional_iso_date
from bunk_logs.core.campminder_csv import read_campminder_csv_rows
from bunk_logs.core.campminder_person_match import MatchStrategy
from bunk_logs.core.campminder_person_match import match_campminder_person
from bunk_logs.core.campminder_person_match import strategy_is_duplicate
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
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[AssignmentGroupMembership, bool]:
    membership, created = AssignmentGroupMembership.all_objects.get_or_create(
        group=group,
        person=person,
        role_in_group=role_in_group,
        defaults={
            "is_active": True,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    changed: list[str] = []
    if not membership.is_active:
        membership.is_active = True
        changed.append("is_active")
    if start_date is not None and membership.start_date != start_date:
        membership.start_date = start_date
        changed.append("start_date")
    if end_date is not None and membership.end_date != end_date:
        membership.end_date = end_date
        changed.append("end_date")
    if changed:
        membership.save(update_fields=changed)
    return membership, created


def _duplicate_message(
    *,
    row_number: int,
    campminder_id: str,
    full_name: str,
    match_strategy: MatchStrategy,
    candidate_ids: list[int],
) -> str:
    if match_strategy == MatchStrategy.DUPLICATE_AMBIGUOUS_NAME:
        return (
            f"Row {row_number} ({full_name}, campminder_id={campminder_id}): "
            f"ambiguous name match — {len(candidate_ids)} existing persons "
            f"without Campminder ID (ids={candidate_ids}) — skipped"
        )
    if match_strategy == MatchStrategy.DUPLICATE_EMAIL_CONFLICT:
        return (
            f"Row {row_number} ({full_name}, campminder_id={campminder_id}): "
            f"email already linked to Person {candidate_ids[0]} with a different "
            f"Campminder ID — skipped"
        )
    return (
        f"Row {row_number} ({full_name}, campminder_id={campminder_id}): "
        f"same name as Person {candidate_ids[0]} who already has a different "
        f"Campminder ID — created as new person"
    )


def _upsert_person(
    org: Organization,
    row: dict,
    campminder_id: str,
    *,
    row_number: int,
) -> tuple[Person | None, bool, bool, bool, MatchStrategy, list[int]]:
    """Return (person, created, updated, merged, strategy, candidate_ids)."""
    first_name = (row.get("first_name") or "").strip()
    last_name = (row.get("last_name") or "").strip()
    preferred_name = (row.get("preferred_name") or "").strip()
    email = (row.get("email") or "").strip()

    person_match = match_campminder_person(
        org,
        campminder_id=campminder_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    if strategy_is_duplicate(person_match.strategy):
        if person_match.strategy == MatchStrategy.DUPLICATE_NAME_DIFFERENT_ID:
            person = Person.all_objects.create(
                organization=org,
                first_name=first_name,
                last_name=last_name,
                preferred_name=preferred_name,
                email=email,
                external_ids={"campminder_id": campminder_id},
            )
            return (
                person,
                True,
                False,
                False,
                person_match.strategy,
                person_match.candidate_ids,
            )
        return None, False, False, False, person_match.strategy, person_match.candidate_ids

    if person_match.strategy == MatchStrategy.NEW:
        person = Person.all_objects.create(
            organization=org,
            first_name=first_name,
            last_name=last_name,
            preferred_name=preferred_name,
            email=email,
            external_ids={"campminder_id": campminder_id},
        )
        return person, True, False, False, person_match.strategy, []

    person = person_match.person
    assert person is not None
    merged = person_match.strategy in {
        MatchStrategy.MERGE_EMAIL,
        MatchStrategy.MERGE_NAME,
    }

    changed: list[str] = []
    for field, value in [
        ("first_name", first_name),
        ("last_name", last_name),
        ("preferred_name", preferred_name),
        ("email", email),
    ]:
        if value and getattr(person, field) != value:
            setattr(person, field, value)
            changed.append(field)
    merged_ids = {**person.external_ids, "campminder_id": campminder_id}
    if merged_ids != person.external_ids:
        person.external_ids = merged_ids
        changed.append("external_ids")
    if changed:
        person.save(update_fields=changed)
        return person, False, True, merged, person_match.strategy, []
    return person, False, False, merged, person_match.strategy, []


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
            importer_type="campminder",
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
        reconcile: bool = options["reconcile"]
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

        log = self._resolve_import_log(
            org=org,
            program=program,
            csv_path=csv_path,
            log_id=options.get("log_id"),
            dry_run=dry_run,
        )

        persons_created = persons_updated = persons_skipped = persons_merged = 0
        users_created = users_linked = users_already_linked = 0
        memberships_created = memberships_reactivated = 0
        memberships_deactivated = 0
        warnings: list[str] = []
        duplicates_flagged: list[dict[str, Any]] = []
        user_link_conflicts: list[dict[str, Any]] = []

        # Track (group_pk, role_in_group) → set of person_pks seen in this CSV
        seen_group_members: dict[tuple[int, str], set[int]] = {}

        for i, raw_row in enumerate(rows, start=2):
            row = normalize_campminder_row(raw_row)
            campminder_id = row["campminder_id"]
            if not campminder_id:
                warnings.append(f"Row {i}: missing campminder_id — skipped")
                continue

            role = row["role"]
            if role not in VALID_ROLES:
                warnings.append(f"Row {i} (campminder_id={campminder_id}): unknown role {role!r} — skipped")
                continue

            if not row["last_name"]:
                msg = f"Row {i} (campminder_id={campminder_id}): missing last_name — skipped"
                if i == 2:
                    msg += f" (headers: {format_csv_headers(raw_row)})"
                warnings.append(msg)
                continue
            if not row["first_name"]:
                warnings.append(f"Row {i} (campminder_id={campminder_id}): missing first_name — skipped")
                continue

            bunk_name = row["bunk_name"]
            unit_name = row["unit_name"]
            division_name = row["division_name"]
            caseload_name = row["caseload_name"]
            caseload_owner_id = row["caseload_owner_campminder_id"]
            lang_pref = row["language_preference"]
            position_type = row.get("position_type") or ""
            position = row.get("position") or ""
            tags = _normalize_tags(row["tags"])
            start_date = parse_optional_iso_date(row.get("start_date") or "")
            end_date = parse_optional_iso_date(row.get("end_date") or "")

            if dry_run:
                self.stdout.write(
                    f"[dry-run] Row {i}: campminder_id={campminder_id} role={role} "
                    f"bunk={bunk_name or '—'} unit={unit_name or '—'} "
                    f"division={division_name or '—'} caseload={caseload_name or '—'} "
                    f"dates={start_date or '—'}→{end_date or '—'}",
                )
                continue

            with transaction.atomic():
                (
                    person,
                    created,
                    updated,
                    merged,
                    match_strategy,
                    candidate_ids,
                ) = _upsert_person(
                    org,
                    row,
                    campminder_id,
                    row_number=i,
                )
                full_name = f"{row['first_name']} {row['last_name']}".strip()
                if person is None:
                    msg = _duplicate_message(
                        row_number=i,
                        campminder_id=campminder_id,
                        full_name=full_name,
                        match_strategy=match_strategy,
                        candidate_ids=candidate_ids,
                    )
                    warnings.append(msg)
                    duplicates_flagged.append({
                        "row": i,
                        "campminder_id": campminder_id,
                        "full_name": full_name,
                        "reason": match_strategy.value,
                        "candidate_person_ids": candidate_ids,
                    })
                    continue
                if match_strategy == MatchStrategy.DUPLICATE_NAME_DIFFERENT_ID:
                    msg = _duplicate_message(
                        row_number=i,
                        campminder_id=campminder_id,
                        full_name=full_name,
                        match_strategy=match_strategy,
                        candidate_ids=candidate_ids,
                    )
                    warnings.append(msg)
                    duplicates_flagged.append({
                        "row": i,
                        "campminder_id": campminder_id,
                        "full_name": full_name,
                        "reason": match_strategy.value,
                        "candidate_person_ids": candidate_ids,
                    })
                if created:
                    persons_created += 1
                elif merged:
                    persons_merged += 1
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
                if position_type:
                    meta["campminder_position_type"] = position_type
                if position:
                    meta["campminder_position"] = position
                membership.metadata = meta
                membership.tags = tags
                membership_fields = ["tags", "metadata"]
                if start_date is not None:
                    membership.start_date = start_date
                    membership_fields.append("start_date")
                if end_date is not None:
                    membership.end_date = end_date
                    membership_fields.append("end_date")
                membership.save(update_fields=membership_fields)

                user_link = ensure_user_for_imported_person(person, membership_role=role)
                if user_link.action == UserLinkAction.CREATED:
                    users_created += 1
                elif user_link.action == UserLinkAction.LINKED:
                    users_linked += 1
                elif user_link.action == UserLinkAction.ALREADY_LINKED:
                    users_already_linked += 1
                elif user_link.action == UserLinkAction.CONFLICT:
                    msg = (
                        f"Row {i} ({full_name}, campminder_id={campminder_id}): "
                        f"could not link user — {user_link.message}"
                    )
                    warnings.append(msg)
                    user_link_conflicts.append({
                        "row": i,
                        "campminder_id": campminder_id,
                        "full_name": full_name,
                        "email": person.email,
                        "user_id": user_link.user_id,
                        "message": user_link.message,
                    })

                if target_group is not None:
                    role_in_group = resolve_role_in_group(
                        row,
                        role,
                        bulk_role_in_group=bulk_role_in_group or None,
                    )
                    _, group_mem_created = _ensure_membership(
                        target_group,
                        person,
                        role_in_group,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    key = (target_group.pk, role_in_group)
                    seen_group_members.setdefault(key, set()).add(person.pk)
                    if group_mem_created:
                        memberships_created += 1
                elif bunk_name:
                    division_group: AssignmentGroup | None = None
                    unit_group: AssignmentGroup | None = None

                    if division_name:
                        division_group = _get_or_create_group(program, "division", division_name)

                    if unit_name:
                        unit_group = _get_or_create_group(program, "unit", unit_name, parent=division_group)

                    bunk_group = _get_or_create_group(program, "bunk", bunk_name, parent=unit_group)

                    role_in_group = "subject" if role == "camper" else "author"
                    _, bunk_mem_created = _ensure_membership(
                        bunk_group,
                        person,
                        role_in_group,
                        start_date=start_date,
                        end_date=end_date,
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
                            _ensure_membership(
                                caseload_group,
                                owner,
                                "author",
                                start_date=start_date,
                                end_date=end_date,
                            )
                            _, case_mem_created = _ensure_membership(
                                caseload_group,
                                person,
                                "subject",
                                start_date=start_date,
                                end_date=end_date,
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
            "persons_merged": persons_merged,
            "persons_unchanged": persons_skipped,
            "memberships_created": memberships_created,
            "memberships_reactivated": memberships_reactivated,
            "memberships_deactivated": memberships_deactivated,
            "duplicates_flagged": duplicates_flagged,
            "users_created": users_created,
            "users_linked": users_linked,
            "users_already_linked": users_already_linked,
            "user_link_conflicts": user_link_conflicts,
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

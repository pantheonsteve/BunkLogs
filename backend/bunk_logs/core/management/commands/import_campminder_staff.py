"""Import staff roster from a Campminder CSV export into Person/Membership records.

Idempotent: re-running with the same CSV does not create duplicates.
Person records are keyed by campminder_id stored in Person.external_ids.
"""
from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

VALID_ROLES: set[str] = {choice[0] for choice in Membership.ROLES}


def _normalize_tags(raw: str) -> list[str]:
    return sorted({t.strip().lower() for t in raw.split(",") if t.strip()})


class Command(BaseCommand):
    help = "Import staff from a Campminder CSV export into Person/Membership records."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--csv-path", required=True, help="Path to the Campminder CSV export.")
        parser.add_argument("--org-slug", required=True, help="Organization slug (e.g. 'clc').")
        parser.add_argument("--program-slug", required=True, help="Program slug (e.g. 'summer-2026').")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report without writing to the database.",
        )

    def handle(self, *args, **options) -> None:
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        try:
            org = Organization.objects.get(slug=options["org_slug"])
        except Organization.DoesNotExist:
            raise CommandError(f"Organization not found: {options['org_slug']!r}")

        try:
            program = Program.all_objects.get(organization=org, slug=options["program_slug"])
        except Program.DoesNotExist:
            raise CommandError(
                f"Program not found: {options['program_slug']!r} under org {options['org_slug']!r}"
            )

        dry_run: bool = options["dry_run"]
        created = updated = skipped = 0
        warnings: list[str] = []

        with csv_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for i, row in enumerate(rows, start=2):
            campminder_id = row.get("campminder_id", "").strip()
            if not campminder_id:
                warnings.append(f"Row {i}: missing campminder_id — skipped")
                continue

            role = row.get("role", "").strip()
            if role not in VALID_ROLES:
                warnings.append(f"Row {i} (campminder_id={campminder_id}): unknown role {role!r} — skipped")
                continue

            first_name = row.get("first_name", "").strip()
            last_name = row.get("last_name", "").strip()
            email = row.get("email", "").strip()
            lang_pref = row.get("language_preference", "").strip()
            tags = _normalize_tags(row.get("tags", ""))

            if dry_run:
                self.stdout.write(
                    f"[dry-run] Row {i}: campminder_id={campminder_id} role={role} "
                    f"name='{first_name} {last_name}' email={email or '—'}"
                )
                continue

            with transaction.atomic():
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
                    created += 1
                else:
                    changed_fields: list[str] = []
                    if person.first_name != first_name:
                        person.first_name = first_name
                        changed_fields.append("first_name")
                    if person.last_name != last_name:
                        person.last_name = last_name
                        changed_fields.append("last_name")
                    if person.email != email:
                        person.email = email
                        changed_fields.append("email")
                    merged_ids = {**person.external_ids, "campminder_id": campminder_id}
                    if merged_ids != person.external_ids:
                        person.external_ids = merged_ids
                        changed_fields.append("external_ids")
                    if changed_fields:
                        person.save(update_fields=changed_fields)
                        updated += 1
                    else:
                        skipped += 1

                membership, _ = Membership.all_objects.get_or_create(
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

        self.stdout.write(
            self.style.SUCCESS(f"Done. Created: {created}  Updated: {updated}  Unchanged: {skipped}")
            if not dry_run
            else self.style.NOTICE(f"[dry-run] Rows inspected: {len(rows)}")
        )
        for w in warnings:
            self.stdout.write(self.style.WARNING(w))

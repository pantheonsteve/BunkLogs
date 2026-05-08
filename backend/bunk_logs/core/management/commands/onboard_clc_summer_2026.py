"""End-to-end onboarding command for URJ Crane Lake Camp — Summer 2026.

Idempotent: safe to run multiple times. Every sub-step is wrapped in the
individual command's own idempotency (get_or_create / update_or_create).

Usage
-----
# Minimal (no staff CSV):
  python manage.py onboard_clc_summer_2026

# With staff CSV import:
  python manage.py onboard_clc_summer_2026 --csv-path /path/to/staff.csv

# Dry-run: validate everything without writing:
  python manage.py onboard_clc_summer_2026 --csv-path /path/to/staff.csv --dry-run

# Skip the staff import (templates + org/program only):
  python manage.py onboard_clc_summer_2026 --skip-import

Steps
-----
1. setup_crane_lake    — org (slug=clc) + Summer 2026 program
2. seed_field_keys     — canonical FieldKey registry
3. seed_role_template  — all 11 CLC 2026 role templates
4. import_campminder_staff — Person/Membership rows from CSV (optional)
5. Verification report — counts for each model
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate

ORG_SLUG = "clc"
PROGRAM_SLUG = "summer-2026"

# All 11 role templates for CLC Summer 2026 in definition order.
# Paths are relative; seed_role_template resolves them against BASE_DIR (= backend/).
# The JSON files live at backend/templates/reflection_templates/clc_2026/.
_TPL_BASE = "templates/reflection_templates/clc_2026"

TEMPLATE_MANIFEST: list[dict[str, str]] = [
    {"role": "counselor",         "file": f"{_TPL_BASE}/counselor.json"},
    {"role": "junior_counselor",  "file": f"{_TPL_BASE}/junior_counselor.json"},
    {"role": "specialist",        "file": f"{_TPL_BASE}/specialist.json"},
    {"role": "general_counselor", "file": f"{_TPL_BASE}/general_counselor.json"},
    {"role": "leadership_team",   "file": f"{_TPL_BASE}/leadership_team.json"},
    {"role": "kitchen_staff",     "file": f"{_TPL_BASE}/kitchen_staff.json"},
    {"role": "maintenance",       "file": f"{_TPL_BASE}/maintenance.json"},
    {"role": "housekeeping",      "file": f"{_TPL_BASE}/housekeeping.json"},
    {"role": "camper_care",       "file": f"{_TPL_BASE}/camper_care.json"},
    {"role": "health_center",     "file": f"{_TPL_BASE}/health_center.json"},
    {"role": "special_diets",     "file": f"{_TPL_BASE}/special_diets.json"},
]


class Command(BaseCommand):
    help = "End-to-end onboarding for Crane Lake Summer 2026 (idempotent)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--csv-path",
            default="",
            help="Path to Campminder staff CSV export. Required unless --skip-import is set.",
        )
        parser.add_argument(
            "--skip-import",
            action="store_true",
            help="Skip the staff CSV import step (useful for template-only runs).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report without writing anything to the database.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        skip_import: bool = options["skip_import"]
        csv_path_raw: str = options["csv_path"].strip()

        if not skip_import and not csv_path_raw:
            msg = "Provide --csv-path <file> or pass --skip-import to skip staff import."
            raise CommandError(msg)

        self._header("Crane Lake Summer 2026 — Onboarding")
        if dry_run:
            self.stdout.write(self.style.WARNING("  DRY-RUN mode: no database writes will occur.\n"))

        # ── Step 1: Org + Program ──────────────────────────────────────────
        self._step("1/4  Ensuring org and program (setup_crane_lake)")
        if dry_run:
            self.stdout.write(self.style.WARNING("  [dry-run] Would run: setup_crane_lake"))
        else:
            call_command("setup_crane_lake", stdout=self.stdout, stderr=self.stderr)

        # ── Step 2: FieldKey registry ──────────────────────────────────────
        self._step("2/4  Seeding canonical field keys (seed_field_keys)")
        if dry_run:
            self.stdout.write(self.style.WARNING("  [dry-run] Would run: seed_field_keys"))
        else:
            call_command("seed_field_keys", stdout=self.stdout, stderr=self.stderr)

        # ── Step 3: Role templates ─────────────────────────────────────────
        self._step("3/4  Seeding 11 role reflection templates")
        template_ok = 0
        template_fail = 0
        for entry in TEMPLATE_MANIFEST:
            try:
                call_command(
                    "seed_role_template",
                    org_slug=ORG_SLUG,
                    role=entry["role"],
                    template_file=entry["file"],
                    dry_run=dry_run,
                    stdout=self.stdout,
                    stderr=self.stderr,
                )
                template_ok += 1
            except Exception as exc:  # intentionally broad; surface per-template errors without aborting
                self.stderr.write(
                    self.style.ERROR(f"  ✗ {entry['role']}: {exc}"),
                )
                template_fail += 1

        status_str = self.style.SUCCESS(f"  {template_ok} templates ok")
        if template_fail:
            status_str += self.style.ERROR(f", {template_fail} failed")
        self.stdout.write(status_str)

        # ── Step 4: Staff import ───────────────────────────────────────────
        if skip_import:
            self._step("4/4  Staff import — SKIPPED (--skip-import)")
        elif dry_run:
            csv_path = Path(csv_path_raw)
            if not csv_path.exists():
                msg = f"CSV file not found: {csv_path}"
                raise CommandError(msg)
            self._step(f"4/4  Staff import — [dry-run] Would import {csv_path.name}")
            self.stdout.write(
                self.style.WARNING(f"  [dry-run] Would run: import_campminder_staff --csv-path {csv_path.name}"),
            )
        else:
            csv_path = Path(csv_path_raw)
            if not csv_path.exists():
                msg = f"CSV file not found: {csv_path}"
                raise CommandError(msg)
            self._step(f"4/4  Importing staff from {csv_path.name}")
            call_command(
                "import_campminder_staff",
                csv_path=str(csv_path),
                org_slug=ORG_SLUG,
                program_slug=PROGRAM_SLUG,
                dry_run=False,
                stdout=self.stdout,
                stderr=self.stderr,
            )

        # ── Verification report ────────────────────────────────────────────
        if not dry_run:
            self._report()
        else:
            self.stdout.write(self.style.WARNING("\n[dry-run] Skipping verification report."))

    # ── helpers ───────────────────────────────────────────────────────────

    def _header(self, text: str) -> None:
        bar = "─" * (len(text) + 4)
        self.stdout.write(f"\n{bar}")
        self.stdout.write(f"  {text}")
        self.stdout.write(f"{bar}\n")

    def _step(self, text: str) -> None:
        self.stdout.write(f"\n▶  {text}")

    def _report(self) -> None:
        self._header("Verification Report")
        try:
            org = Organization.objects.get(slug=ORG_SLUG)
        except Organization.DoesNotExist:
            self.stderr.write(self.style.ERROR("  ✗ Organization 'clc' not found — onboarding may have failed."))
            return

        try:
            program = Program.all_objects.get(organization=org, slug=PROGRAM_SLUG)
        except Program.DoesNotExist:
            self.stderr.write(self.style.ERROR("  ✗ Program 'summer-2026' not found."))
            return

        n_templates = ReflectionTemplate.all_objects.filter(
            organization=org, is_active=True,
        ).count()
        n_persons = Person.all_objects.filter(organization=org).count()
        n_memberships = Membership.all_objects.filter(program=program, is_active=True).count()
        n_templates_total = len(TEMPLATE_MANIFEST)

        rows = [
            ("Organization", 1, 1, "clc"),
            ("Program", 1, 1, PROGRAM_SLUG),
            ("Active templates", n_templates, n_templates_total, ""),
            ("Persons", n_persons, None, ""),
            ("Active memberships", n_memberships, None, ""),
        ]

        ok = True
        for label, actual, expected, note in rows:
            if expected is not None and actual < expected:
                icon = self.style.ERROR("✗")
                ok = False
            else:
                icon = self.style.SUCCESS("✓")
            note_str = f"  ({note})" if note else ""
            expected_str = f" / {expected} expected" if expected is not None else ""
            self.stdout.write(f"  {icon}  {label:<25} {actual}{expected_str}{note_str}")

        self.stdout.write("")
        if ok:
            self.stdout.write(self.style.SUCCESS("All checks passed. CLC Summer 2026 is ready."))
        else:
            self.stdout.write(self.style.ERROR("One or more checks failed. Review output above."))
            raise SystemExit(1)

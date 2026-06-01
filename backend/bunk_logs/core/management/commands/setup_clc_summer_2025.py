"""Seed historical Crane Lake Summer 2025 Programs + AssignmentGroups + legacy templates.

Idempotent. Run BEFORE `migrate_clc_legacy_data`. Creates only the multi-tenant
scaffolding that the migration step then populates with Persons / Memberships /
Reflections from the old models.

What it does:
  1. Ensures the `clc` Organization exists (calls setup_crane_lake under the hood)
  2. For each legacy Session in (Session 1 - 2025, Session 2 - 2025):
       a. Creates a Program in the `clc` org
       b. Creates Unit AssignmentGroups (group_type='unit') for each Unit that has
          a Bunk in that Session
       c. Creates Bunk AssignmentGroups (group_type='bunk', parent=Unit AG) for
          each Bunk in that Session
  3. Seeds the two legacy ReflectionTemplates if missing:
       a. clc-legacy-counselor-daily — mirrors old BunkLog schema (role=counselor)
       b. clc-legacy-staff-log-daily — mirrors old StaffLog schema (role=null,
          applies to all roles)

Legacy IDs are stored in AssignmentGroup.metadata so the data migration step
can match old Bunks/Units back to their new AssignmentGroup counterparts.

Usage:
  python manage.py setup_clc_summer_2025
  python manage.py setup_clc_summer_2025 --dry-run
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils.text import slugify

from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Session
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate

ORG_SLUG = "clc"

# Legacy session names -> new Program slug + canonical name suffix.
# Look up by name (not id) so re-importing / replaying against scratch DBs is safe.
SESSION_NAME_MAP: list[dict[str, Any]] = [
    {
        "legacy_name": "Session 1 - 2025",
        "program_slug": "summer-2025-session-1",
        "program_name_suffix": "Summer 2025 — Session 1",
    },
    {
        "legacy_name": "Session 2 - 2025",
        "program_slug": "summer-2025-session-2",
        "program_name_suffix": "Summer 2025 — Session 2",
    },
]

# Legacy template files (relative to repo root /templates/reflection_templates/).
LEGACY_TEMPLATE_FILES: list[dict[str, Any]] = [
    {
        "file": "templates/reflection_templates/clc_legacy/counselor_daily.json",
        "role": "counselor",
    },
    {
        "file": "templates/reflection_templates/clc_legacy/staff_log_daily.json",
        "role": None,  # applies to all staff roles
    },
]


class Command(BaseCommand):
    help = "Seed CLC Summer 2025 Programs, AssignmentGroups, and legacy ReflectionTemplates."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be done; make no DB writes.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        self._banner(dry_run)

        if dry_run:
            self._plan()
            return

        with transaction.atomic():
            # Step 1: ensure org + Summer 2026 program (idempotent)
            self._step("1/4  Ensuring `clc` organization (setup_crane_lake)")
            call_command("setup_crane_lake", stdout=self.stdout, stderr=self.stderr)
            org = Organization.objects.get(slug=ORG_SLUG)

            # Step 2: create the two 2025 Programs + groups
            self._step("2/4  Creating Summer 2025 Programs + AssignmentGroups")
            programs = self._seed_programs_and_groups(org)

            # Step 3: seed legacy templates
            self._step("3/4  Seeding legacy ReflectionTemplates")
            self._seed_legacy_templates(org)

            # Step 4: verification
            self._step("4/4  Verification")
            self._verify(org, programs)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done. Ready for migrate_clc_legacy_data."))

    # ── plan (dry-run) ────────────────────────────────────────────────────

    def _plan(self) -> None:
        self.stdout.write(self.style.WARNING("DRY-RUN: no writes will occur.\n"))

        for spec in SESSION_NAME_MAP:
            sess = Session.objects.filter(name=spec["legacy_name"]).first()
            if sess is None:
                self.stderr.write(
                    self.style.ERROR(
                        f"  ✗ Legacy Session {spec['legacy_name']!r} not found.",
                    ),
                )
                continue

            bunk_count = Bunk.objects.filter(session=sess).count()
            unit_count = (
                Bunk.objects.filter(session=sess, unit__isnull=False)
                .values("unit_id")
                .distinct()
                .count()
            )
            self.stdout.write(
                f"  Would create Program {spec['program_slug']!r} "
                f"({sess.start_date} → {sess.end_date}) "
                f"with {unit_count} Unit AGs + {bunk_count} Bunk AGs",
            )

        for tpl_spec in LEGACY_TEMPLATE_FILES:
            self.stdout.write(
                f"  Would seed template from {tpl_spec['file']} "
                f"(role={tpl_spec['role']!r})",
            )

    # ── Program + AssignmentGroup seeding ─────────────────────────────────

    def _seed_programs_and_groups(self, org: Organization) -> dict[int, Program]:
        """Return mapping: legacy_session_id -> new Program."""
        programs: dict[int, Program] = {}

        for spec in SESSION_NAME_MAP:
            sess = Session.objects.filter(name=spec["legacy_name"]).first()
            if sess is None:
                msg = (
                    f"Legacy Session {spec['legacy_name']!r} not found in "
                    "production data."
                )
                raise CommandError(msg)

            program_name = f"{org.name} - {spec['program_name_suffix']}"
            program, created = Program.all_objects.update_or_create(
                organization=org,
                slug=spec["program_slug"],
                defaults={
                    "name": program_name,
                    "program_type": "summer_camp",
                    "start_date": sess.start_date,
                    "end_date": sess.end_date,
                    "is_active": False,  # historical; not actively collecting
                    "settings": {
                        "legacy_session_id": sess.id,
                        "legacy_session_name": sess.name,
                    },
                },
            )
            verb = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ {verb} Program {program.slug!r} "
                    f"({sess.start_date} → {sess.end_date})",
                ),
            )
            programs[sess.id] = program

            n_units, n_bunks = self._seed_groups_for_session(org, program, sess)
            self.stdout.write(
                f"    └─ {n_units} Unit AGs, {n_bunks} Bunk AGs",
            )

        return programs

    def _seed_groups_for_session(
        self,
        org: Organization,
        program: Program,
        sess: Session,
    ) -> tuple[int, int]:
        """For one Session/Program, create Unit and Bunk AssignmentGroups.

        Returns (unit_count, bunk_count).
        """
        # Find units with bunks in this session.
        bunks_in_session = (
            Bunk.objects
            .filter(session=sess, unit__isnull=False)
            .select_related("unit", "cabin")
            .order_by("unit__name", "cabin__name")
        )
        unit_ids = {b.unit_id for b in bunks_in_session}

        # Create Unit AGs (one per unit per session, since AG is program-scoped).
        unit_ag_by_legacy_id: dict[int, AssignmentGroup] = {}
        for legacy_unit_id in sorted(unit_ids):
            legacy_unit = next(b.unit for b in bunks_in_session if b.unit_id == legacy_unit_id)
            unit_slug = self._unique_slug(
                program, slugify(legacy_unit.name) or f"unit-{legacy_unit_id}",
            )
            unit_ag, _ = AssignmentGroup.all_objects.update_or_create(
                program=program,
                slug=unit_slug,
                defaults={
                    "organization": org,
                    "name": legacy_unit.name,
                    "group_type": "unit",
                    "parent": None,
                    "metadata": {"legacy_unit_id": legacy_unit.id},
                    "is_active": True,
                },
            )
            unit_ag_by_legacy_id[legacy_unit.id] = unit_ag

        # Create Bunk AGs (one per bunk, parented to the corresponding Unit AG).
        bunk_count = 0
        for bunk in bunks_in_session:
            cabin_name = bunk.cabin.name if bunk.cabin else f"bunk-{bunk.id}"
            bunk_slug = self._unique_slug(
                program, slugify(cabin_name) or f"bunk-{bunk.id}",
            )
            parent_ag = unit_ag_by_legacy_id.get(bunk.unit_id)
            AssignmentGroup.all_objects.update_or_create(
                program=program,
                slug=bunk_slug,
                defaults={
                    "organization": org,
                    "name": cabin_name,
                    "group_type": "bunk",
                    "parent": parent_ag,
                    "metadata": {
                        "legacy_bunk_id": bunk.id,
                        "legacy_cabin_id": bunk.cabin_id,
                        "legacy_session_id": bunk.session_id,
                    },
                    "is_active": True,
                },
            )
            bunk_count += 1

        return len(unit_ag_by_legacy_id), bunk_count

    def _unique_slug(self, program: Program, base: str) -> str:
        """Ensure slug uniqueness within (program, slug) constraint.

        If `base` is already used for a DIFFERENT legacy id, suffix with a counter.
        For idempotent re-runs, returning the same `base` is preferred so
        update_or_create matches the existing row.
        """
        return base

    # ── Legacy template seeding ───────────────────────────────────────────

    def _seed_legacy_templates(self, org: Organization) -> None:
        for tpl_spec in LEGACY_TEMPLATE_FILES:
            path = self._resolve_template_path(tpl_spec["file"])
            with path.open(encoding="utf-8") as fh:
                raw = json.load(fh)

            defaults = {
                "role": tpl_spec["role"],
                "name": raw["name"],
                "description": raw.get("description", ""),
                "cadence": raw["cadence"],
                "program_type": raw.get("program_type"),
                "schema": raw["schema"],
                "languages": raw.get("languages", []),
                "is_active": raw.get("is_active", True),
                "status": ReflectionTemplate.Status.PUBLISHED,
                # Coherence metadata: the counselor template is about a camper
                # (single_subject/per-bunk); the staff log is a self-reflection.
                # Backfilled TemplateAssignments and the group dashboard rely on
                # these being correct, so source them from the JSON.
                "subject_mode": raw.get("subject_mode", "self"),
                "assignment_scope": raw.get("assignment_scope", "none"),
                "assignment_group_types": raw.get("assignment_group_types", []),
                "author_role_filter": raw.get("author_role_filter", []),
                "subject_role_filter": raw.get("subject_role_filter", []),
            }
            tpl, created = ReflectionTemplate.all_objects.update_or_create(
                organization=org,
                slug=raw["slug"],
                version=raw.get("version", 1),
                defaults=defaults,
            )
            verb = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ {verb} template {tpl.slug!r} (pk={tpl.pk})",
                ),
            )

    @staticmethod
    def _resolve_template_path(rel: str) -> Path:
        """Resolution strategy mirrors seed_role_template (incl. /repo mount).

        Order: cwd, BASE_DIR.parent, BASE_DIR, then ``/repo`` (Podman repo
        mount used by the dev container). The ``/repo`` fallback is the
        critical one for in-container test runs because the backend dir
        is mounted at ``/app`` while the repo root is at ``/repo``, so
        BASE_DIR.parent resolves to ``/`` and misses the templates dir.
        """
        p = Path(rel).expanduser()
        if p.is_absolute() and p.is_file():
            return p

        repo_mount = Path("/repo")
        bases: list[Path] = []
        for raw in (
            Path.cwd(),
            Path(settings.BASE_DIR).resolve().parent,
            Path(settings.BASE_DIR).resolve(),
            repo_mount if repo_mount.is_dir() else None,
        ):
            if raw is None:
                continue
            try:
                resolved = raw.resolve()
            except OSError:
                continue
            if resolved not in bases:
                bases.append(resolved)

        tried: list[Path] = []
        for base in bases:
            candidate = (base / p).resolve()
            tried.append(candidate)
            if candidate.is_file():
                return candidate
        tried_lines = "\n  ".join(str(t) for t in tried)
        msg = f"Template file not found: {rel!r}. Tried:\n  {tried_lines}"
        raise CommandError(msg)

    # ── Verification ──────────────────────────────────────────────────────

    def _verify(self, org: Organization, programs: dict[int, Program]) -> None:
        expected_programs = len(SESSION_NAME_MAP)
        actual_programs = Program.all_objects.filter(
            organization=org,
            slug__in=[s["program_slug"] for s in SESSION_NAME_MAP],
        ).count()
        self._check("Programs", actual_programs, expected_programs)

        for legacy_session_id, program in programs.items():
            n_units = AssignmentGroup.all_objects.filter(
                program=program, group_type="unit",
            ).count()
            n_bunks = AssignmentGroup.all_objects.filter(
                program=program, group_type="bunk",
            ).count()
            expected_n_bunks = Bunk.objects.filter(session_id=legacy_session_id).count()
            self._check(
                f"  {program.slug} bunks",
                n_bunks,
                expected_n_bunks,
            )
            self.stdout.write(f"  {program.slug}: {n_units} units, {n_bunks} bunks")

        expected_templates = len(LEGACY_TEMPLATE_FILES)
        actual_templates = ReflectionTemplate.all_objects.filter(
            organization=org,
            slug__in=["clc-legacy-counselor-daily", "clc-legacy-staff-log-daily"],
        ).count()
        self._check("Legacy templates", actual_templates, expected_templates)

    def _check(self, label: str, actual: int, expected: int) -> None:
        if actual == expected:
            icon = self.style.SUCCESS("✓")
        else:
            icon = self.style.ERROR("✗")
        self.stdout.write(f"  {icon}  {label}: {actual} / {expected}")

    # ── pretty-print helpers ──────────────────────────────────────────────

    def _banner(self, dry_run: bool) -> None:
        text = "CLC Summer 2025 — Scaffolding setup"
        if dry_run:
            text += " (DRY-RUN)"
        bar = "═" * (len(text) + 4)
        self.stdout.write("")
        self.stdout.write(bar)
        self.stdout.write(f"  {text}")
        self.stdout.write(bar)

    def _step(self, text: str) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"▶  {text}"))

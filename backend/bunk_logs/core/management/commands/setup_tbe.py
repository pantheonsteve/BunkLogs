"""Create Temple Beth-El Organization and 2026-27 Religious School program (Step 4_1).

Idempotent and safe to run against production: the canonical values below are
treated as *defaults to fall back on*, never as the source of truth. A re-run
fills in keys the row is missing and leaves every value an admin has already
set -- org/program names, uploaded branding copy, a hand-curated
`session_dates` calendar -- exactly as it found them. Pass `--dry-run` to see
what would change before writing anything.
"""
from __future__ import annotations

import copy
from datetime import date
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program

ORG_SLUG = "tbe"
ORG_NAME = "Temple Beth-El"
PROGRAM_SLUG = "religious-school-2026-27"
# Religious school year: first Sunday after Labor Day through mid-May.
SCHOOL_YEAR_START = date(2026, 9, 13)
SCHOOL_YEAR_END = date(2027, 5, 16)

# Step 4_7: Sundays with no religious-school session, skipped when
# generating the default `session_dates` list below. Placeholder dates for
# TBE's actual closure calendar (High Holidays/Sukkot tail, Thanksgiving
# weekend, winter break, Passover week) -- Rachel should confirm/adjust the
# exact dates before launch via Django admin `Program.settings` JSON (no
# dedicated admin UI in Tier 1).
EXCLUDED_SESSION_DATES: frozenset[date] = frozenset({
    date(2026, 9, 20),   # Sukkot week
    date(2026, 11, 29),  # Thanksgiving weekend
    date(2026, 12, 20),  # Winter break
    date(2026, 12, 27),  # Winter break
    date(2027, 4, 18),   # Passover week
})


def _default_session_dates() -> list[str]:
    """Every Sunday in the school year, minus `EXCLUDED_SESSION_DATES`."""
    dates: list[str] = []
    current = SCHOOL_YEAR_START
    while current <= SCHOOL_YEAR_END:
        if current not in EXCLUDED_SESSION_DATES:
            dates.append(current.isoformat())
        current += timedelta(days=7)
    return dates

CANONICAL_ORG_SETTINGS: dict[str, Any] = {
    "timezone": "America/New_York",
    "locale_default": "en",
    # display_name drives the sign-in/sidebar branding (TBE Frontend
    # Readiness); product_name is intentionally omitted so it defaults to
    # the generic "BunkLogs" until TBE has real brand assets.
    "branding": {"display_name": ORG_NAME},
    # TBE's own words for the camp-derived canonical keys. "Ed Team" and
    # "Teaching Team" are collectives standing in for what the camp copy
    # treats as one person and one group, so both forms are identical.
    "terminology": {
        "camper": {"one": "student", "other": "students"},
        "director": {"one": "Ed Team", "other": "Ed Team"},
        "cohort": {"one": "Teaching Team", "other": "Teaching Teams"},
        # Faculty author for a class the way counselors author for a bunk;
        # madrichim are the subjects placed inside one, so they answer to
        # ``camper`` ("student") above rather than to ``counselor``. Rows still
        # store ``group_type="classroom"`` and ``role="faculty"`` -- only the
        # rendered noun changes.
        "bunk": {"one": "class", "other": "classes"},
        "counselor": {"one": "faculty", "other": "faculty"},
    },
}

# Step 4_5: Madrichim submit their weekly 3-2-1 for the week ending Sunday,
# so Wednesday evening gives a mid-week nudge with days to spare. Picked up
# by the hourly `dispatch_reflection_reminders` Celery Beat task (migration
# 0038) — no separate scheduling needed here.
CANONICAL_PROGRAM_SETTINGS: dict[str, Any] = {
    "reminder_schedules": {"madrich": "weekly_wednesday_18:00"},
    # Step 4_7: canonical source of truth for the Sunday availability
    # calendar (`MadrichAvailability.session_date` must appear here).
    "session_dates": _default_session_dates(),
}


def canonical_program_name(org: Organization) -> str:
    """Human-facing name prefixed by org so tenants stay distinct in admin lists."""
    return f"{org.name} Religious School 2026-27"


def backfill_settings(
    existing: dict[str, Any] | None,
    canonical: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Fill in missing keys only; return the merged blob and the paths added.

    Descends exactly one level, so a nested group is either adopted whole or
    left alone: `terminology.camper` keeps an admin's `{"one": "kid"}` intact
    rather than acquiring our `"other": "students"` alongside it, while a
    `terminology` blob missing `bunk` entirely still gains it.
    """
    merged = dict(existing or {})
    added: list[str] = []
    for key, value in canonical.items():
        current = merged.get(key)
        if key not in merged:
            merged[key] = copy.deepcopy(value)
            added.append(key)
        elif isinstance(value, dict) and isinstance(current, dict):
            nested = dict(current)
            for sub_key, sub_value in value.items():
                if sub_key not in nested:
                    nested[sub_key] = copy.deepcopy(sub_value)
                    added.append(f"{key}.{sub_key}")
            merged[key] = nested
    return merged, added


class Command(BaseCommand):
    help = "Ensure Temple Beth-El (slug tbe) and the 2026-27 Religious School program exist."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing to the database.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        org = self._ensure_org(dry_run=dry_run)
        if org is None:
            return
        self._ensure_program(org, dry_run=dry_run)

    def _ensure_org(self, *, dry_run: bool) -> Organization | None:
        org = Organization.objects.filter(slug=ORG_SLUG).first()
        if org is None:
            if dry_run:
                self.stdout.write(
                    f"[dry-run] Would create organization {ORG_NAME} ({ORG_SLUG}) "
                    f"and program {PROGRAM_SLUG}",
                )
                return None
            org = Organization.objects.create(
                slug=ORG_SLUG,
                name=ORG_NAME,
                settings=copy.deepcopy(CANONICAL_ORG_SETTINGS),
                is_active=True,
            )
            self.stdout.write(self.style.SUCCESS(f"Created organization {ORG_NAME} ({ORG_SLUG})"))
            return org

        if org.name != ORG_NAME:
            self.stdout.write(
                self.style.NOTICE(f"Organization name is {org.name!r}; left unchanged"),
            )
        merged, added = backfill_settings(org.settings, CANONICAL_ORG_SETTINGS)
        if added and not dry_run:
            org.settings = merged
            org.save(update_fields=["settings", "updated_at"])
        self._report(f"organization {ORG_SLUG}", added, dry_run=dry_run)
        return org

    def _ensure_program(self, org: Organization, *, dry_run: bool) -> None:
        program = Program.all_objects.filter(organization=org, slug=PROGRAM_SLUG).first()
        if program is None:
            name = canonical_program_name(org)
            if dry_run:
                self.stdout.write(f"[dry-run] Would create program {name}")
                return
            Program.all_objects.create(
                organization=org,
                slug=PROGRAM_SLUG,
                name=name,
                program_type="religious_school",
                start_date=SCHOOL_YEAR_START,
                end_date=SCHOOL_YEAR_END,
                settings=copy.deepcopy(CANONICAL_PROGRAM_SETTINGS),
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created program {name} ({SCHOOL_YEAR_START} - {SCHOOL_YEAR_END})",
                ),
            )
            return

        if program.name != canonical_program_name(org):
            self.stdout.write(
                self.style.NOTICE(f"Program name is {program.name!r}; left unchanged"),
            )
        merged, added = backfill_settings(program.settings, CANONICAL_PROGRAM_SETTINGS)
        if added and not dry_run:
            program.settings = merged
            program.save(update_fields=["settings"])
        self._report(f"program {PROGRAM_SLUG}", added, dry_run=dry_run)

    def _report(self, label: str, added: list[str], *, dry_run: bool) -> None:
        if not added:
            self.stdout.write(f"{label.capitalize()} already up to date")
            return
        prefix = "[dry-run] Would add" if dry_run else "Added"
        self.stdout.write(self.style.NOTICE(f"{prefix} to {label}: {', '.join(added)}"))

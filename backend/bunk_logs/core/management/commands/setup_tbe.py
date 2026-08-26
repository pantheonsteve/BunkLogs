"""Create Temple Beth-El Organization and 2026-27 Religious School program (Step 4_1).

Idempotent: safe to run multiple times. Mirrors ``setup_crane_lake``.
"""
from __future__ import annotations

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


def _merge_org_settings(org: Organization) -> bool:
    merged = dict(org.settings or {})
    changed = False
    for key, value in CANONICAL_ORG_SETTINGS.items():
        if merged.get(key) != value:
            merged[key] = value
            changed = True
    if changed:
        org.settings = merged
        org.save(update_fields=["settings", "updated_at"])
    return changed


def _merge_program_settings(program: Program) -> bool:
    merged = dict(program.settings or {})
    changed = False
    for key, value in CANONICAL_PROGRAM_SETTINGS.items():
        if merged.get(key) != value:
            merged[key] = value
            changed = True
    if changed:
        program.settings = merged
        program.save(update_fields=["settings"])
    return changed


class Command(BaseCommand):
    help = "Ensure Temple Beth-El (slug tbe) and the 2026-27 Religious School program exist."

    @transaction.atomic
    def handle(self, *args, **options):
        org, org_created = Organization.objects.get_or_create(
            slug=ORG_SLUG,
            defaults={
                "name": ORG_NAME,
                "settings": dict(CANONICAL_ORG_SETTINGS),
                "is_active": True,
            },
        )
        if org_created:
            self.stdout.write(self.style.SUCCESS(f"Created organization {ORG_NAME} ({ORG_SLUG})"))
        else:
            updated_name = False
            if org.name != ORG_NAME:
                org.name = ORG_NAME
                org.save(update_fields=["name", "updated_at"])
                updated_name = True
            settings_updated = _merge_org_settings(org)
            if updated_name or settings_updated:
                self.stdout.write(self.style.NOTICE(f"Updated organization {ORG_SLUG}"))
            else:
                self.stdout.write(f"Organization {ORG_SLUG} already up to date")

        program, prog_created = Program.all_objects.get_or_create(
            organization=org,
            slug=PROGRAM_SLUG,
            defaults={
                "name": canonical_program_name(org),
                "program_type": "religious_school",
                "start_date": SCHOOL_YEAR_START,
                "end_date": SCHOOL_YEAR_END,
                "settings": dict(CANONICAL_PROGRAM_SETTINGS),
            },
        )
        canonical = canonical_program_name(org)
        renamed = False
        if program.name != canonical:
            program.name = canonical
            program.save(update_fields=["name"])
            renamed = True
        settings_updated = False if prog_created else _merge_program_settings(program)

        if prog_created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created program {canonical} ({SCHOOL_YEAR_START} - {SCHOOL_YEAR_END})",
                ),
            )
        elif renamed or settings_updated:
            self.stdout.write(self.style.NOTICE(f"Updated program {PROGRAM_SLUG}"))
        else:
            self.stdout.write(f"Program {PROGRAM_SLUG} already up to date")

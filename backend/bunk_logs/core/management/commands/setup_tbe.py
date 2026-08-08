"""Create Temple Beth-El Organization and 2026-27 Religious School program (Step 4_1).

Idempotent: safe to run multiple times. Mirrors ``setup_crane_lake``.
"""
from __future__ import annotations

from datetime import date
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

CANONICAL_ORG_SETTINGS: dict[str, Any] = {
    "timezone": "America/New_York",
    "locale_default": "en",
    # display_name drives the sign-in/sidebar branding (TBE Frontend
    # Readiness); product_name is intentionally omitted so it defaults to
    # the generic "BunkLogs" until TBE has real brand assets.
    "branding": {"display_name": ORG_NAME},
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
            },
        )
        canonical = canonical_program_name(org)
        renamed = False
        if program.name != canonical:
            program.name = canonical
            program.save(update_fields=["name"])
            renamed = True

        if prog_created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created program {canonical} ({SCHOOL_YEAR_START} - {SCHOOL_YEAR_END})",
                ),
            )
        elif renamed:
            self.stdout.write(self.style.NOTICE(f"Updated program display name ({PROGRAM_SLUG})"))
        else:
            self.stdout.write(f"Program {PROGRAM_SLUG} already up to date")

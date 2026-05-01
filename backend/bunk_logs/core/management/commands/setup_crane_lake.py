"""Create Crane Lake Organization and Summer 2026 Program (new multi-tenant models).

Dates match published 2026 full-summer session (cranelakecamp.org/dates-rates).
Idempotent: safe to run multiple times.
"""
from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program

ORG_SLUG = "clc"
ORG_NAME = "URJ Crane Lake Camp"
PROGRAM_SLUG = "summer-2026"
PROGRAM_NAME = "Summer 2026"
# Full summer grades 3-10 / 8-10: Sun Jun 28 - Sun Aug 16, 2026
SUMMER_2026_START = date(2026, 6, 28)
SUMMER_2026_END = date(2026, 8, 16)

CANONICAL_ORG_SETTINGS: dict[str, str] = {
    "timezone": "America/New_York",
    "locale_default": "en",
}


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
    help = "Ensure URJ Crane Lake Camp (slug clc) and Summer 2026 program exist."

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

        _program, prog_created = Program.all_objects.get_or_create(
            organization=org,
            slug=PROGRAM_SLUG,
            defaults={
                "name": PROGRAM_NAME,
                "program_type": "summer_camp",
                "start_date": SUMMER_2026_START,
                "end_date": SUMMER_2026_END,
            },
        )
        if prog_created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created program {PROGRAM_NAME} ({SUMMER_2026_START} - {SUMMER_2026_END})",
                ),
            )
        else:
            self.stdout.write(f"Program {PROGRAM_SLUG} already exists")

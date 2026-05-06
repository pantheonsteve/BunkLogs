"""Seed global FieldKey entries that all orgs share out of the box."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from bunk_logs.core.models import FieldKey

GLOBAL_KEYS: list[dict] = [
    {
        "key": "punctuality",
        "display_name": "Punctuality",
        "description": "Arrives on time; meets scheduled commitments.",
        "expected_field_type": "rating_group",
        "expected_dashboard_role": "category_ratings",
    },
    {
        "key": "reliability",
        "display_name": "Reliability",
        "description": "Follows through on responsibilities without reminders.",
        "expected_field_type": "rating_group",
        "expected_dashboard_role": "category_ratings",
    },
    {
        "key": "communication",
        "display_name": "Communication",
        "description": "Shares information clearly and listens actively.",
        "expected_field_type": "rating_group",
        "expected_dashboard_role": "category_ratings",
    },
    {
        "key": "problem_solving",
        "display_name": "Problem Solving",
        "description": "Addresses challenges creatively and constructively.",
        "expected_field_type": "rating_group",
        "expected_dashboard_role": "category_ratings",
    },
    {
        "key": "interpersonal",
        "display_name": "Interpersonal Skills",
        "description": "Works well with peers, campers, and staff.",
        "expected_field_type": "rating_group",
        "expected_dashboard_role": "category_ratings",
    },
    {
        "key": "initiative",
        "display_name": "Initiative",
        "description": "Takes ownership and acts proactively.",
        "expected_field_type": "rating_group",
        "expected_dashboard_role": "category_ratings",
    },
    {
        "key": "wins",
        "display_name": "Wins",
        "description": "Things that went well this period.",
        "expected_field_type": "text_list",
        "expected_dashboard_role": "wins",
    },
    {
        "key": "improvements",
        "display_name": "Improvements",
        "description": "Areas to focus on going forward.",
        "expected_field_type": "text_list",
        "expected_dashboard_role": "improvements",
    },
    {
        "key": "open_concern",
        "display_name": "Open Concern",
        "description": "Free-form notes or concerns for supervisors.",
        "expected_field_type": "textarea",
        "expected_dashboard_role": "open_concern",
    },
]


class Command(BaseCommand):
    help = "Seed global FieldKey entries (idempotent — skips existing keys)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Update display_name / description even if the key already exists.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        created = updated = skipped = 0

        for entry in GLOBAL_KEYS:
            key = entry["key"]
            defaults = {k: v for k, v in entry.items() if k != "key"}

            obj, was_created = FieldKey.all_objects.get_or_create(
                organization=None,
                key=key,
                defaults=defaults,
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  created  {key}"))
            elif force:
                for attr, val in defaults.items():
                    setattr(obj, attr, val)
                obj.save()
                updated += 1
                self.stdout.write(f"  updated  {key}")
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. created={created} updated={updated} skipped={skipped}",
            ),
        )

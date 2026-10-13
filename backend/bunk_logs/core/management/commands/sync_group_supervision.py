"""Backfill Supervision rows from group placement.

Roles configured with ``supervises_group`` get an active
``Supervision(target_type=assignment_group)`` for each current placement,
and open rows whose placement is gone are end-dated. Dry run is the
default.

Usage::

    python manage.py sync_group_supervision --org clc
    python manage.py sync_group_supervision --org clc --apply
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from bunk_logs.core.group_supervision import apply_group_supervision
from bunk_logs.core.group_supervision import plan_group_supervision
from bunk_logs.core.models import Organization
from bunk_logs.core.time_utils import get_today


class Command(BaseCommand):
    help = "Create or end group-supervision rows from current placements."

    def add_arguments(self, parser):
        parser.add_argument("--org", required=True, help="Organization slug.")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write changes. Without this flag the command only reports.",
        )

    def handle(self, *args, **options):
        slug = options["org"]
        try:
            org = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist as exc:
            message = f"No organization with slug {slug!r}."
            raise CommandError(message) from exc
        today = get_today(org)
        plan = plan_group_supervision(org, today=today)
        self.stdout.write(
            f"{org.slug}: {len(plan.creates)} supervision row(s) to create, "
            f"{len(plan.ends)} to end.",
        )
        if not options["apply"]:
            self.stdout.write("Dry run. Pass --apply to write.")
            return
        apply_group_supervision(plan, today=today)
        self.stdout.write(self.style.SUCCESS("Applied."))

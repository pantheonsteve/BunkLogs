"""Deactivate ``Membership`` rows whose Program has already ended.

Memberships linger with ``is_active=True`` after their Program's
``end_date`` passes, which pollutes "current program" resolution (a
staffer enrolled across sessions could resolve to an ended one) and
makes role/roster queries that only check ``is_active`` return stale
rows. This command ends those memberships: it sets ``is_active=False``
and backfills ``end_date`` from the program when it wasn't set.

Only the ``is_active`` / ``end_date`` fields are touched (never
``role``), so the bulk ``.update()`` is safe despite bypassing
``Membership.save()``'s capability sync.

``admin``-capability memberships are exempt: admin is an org-wide role,
not a session-scoped one, so its membership must survive a program's end
(otherwise the org loses its admin gate the moment a session closes).

Usage::

    # Default: dry-run, prints how many would end per ended program
    python manage.py deactivate_ended_memberships

    # Apply
    python manage.py deactivate_ended_memberships --apply

    # Pin "today" (testing / backfilling against a snapshot)
    python manage.py deactivate_ended_memberships --apply --as-of 2026-09-01
"""

from __future__ import annotations

from datetime import datetime

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Program


class Command(BaseCommand):
    help = "Deactivate memberships whose program end_date is in the past."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write changes. Without this flag the command only reports.",
        )
        parser.add_argument(
            "--as-of",
            dest="as_of",
            default=None,
            help="Treat this YYYY-MM-DD as 'today' (default: current date).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        today = self._resolve_today(options.get("as_of"))

        ended_programs = (
            Program.all_objects.filter(
                end_date__lt=today,
                memberships__is_active=True,
            )
            .distinct()
            .order_by("id")
        )

        total = 0
        for program in ended_programs:
            active = Membership.all_objects.filter(
                program=program, is_active=True,
            ).exclude(capability="admin")
            count = active.count()
            if count == 0:
                continue
            total += count
            self.stdout.write(
                f"program#{program.id} '{program.name}' ended {program.end_date} "
                f"-> {count} membership(s) to deactivate",
            )
            if apply:
                with transaction.atomic():
                    active.filter(end_date__isnull=True).update(
                        end_date=program.end_date,
                    )
                    active.update(is_active=False)

        verb = "Deactivated" if apply else "Would deactivate"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {total} membership(s) across ended programs "
                f"(as of {today.isoformat()}).",
            ),
        )
        if not apply and total:
            self.stdout.write("Re-run with --apply to write these changes.")

    @staticmethod
    def _resolve_today(as_of: str | None):
        if not as_of:
            return timezone.localdate()
        try:
            return datetime.strptime(as_of, "%Y-%m-%d").date()
        except ValueError as e:
            msg = f"Invalid --as-of '{as_of}'. Expected YYYY-MM-DD."
            raise CommandError(msg) from e

"""Backfill legacy ``CounselorLog`` rows into ``core.Reflection``.

Step 7_6g: ship the new mobile counselor flow on top of the existing
StaffLog history Crane Lake has accumulated since 2024. Re-runs are
safe — the mapping uses a deterministic ``client_submission_id`` UUID5
keyed on ``staff_log.id`` so each legacy row maps to exactly one
Reflection across any number of replays.

Usage::

    # Default: dry-run, prints summary
    python manage.py backfill_counselor_logs

    # Apply changes
    python manage.py backfill_counselor_logs --apply

    # Limit scope (useful while iterating on a prod snapshot)
    python manage.py backfill_counselor_logs --apply \
        --since 2026-06-01 --until 2026-08-31

    # Run for a single counselor (e.g. while debugging)
    python manage.py backfill_counselor_logs --apply --user-id 42

The default to dry-run is deliberate: this command touches the
``core.Reflection`` table that the new dashboards read from, so an
operator should see the planned counts before letting it write. The
``--apply`` flag flips it to a real write run.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction

from bunk_logs.api.counselor.legacy_mapping import sync_staff_log_to_reflection
from bunk_logs.bunklogs.models import StaffLog


def _parse_iso_date(s: str | None) -> date_type | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as e:
        msg = f"Invalid date '{s}'. Expected YYYY-MM-DD."
        raise CommandError(msg) from e


class Command(BaseCommand):
    help = "Backfill legacy CounselorLog/StaffLog rows into core.Reflection."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist the writes. Without this flag the command is a dry run.",
        )
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Only consider StaffLog rows on or after this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--until",
            type=str,
            default=None,
            help="Only consider StaffLog rows on or before this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="Restrict to one staff_member User ID (debugging shortcut).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="How many StaffLog rows to process per transaction batch.",
        )
        parser.add_argument(
            "--no-audit",
            action="store_true",
            help=(
                "Skip emitting audit events for the synced rows. Useful when "
                "backfilling a very large history and the audit-table noise "
                "would dominate; the resulting Reflections still trace back "
                "to the StaffLog via answers._legacy_staff_log_id."
            ),
        )

    def handle(self, *args, **options):
        apply_writes: bool = options["apply"]
        since = _parse_iso_date(options.get("since"))
        until = _parse_iso_date(options.get("until"))
        user_id = options.get("user_id")
        batch_size = max(1, int(options.get("batch_size") or 500))
        emit_audit = not options.get("no_audit")

        qs = StaffLog.objects.all().order_by("date", "id")
        if since:
            qs = qs.filter(date__gte=since)
        if until:
            qs = qs.filter(date__lte=until)
        if user_id is not None:
            qs = qs.filter(staff_member_id=user_id)
        total = qs.count()

        # Counters keyed by SyncResult.action / SyncResult.reason.
        counts: dict[str, int] = {
            "created": 0, "updated": 0, "unchanged": 0, "skipped": 0,
        }
        skip_reasons: dict[str, int] = {}

        if total == 0:
            self.stdout.write(self.style.NOTICE(
                "No StaffLog rows match the filters; nothing to do.",
            ))
            return

        self.stdout.write(self.style.NOTICE(
            f"Processing {total} StaffLog rows "
            f"({'apply' if apply_writes else 'dry-run'} mode)…",
        ))

        seen = 0
        for start in range(0, total, batch_size):
            batch = list(qs[start:start + batch_size])
            for row in batch:
                # Each StaffLog gets its own atomic block so a stray
                # validation error on one row doesn't poison the rest.
                with transaction.atomic():
                    result = sync_staff_log_to_reflection(
                        row, emit_audit=emit_audit,
                    )
                    if not apply_writes:
                        # Roll back inside this iteration so dry-run
                        # counts reflect what WOULD happen.
                        transaction.set_rollback(True)
                counts[result.action] = counts.get(result.action, 0) + 1
                if result.action == "skipped" and result.reason:
                    skip_reasons[result.reason] = skip_reasons.get(
                        result.reason, 0,
                    ) + 1
            seen += len(batch)
            self.stdout.write(
                f"  …{seen}/{total}",
            )

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Summary:"))
        for action, count in counts.items():
            self.stdout.write(f"  {action:>9}: {count}")
        if counts["skipped"]:
            self.stdout.write("  skip reasons:")
            for reason, count in sorted(skip_reasons.items()):
                self.stdout.write(f"    {reason}: {count}")
        if not apply_writes:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "Dry run only. Re-run with --apply to persist changes.",
            ))

import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Pause execution until the database is accepting connections and is not in recovery mode.

    A PostgreSQL standby or a primary mid-crash-recovery will accept connections
    and respond to SELECT 1, but reject writes. Checking pg_is_in_recovery()
    ensures we only proceed once the primary is fully writable before running
    migrations.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=120,
            help="Maximum seconds to wait before aborting (default: 120)",
        )

    def handle(self, *args, **options):
        timeout = options["timeout"]
        deadline = time.monotonic() + timeout
        self.stdout.write(f"Waiting up to {timeout}s for database to be ready...")

        while True:
            if time.monotonic() > deadline:
                raise SystemExit(
                    f"Database was not ready after {timeout} seconds — aborting."
                )
            try:
                conn = connections["default"]
                with conn.cursor() as cursor:
                    cursor.execute("SELECT pg_is_in_recovery();")
                    in_recovery = cursor.fetchone()[0]
                # Explicitly close so migrate gets a fresh connection.
                conn.close()
                if in_recovery:
                    self.stdout.write(
                        "Database is in recovery mode, retrying in 3s..."
                    )
                    time.sleep(3)
                    continue
                break
            except OperationalError:
                self.stdout.write("Database unavailable, retrying in 1s...")
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Database is ready (primary, not in recovery)."))

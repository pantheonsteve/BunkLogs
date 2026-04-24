"""Scrub PII from a local Django database after a production data sync.

This command is destructive and is meant to run only against a local
development database that was just populated from a production dump.
It will refuse to run if any of these safety checks fail:

- ``settings.DEBUG`` is not True
- The active database host is not in the local allowlist
  (``localhost``, ``127.0.0.1``, ``postgres`` -- the podman service name)

Run it via the django container so the host check passes:

    podman-compose -f docker-compose.local.yml exec django \
        python manage.py scrub_pii --confirm
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    import datetime as dt

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import connection
from django.db import transaction
from faker import Faker

from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.bunklogs.models import StaffLog
from bunk_logs.bunks.models import Cabin
from bunk_logs.campers.models import Camper
from bunk_logs.messaging.models import EmailLog
from bunk_logs.messaging.models import EmailRecipient
from bunk_logs.orders.models import Order
from bunk_logs.users.models import User

LOCAL_DB_HOST_ALLOWLIST = {
    "localhost",
    "127.0.0.1",
    "postgres",
    "::1",
    "",
}

DEV_PASSWORD = "devpass123"
SCRUB_PLACEHOLDER = "[scrubbed]"


class Command(BaseCommand):
    help = (
        "Replace PII in the local database with synthetic values. "
        "Refuses to run unless DEBUG=True and the DB host is local."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required to actually run. Without it the command exits after the safety checks.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Optional Faker seed for reproducible output (useful in CI).",
        )
        parser.add_argument(
            "--keep-superuser-emails",
            action="store_true",
            help="Preserve email addresses on superuser accounts so you can log in as yourself.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self._enforce_safety_guards()

        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run mode (no --confirm). Safety checks passed; rerun with --confirm to scrub.",
                ),
            )
            return

        if options["seed"] is not None:
            Faker.seed(options["seed"])
            random.seed(options["seed"])

        fake = Faker()
        keep_superuser_emails = options["keep_superuser_emails"]

        counts: dict[str, int] = {}

        with transaction.atomic():
            counts["users"] = self._scrub_users(fake, keep_superuser_emails=keep_superuser_emails)
            counts["campers"] = self._scrub_campers(fake)
            counts["cabins"] = self._scrub_cabins(fake)
            counts["bunk_logs"] = self._scrub_bunk_logs()
            counts["staff_logs"] = self._scrub_staff_logs()
            counts["orders"] = self._scrub_orders()
            counts["email_recipients"] = self._scrub_email_recipients(fake)
            counts["email_logs_truncated"] = self._truncate_email_logs()
            counts["sessions_truncated"] = self._truncate_table("django_session")
            counts["authtokens_truncated"] = self._truncate_table("authtoken_token")
            counts["jwt_outstanding_truncated"] = self._truncate_table(
                "token_blacklist_outstandingtoken",
                cascade=True,
            )
            counts["jwt_blacklisted_truncated"] = self._truncate_table(
                "token_blacklist_blacklistedtoken",
            )
            counts["socialaccount_tokens_truncated"] = self._truncate_table(
                "socialaccount_socialtoken",
            )
            counts["socialaccount_accounts_truncated"] = self._truncate_table(
                "socialaccount_socialaccount",
                cascade=True,
            )
            counts["account_emailaddresses_scrubbed"] = self._scrub_account_emailaddresses()

        self._report(counts)

    # ---------------------------------------------------------------- safety

    def _enforce_safety_guards(self) -> None:
        if not settings.DEBUG:
            msg = (
                "Refusing to run: settings.DEBUG is False. "
                "scrub_pii is for local development databases only."
            )
            raise CommandError(msg)

        db_settings = settings.DATABASES.get("default", {})
        host = (db_settings.get("HOST") or "").strip().lower()
        name = db_settings.get("NAME", "<unknown>")

        if host not in LOCAL_DB_HOST_ALLOWLIST:
            msg = (
                f"Refusing to run: database host '{host}' is not in the local allowlist "
                f"({sorted(LOCAL_DB_HOST_ALLOWLIST)!r}). "
                f"Active DB: name={name!r} host={host!r}. "
                "If you really meant to scrub a remote DB, do not."
            )
            raise CommandError(msg)

        # Loud, hard-to-miss banner so accidental runs are obvious in logs.
        self.stdout.write(self.style.WARNING("=" * 72))
        self.stdout.write(self.style.WARNING(f"scrub_pii: target DB '{name}' on host '{host or 'localhost'}'"))
        self.stdout.write(self.style.WARNING("=" * 72))

    # ----------------------------------------------------------------- users

    def _scrub_users(self, fake: Faker, *, keep_superuser_emails: bool) -> int:
        dev_password_hash = make_password(DEV_PASSWORD)
        count = 0
        users = User.objects.all().only(
            "id", "email", "first_name", "last_name", "is_superuser",
        )
        for user in users.iterator(chunk_size=500):
            user.first_name = fake.first_name()
            user.last_name = fake.last_name()
            if not (keep_superuser_emails and user.is_superuser):
                user.email = f"user{user.pk}@example.test"
            user.password = dev_password_hash
            user.last_login = None
            user.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "email",
                    "password",
                    "last_login",
                ],
            )
            count += 1
        return count

    # --------------------------------------------------------------- campers

    def _scrub_campers(self, fake: Faker) -> int:
        count = 0
        for camper in Camper.objects.all().iterator(chunk_size=500):
            camper.first_name = fake.first_name()
            camper.last_name = fake.last_name()
            camper.date_of_birth = self._jitter_dob(camper.date_of_birth)
            camper.emergency_contact_name = fake.name()
            camper.emergency_contact_phone = fake.numerify("###-###-####")
            camper.camper_notes = SCRUB_PLACEHOLDER
            camper.parent_notes = SCRUB_PLACEHOLDER
            camper.status_note = ""
            camper.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "date_of_birth",
                    "emergency_contact_name",
                    "emergency_contact_phone",
                    "camper_notes",
                    "parent_notes",
                    "status_note",
                ],
            )
            count += 1
        return count

    @staticmethod
    def _jitter_dob(dob: dt.date | None) -> dt.date | None:
        """Preserve year+month, randomize day. Keeps age bucket realistic."""
        if not dob:
            return dob
        # Days 1..28 always valid for any month
        new_day = random.randint(1, 28)  # noqa: S311 - non-cryptographic OK
        return dob.replace(day=new_day)

    # ---------------------------------------------------------------- cabins

    def _scrub_cabins(self, fake: Faker) -> int:
        # Cabin name and capacity are realistic data, not PII. Notes/location
        # may contain identifying staff comments or addresses.
        return Cabin.objects.update(
            location="",
            notes=SCRUB_PLACEHOLDER,
        )

    # ---------------------------------------------------------- bunk logs

    def _scrub_bunk_logs(self) -> int:
        # Preserve scores so the UI looks real; only the free-text leaks PII.
        return BunkLog.objects.exclude(description="").update(description=SCRUB_PLACEHOLDER)

    def _scrub_staff_logs(self) -> int:
        return StaffLog.objects.update(
            elaboration=SCRUB_PLACEHOLDER,
            values_reflection=SCRUB_PLACEHOLDER,
        )

    # --------------------------------------------------------------- orders

    def _scrub_orders(self) -> int:
        return Order.objects.update(
            additional_notes=SCRUB_PLACEHOLDER,
            narrative_description=SCRUB_PLACEHOLDER,
        )

    # ------------------------------------------------------------ messaging

    def _scrub_email_recipients(self, fake: Faker) -> int:
        count = 0
        for recipient in EmailRecipient.objects.all().iterator(chunk_size=500):
            recipient.email = f"recipient{recipient.pk}@example.test"
            recipient.name = fake.name()
            recipient.save(update_fields=["email", "name"])
            count += 1
        return count

    def _truncate_email_logs(self) -> int:
        count = EmailLog.objects.count()
        EmailLog.objects.all().delete()
        return count

    # ----------------------------------------------------- raw-table truncates

    def _truncate_table(self, table: str, *, cascade: bool = False) -> int:
        """Truncate a table by raw SQL. Returns row count or -1 if table absent."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT to_regclass(%s)",
                [f"public.{table}"],
            )
            row = cursor.fetchone()
            if not row or row[0] is None:
                return -1

            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')  # noqa: S608
            count = cursor.fetchone()[0]
            cascade_sql = " CASCADE" if cascade else ""
            cursor.execute(f'TRUNCATE TABLE "{table}"{cascade_sql}')
            return count

    def _scrub_account_emailaddresses(self) -> int:
        """Update allauth's EmailAddress rows to mirror the scrubbed user emails."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.account_emailaddress')")
            row = cursor.fetchone()
            if not row or row[0] is None:
                return -1
            cursor.execute(
                """
                UPDATE account_emailaddress AS ae
                SET email = u.email,
                    verified = TRUE,
                    "primary" = TRUE
                FROM users_user AS u
                WHERE ae.user_id = u.id
                """,
            )
            return cursor.rowcount

    # --------------------------------------------------------------- output

    def _report(self, counts: dict[str, int]) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("PII scrub complete:"))
        for label, n in counts.items():
            if n == -1:
                rendered = "table not present (skipped)"
            else:
                rendered = f"{n} row(s)"
            self.stdout.write(f"  - {label:40s} {rendered}")
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                f"All non-superuser passwords reset to '{DEV_PASSWORD}'.",
            ),
        )

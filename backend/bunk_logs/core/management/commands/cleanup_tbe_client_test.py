"""Tear down the TBE client-test sandbox.

Deletes program ``client-test`` under org ``tbe``, TEST Person rows tagged
by this seed, and allowlisted ``@bunklogs.test`` Users. Never deletes the
``tbe`` Organization or program ``religious-school-2026-27``.

Default is a dry-run. Pass ``--confirm`` to delete. No interactive prompt
(safe for Render one-off jobs).

    python manage.py cleanup_tbe_client_test
    python manage.py cleanup_tbe_client_test --confirm
"""
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import Q

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.tbe_client_test import ORG_SLUG
from bunk_logs.core.tbe_client_test import PERSON_SOURCE
from bunk_logs.core.tbe_client_test import PROGRAM_SLUG
from bunk_logs.core.tbe_client_test import all_sandbox_emails

User = get_user_model()

REAL_PROGRAM_SLUG = "religious-school-2026-27"


class Command(BaseCommand):
    help = (
        "Delete the TBE client-test sandbox (program client-test + TEST people). "
        "Dry-run by default; pass --confirm to delete."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually delete. Without this flag, only report what would be removed.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if PROGRAM_SLUG == REAL_PROGRAM_SLUG:
            msg = "Refusing to run: sandbox program slug matches the production program."
            raise CommandError(msg)

        org = Organization.objects.filter(slug=ORG_SLUG).first()
        if org is None:
            self.stdout.write("Organization 'tbe' not found; nothing to clean up.")
            return

        program = Program.all_objects.filter(organization=org, slug=PROGRAM_SLUG).first()
        if program is not None and program.slug != PROGRAM_SLUG:
            msg = f"Refusing to delete program slug={program.slug!r}."
            raise CommandError(msg)

        emails = all_sandbox_emails()
        people = Person.all_objects.filter(organization=org).filter(
            Q(email__in=emails) | Q(external_ids__source=PERSON_SOURCE),
        )
        users = User.objects.filter(email__in=emails, is_test_data=True)

        n_programs = 1 if program is not None else 0
        n_people = people.count()
        n_users = users.count()

        if n_programs == 0 and n_people == 0 and n_users == 0:
            self.stdout.write(self.style.SUCCESS("No TBE client-test sandbox data found."))
            return

        self.stdout.write(
            f"Sandbox rows: {n_programs} program, {n_people} Person(s), {n_users} User(s).",
        )
        if program is not None:
            self.stdout.write(f"  Program: {org.slug}/{program.slug} (pk={program.pk})")
        for person in people.order_by("email"):
            self.stdout.write(f"  Person: {person.email} ({person.full_name})")
        for user in users.order_by("email"):
            self.stdout.write(f"  User:   {user.email}")

        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run. Re-run with --confirm to delete these rows.",
                ),
            )
            return

        with transaction.atomic():
            if program is not None:
                program.delete()
            # Re-query after program delete; Person is org-scoped and not cascaded.
            leftover = Person.all_objects.filter(organization=org).filter(
                Q(email__in=emails) | Q(external_ids__source=PERSON_SOURCE),
            )
            leftover.delete()
            User.objects.filter(email__in=emails, is_test_data=True).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {n_programs} program, {n_people} Person(s), {n_users} User(s). "
                f"Org {ORG_SLUG!r} and program {REAL_PROGRAM_SLUG!r} were not touched.",
            ),
        )

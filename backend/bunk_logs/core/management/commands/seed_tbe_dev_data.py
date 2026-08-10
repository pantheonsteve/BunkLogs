"""Seed a self-contained TBE dev/test sandbox for local development.

Creates its own ``dev-test`` Program inside the real ``tbe`` Organization
(never the production-mirroring ``religious-school-2026-27`` program from
``setup_tbe``), an admin user, five madrichim (grades 8-12), an active
``TemplateAssignment`` binding the global 3-2-1 template to that program,
and a few sample Reflections so dashboards have realistic content.

The test program's date window is recomputed on every run so it stays
"operational" (see ``core.program_scope``) no matter when this is run --
useful since the real 2026-27 program doesn't open until 2026-09-13.

DEBUG-only: refuses to run unless ``settings.DEBUG=True``, since it
provisions shared-password fixture accounts.

Run inside the django container::

    podman-compose -f backend/docker-compose.local.yml exec django \\
        python manage.py seed_tbe_dev_data --reset

Known limitation: ``AdminReflectionsTeamView`` scopes madrich Memberships
by organization, not by program, and resolves the template/period from
whichever program the first matching membership belongs to. Once the real
2026-27 program has active madrich rows too, the admin dashboard will
merge this sandbox's rows with the real cohort's. Run ``--reset`` before
onboarding real TBE madrichim locally.
"""
from __future__ import annotations

from datetime import date
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()

TBE_ORG_SLUG = "tbe"
TEST_PROGRAM_SLUG = "dev-test"
MADRICH_TEMPLATE_SLUG = "tbe-madrich-3-2-1-weekly"

DEV_PASSWORD = "tbedevpass123"  # local dev fixture password
GRADES = [8, 9, 10, 11, 12]
ADMIN_EMAIL = "tbe-dev-admin@example.test"

# Leave the last two madrichim without a submission so the admin dashboard
# shows a realistic submitted/missing mix rather than "all done".
SUBMITTING_GRADE_COUNT = 3


def _madrich_email(grade: int) -> str:
    return f"tbe-dev-madrich-{grade}@example.test"


def _all_seed_emails() -> list[str]:
    return [ADMIN_EMAIL, *[_madrich_email(g) for g in GRADES]]


class Command(BaseCommand):
    help = (
        "DEBUG-only. Seed a self-contained TBE dev/test sandbox: a perpetually "
        "operational Program, an admin user, 5 madrichim (grades 8-12), the "
        "3-2-1 template assignment, and a few sample reflections."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previously seeded TBE dev-sandbox data before re-creating it.",
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            msg = (
                "seed_tbe_dev_data is DEBUG-only -- it provisions shared-password "
                "fixture accounts. Refusing to run with DEBUG=False."
            )
            raise CommandError(msg)

        try:
            org = Organization.objects.get(slug=TBE_ORG_SLUG)
        except Organization.DoesNotExist as exc:
            msg = (
                f"Organization slug={TBE_ORG_SLUG!r} not found. "
                'Run "python manage.py setup_tbe" first.'
            )
            raise CommandError(msg) from exc

        if options["reset"]:
            self._reset(org)

        program = self._ensure_test_program(org)
        template = self._get_madrich_template()
        self._ensure_template_assignment(org, program, template)

        admin_person = self._upsert_admin(org, program)
        madrich_people = [self._upsert_madrich(org, program, grade) for grade in GRADES]

        self._seed_sample_reflections(org, program, template, madrich_people)

        self._print_summary(admin_person, madrich_people)

    # ------------------------------------------------------------- reset

    def _reset(self, org: Organization) -> None:
        emails = _all_seed_emails()

        program = Program.all_objects.filter(
            organization=org, slug=TEST_PROGRAM_SLUG,
        ).first()
        n_programs = 0
        if program is not None:
            # Cascades Membership, TemplateAssignment, Reflection (all FK to
            # Program with on_delete=CASCADE). Person/User are NOT cascaded --
            # Person belongs to the Organization, User to auth -- so they're
            # deleted explicitly below by their known fixture emails.
            program.delete()
            n_programs = 1

        person_ids = list(
            Person.all_objects.filter(organization=org, email__in=emails)
            .values_list("id", flat=True),
        )
        if person_ids:
            Person.all_objects.filter(id__in=person_ids).delete()

        _, deleted_by_model = User.objects.filter(email__in=emails).delete()
        n_users = deleted_by_model.get("users.User", 0)

        self.stdout.write(
            self.style.WARNING(
                f"--reset: deleted {n_programs} test program(s), "
                f"{len(person_ids)} Person record(s), {n_users} User record(s).",
            ),
        )

    # --------------------------------------------------- program + template

    def _ensure_test_program(self, org: Organization) -> Program:
        today = date.today()
        window_start = today - timedelta(days=180)
        window_end = today + timedelta(days=180)
        name = f"{org.name} Dev Test"

        program, created = Program.all_objects.get_or_create(
            organization=org,
            slug=TEST_PROGRAM_SLUG,
            defaults={
                "name": name,
                "program_type": "religious_school",
                "start_date": window_start,
                "end_date": window_end,
            },
        )
        window_changed = not created and (
            program.start_date != window_start or program.end_date != window_end
        )
        if window_changed:
            # Roll the window forward on every run so the program stays
            # "operational" (core.program_scope) regardless of how long ago
            # it was first seeded.
            program.start_date = window_start
            program.end_date = window_end
            program.save(update_fields=["start_date", "end_date"])
        verb = "Created" if created else "Refreshed" if window_changed else "Using existing"
        self.stdout.write(
            f"{verb} test program {TEST_PROGRAM_SLUG!r} ({program.start_date} - {program.end_date}).",
        )
        return program

    def _get_madrich_template(self) -> ReflectionTemplate:
        template = (
            ReflectionTemplate.all_objects.filter(
                organization__isnull=True, slug=MADRICH_TEMPLATE_SLUG, is_active=True,
            )
            .order_by("-version")
            .first()
        )
        if template is None:
            msg = (
                f"Global template slug={MADRICH_TEMPLATE_SLUG!r} not found. "
                "Expected it from migration 0037_seed_tbe_madrich_template -- "
                "run migrations first."
            )
            raise CommandError(msg)
        return template

    def _ensure_template_assignment(
        self, org: Organization, program: Program, template: ReflectionTemplate,
    ) -> TemplateAssignment:
        # Anchored a year back so the assignment is active regardless of the
        # program's rolling window (mirrors api/tests/conftest.py's autoseed).
        start = min(program.start_date, date.today()) - timedelta(days=365)
        assignment, created = TemplateAssignment.all_objects.get_or_create(
            organization=org,
            program=program,
            template=template,
            target_type=TemplateAssignment.TargetType.ROLE,
            target_payload={"role": "madrich"},
            defaults={
                "start_date": start,
                "status": TemplateAssignment.Status.ACTIVE,
                "is_required": True,
            },
        )
        verb = "Created" if created else "Using existing"
        self.stdout.write(f"{verb} TemplateAssignment pk={assignment.pk} for role=madrich.")
        return assignment

    # ------------------------------------------------------------- users

    def _upsert_admin(self, org: Organization, program: Program) -> Person:
        person = self._upsert_user_and_person(
            org, email=ADMIN_EMAIL, first_name="TBE Dev", last_name="Admin",
        )
        Membership.all_objects.get_or_create(
            program=program, person=person, role="admin", defaults={"is_active": True},
        )
        self.stdout.write(f"  Admin: {ADMIN_EMAIL} -> Person pk={person.pk}")
        return person

    def _upsert_madrich(self, org: Organization, program: Program, grade: int) -> Person:
        email = _madrich_email(grade)
        person = self._upsert_user_and_person(
            org, email=email, first_name="TBE Dev", last_name=f"Madrich{grade}",
        )
        membership, _ = Membership.all_objects.get_or_create(
            program=program, person=person, role="madrich",
            defaults={"is_active": True, "grade_level": grade},
        )
        if membership.grade_level != grade:
            membership.grade_level = grade
            membership.save(update_fields=["grade_level"])
        self.stdout.write(f"  Madrich (grade {grade}): {email} -> Person pk={person.pk}")
        return person

    @staticmethod
    def _upsert_user_and_person(
        org: Organization, *, email: str, first_name: str, last_name: str,
    ) -> Person:
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "is_active": True,
                "is_test_data": True,
            },
        )
        user.set_password(DEV_PASSWORD)
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
        user.is_test_data = True
        user.save()

        person = Person.all_objects.filter(user=user, organization=org).first()
        if person is None:
            person = Person.all_objects.filter(
                organization=org, email=email, user__isnull=True,
            ).first()
            if person is not None:
                person.user = user
                person.save(update_fields=["user"])
        if person is None:
            person = Person.all_objects.create(
                organization=org, first_name=first_name, last_name=last_name,
                email=email, user=user,
            )
        return person

    # ------------------------------------------------------- reflections

    def _seed_sample_reflections(
        self,
        org: Organization,
        program: Program,
        template: ReflectionTemplate,
        madrich_people: list[Person],
    ) -> None:
        today = date.today()
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)

        submitters = madrich_people[:SUBMITTING_GRADE_COUNT]
        for i, person in enumerate(submitters):
            existing = Reflection.all_objects.filter(
                template=template, program=program, subject=person,
                period_start=last_monday, period_end=last_sunday,
            ).exists()
            if existing:
                continue
            reflection = Reflection(
                organization=org,
                program=program,
                subject=person,
                author=person,
                template=template,
                period_start=last_monday,
                period_end=last_sunday,
                answers={
                    "wins": [
                        "Led a great discussion with my group",
                        "Helped a camper who was struggling",
                        f"Sample dev fixture win #{i + 1}",
                    ],
                    "improvements": [
                        "Arrive a few minutes earlier next week",
                        "Follow up on last week's action items",
                    ],
                    "question_or_concern": "Sample dev fixture -- no real concern.",
                    "ratings": {
                        "reliability_punctuality": 3,
                        "initiative": 3,
                        "communication": 4,
                        "problem_solving": 3,
                        "interpersonal": 4,
                    },
                },
                language="en",
                is_complete=True,
            )
            reflection.full_clean()
            reflection.save()
        self.stdout.write(
            f"  Seeded reflections for {len(submitters)} madrich(im) covering "
            f"{last_monday}..{last_sunday}; "
            f"{len(madrich_people) - len(submitters)} left as 'not submitted'.",
        )

    # ----------------------------------------------------------- summary

    def _print_summary(self, admin_person: Person, madrich_people: list[Person]) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("TBE dev sandbox ready."))
        self.stdout.write(f"  Shared password: {DEV_PASSWORD}")
        self.stdout.write(f"  Admin:   {ADMIN_EMAIL}")
        for grade in GRADES:
            self.stdout.write(f"  Madrich: {_madrich_email(grade)} (grade {grade})")
        self.stdout.write("")
        self.stdout.write(
            f"Data lives in tbe org's {TEST_PROGRAM_SLUG!r} program -- separate "
            "from setup_tbe's 'religious-school-2026-27' program. "
            "Re-run with --reset to tear it down.",
        )
        _ = admin_person, madrich_people  # kept for future use / clarity

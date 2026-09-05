"""Seed a production-safe TBE client-test sandbox.

Creates program ``client-test`` inside the real ``tbe`` Organization (so
testers can sign in at tbe.bunklogs.net), TEST-named people, two classrooms,
and TemplateAssignments for the global madrich + faculty weekly forms.
Does not seed sample Reflections -- testers submit those themselves.

Requires ``--password``. When DEBUG=False also requires ``--confirm-production``.
Never touches program ``religious-school-2026-27``.

Run on Render::

    python manage.py seed_tbe_client_test --password '...' --confirm-production
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

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.tbe_client_test import ADMIN
from bunk_logs.core.tbe_client_test import CLASSROOMS
from bunk_logs.core.tbe_client_test import FACULTY
from bunk_logs.core.tbe_client_test import FACULTY_TEMPLATE_SLUG
from bunk_logs.core.tbe_client_test import MADRICH_TEMPLATE_SLUG
from bunk_logs.core.tbe_client_test import MADRICHIM
from bunk_logs.core.tbe_client_test import ORG_SLUG
from bunk_logs.core.tbe_client_test import PERSON_SOURCE
from bunk_logs.core.tbe_client_test import PROGRAM_NAME_SUFFIX
from bunk_logs.core.tbe_client_test import PROGRAM_SLUG
from bunk_logs.core.tbe_client_test import STUDENTS
from bunk_logs.core.tbe_client_test import login_emails

User = get_user_model()

REAL_PROGRAM_SLUG = "religious-school-2026-27"


def _rolling_session_dates(today: date) -> list[str]:
    days_since_sunday = (today.weekday() - 6) % 7
    last_sunday = today - timedelta(days=days_since_sunday)
    start = last_sunday - timedelta(weeks=3)
    return [(start + timedelta(weeks=i)).isoformat() for i in range(20)]


class Command(BaseCommand):
    help = (
        "Seed the TBE client-test sandbox: program client-test, TEST people, "
        "2 classrooms, and madrich/faculty template assignments. "
        "Requires --password. Production also requires --confirm-production."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--password",
            required=True,
            help="Shared password for admin, faculty, and madrich test accounts.",
        )
        parser.add_argument(
            "--confirm-production",
            action="store_true",
            help="Required when DEBUG=False. Acknowledges this writes to a live database.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without writing.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        password: str = options["password"]
        if len(password) < 8:
            msg = "--password must be at least 8 characters."
            raise CommandError(msg)

        if not settings.DEBUG and not options["confirm_production"]:
            msg = (
                "Refusing to seed shared-password test accounts with DEBUG=False. "
                "Re-run with --confirm-production if you intend to write to this database."
            )
            raise CommandError(msg)

        try:
            org = Organization.objects.get(slug=ORG_SLUG)
        except Organization.DoesNotExist as exc:
            msg = (
                f"Organization slug={ORG_SLUG!r} not found. "
                'Run "python manage.py setup_tbe" first.'
            )
            raise CommandError(msg) from exc

        self._get_template(MADRICH_TEMPLATE_SLUG)
        self._get_template(FACULTY_TEMPLATE_SLUG)

        if options["dry_run"]:
            self._print_dry_run(org)
            return

        with transaction.atomic():
            program = self._ensure_program(org)
            madrich_tpl = self._get_template(MADRICH_TEMPLATE_SLUG)
            faculty_tpl = self._get_template(FACULTY_TEMPLATE_SLUG)
            self._ensure_template_assignment(org, program, madrich_tpl, role="madrich")
            self._ensure_template_assignment(org, program, faculty_tpl, role="faculty")

            self._upsert_login_person(org, program, ADMIN, role="admin")
            faculty_by_classroom = {
                spec["classroom"]: self._upsert_login_person(
                    org, program, spec, role="faculty",
                )
                for spec in FACULTY
            }
            madrich_people = [
                self._upsert_login_person(
                    org, program, spec, role="madrich", grade=spec["grade"],
                )
                for spec in MADRICHIM
            ]
            self._set_passwords(password)
            students = [self._upsert_student(org, program, spec) for spec in STUDENTS]
            classrooms = self._ensure_classrooms(
                org, program, faculty_by_classroom, madrich_people, students,
            )

        self._print_summary(password, classrooms)

    def _print_dry_run(self, org: Organization) -> None:
        self.stdout.write(f"[dry-run] Would seed program {PROGRAM_SLUG!r} in org {org.slug!r}.")
        self.stdout.write(f"[dry-run] Login accounts: {ADMIN['email']}")
        for spec in FACULTY:
            self.stdout.write(f"[dry-run]   Faculty: {spec['email']}")
        for spec in MADRICHIM:
            self.stdout.write(f"[dry-run]   Madrich: {spec['email']}")
        self.stdout.write(f"[dry-run] Students (no login): {len(STUDENTS)}")
        self.stdout.write(f"[dry-run] Classrooms: {len(CLASSROOMS)}")

    def _ensure_program(self, org: Organization) -> Program:
        today = date.today()
        window_start = today - timedelta(days=180)
        window_end = today + timedelta(days=180)
        name = f"{org.name} {PROGRAM_NAME_SUFFIX}"
        session_dates = _rolling_session_dates(today)
        program_settings = {
            "reminder_schedules": {"madrich": "weekly_wednesday_18:00"},
            "session_dates": session_dates,
        }

        program, created = Program.all_objects.get_or_create(
            organization=org,
            slug=PROGRAM_SLUG,
            defaults={
                "name": name,
                "program_type": "religious_school",
                "start_date": window_start,
                "end_date": window_end,
                "settings": program_settings,
            },
        )
        if program.slug == REAL_PROGRAM_SLUG:
            msg = f"Refusing to mutate production program {REAL_PROGRAM_SLUG!r}."
            raise CommandError(msg)

        updates: list[str] = []
        if program.start_date != window_start or program.end_date != window_end:
            program.start_date = window_start
            program.end_date = window_end
            updates.extend(["start_date", "end_date"])
        if program.settings.get("session_dates") != session_dates:
            merged = dict(program.settings or {})
            merged["session_dates"] = session_dates
            merged.setdefault("reminder_schedules", program_settings["reminder_schedules"])
            program.settings = merged
            updates.append("settings")
        if updates:
            program.save(update_fields=updates)

        verb = "Created" if created else "Refreshed" if updates else "Using existing"
        self.stdout.write(
            f"{verb} program {PROGRAM_SLUG!r} ({program.start_date} - {program.end_date}).",
        )
        return program

    def _get_template(self, slug: str) -> ReflectionTemplate:
        template = (
            ReflectionTemplate.all_objects.filter(
                organization__isnull=True, slug=slug, is_active=True,
            )
            .order_by("-version")
            .first()
        )
        if template is None:
            msg = (
                f"Global template slug={slug!r} not found. Run migrations first."
            )
            raise CommandError(msg)
        return template

    def _ensure_template_assignment(
        self,
        org: Organization,
        program: Program,
        template: ReflectionTemplate,
        *,
        role: str,
    ) -> TemplateAssignment:
        start = min(program.start_date, date.today()) - timedelta(days=365)
        assignment, created = TemplateAssignment.all_objects.get_or_create(
            organization=org,
            program=program,
            template=template,
            target_type=TemplateAssignment.TargetType.ROLE,
            target_payload={"role": role},
            defaults={
                "start_date": start,
                "status": TemplateAssignment.Status.ACTIVE,
                "is_required": True,
            },
        )
        verb = "Created" if created else "Using existing"
        self.stdout.write(
            f"{verb} TemplateAssignment role={role} -> {template.slug!r}.",
        )
        return assignment

    def _upsert_login_person(
        self,
        org: Organization,
        program: Program,
        spec: dict[str, Any],
        *,
        role: str,
        grade: int | None = None,
    ) -> Person:
        email = spec["email"]
        first_name = spec["first_name"]
        last_name = spec["last_name"]
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "is_active": True,
                "is_test_data": True,
            },
        )
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
        user.is_test_data = True
        user.save()

        person = self._upsert_person(org, email, first_name, last_name, user=user)
        defaults: dict[str, Any] = {"is_active": True}
        if grade is not None:
            defaults["grade_level"] = grade
        membership, _ = Membership.all_objects.get_or_create(
            program=program, person=person, role=role, defaults=defaults,
        )
        update_fields: list[str] = []
        if not membership.is_active:
            membership.is_active = True
            update_fields.append("is_active")
        if grade is not None and membership.grade_level != grade:
            membership.grade_level = grade
            update_fields.append("grade_level")
        if update_fields:
            membership.save(update_fields=update_fields)
        self.stdout.write(f"  {role}: {email} -> Person pk={person.pk}")
        return person

    def _upsert_student(
        self, org: Organization, program: Program, spec: dict[str, str],
    ) -> Person:
        person = self._upsert_person(
            org, spec["email"], spec["first_name"], spec["last_name"], user=None,
        )
        Membership.all_objects.get_or_create(
            program=program, person=person, role="student",
            defaults={"is_active": True},
        )
        self.stdout.write(f"  student (no login): {spec['email']} -> Person pk={person.pk}")
        return person

    @staticmethod
    def _upsert_person(
        org: Organization,
        email: str,
        first_name: str,
        last_name: str,
        *,
        user,
    ) -> Person:
        person = None
        if user is not None:
            person = Person.all_objects.filter(user=user, organization=org).first()
        if person is None:
            person = Person.all_objects.filter(organization=org, email=email).first()
        if person is None:
            return Person.all_objects.create(
                organization=org,
                first_name=first_name,
                last_name=last_name,
                email=email,
                user=user,
                external_ids={"source": PERSON_SOURCE},
            )
        updates: list[str] = []
        if person.first_name != first_name:
            person.first_name = first_name
            updates.append("first_name")
        if person.last_name != last_name:
            person.last_name = last_name
            updates.append("last_name")
        if person.email != email:
            person.email = email
            updates.append("email")
        if user is not None and person.user_id != user.pk:
            person.user = user
            updates.append("user")
        source = dict(person.external_ids or {})
        if source.get("source") != PERSON_SOURCE:
            source["source"] = PERSON_SOURCE
            person.external_ids = source
            updates.append("external_ids")
        if updates:
            person.save(update_fields=updates)
        return person

    def _set_passwords(self, password: str) -> None:
        for email in login_emails():
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save(update_fields=["password"])

    def _ensure_classrooms(
        self,
        org: Organization,
        program: Program,
        faculty_by_classroom: dict[str, Person],
        madrich_people: list[Person],
        students: list[Person],
    ) -> list[AssignmentGroup]:
        madrich_by_email = {p.email: p for p in madrich_people}
        student_by_email = {p.email: p for p in students}
        groups: list[AssignmentGroup] = []
        for classroom in CLASSROOMS:
            group, created = AssignmentGroup.all_objects.get_or_create(
                organization=org,
                program=program,
                slug=classroom["slug"],
                defaults={
                    "name": classroom["name"],
                    "group_type": "classroom",
                    "is_active": True,
                },
            )
            faculty = faculty_by_classroom[classroom["key"]]
            self._place(group, faculty, "author")
            madrich_specs = [m for m in MADRICHIM if m["classroom"] == classroom["key"]]
            for spec in madrich_specs:
                person = madrich_by_email[spec["email"]]
                self._place(group, person, "subject")
                self._place(group, person, "author")
            student_specs = [s for s in STUDENTS if s["classroom"] == classroom["key"]]
            for spec in student_specs:
                self._place(group, student_by_email[spec["email"]], "subject")
            verb = "Created" if created else "Using existing"
            self.stdout.write(
                f"  {verb} classroom {classroom['name']!r} "
                f"({len(madrich_specs)} madrichim, {len(student_specs)} students).",
            )
            groups.append(group)
        return groups

    @staticmethod
    def _place(group: AssignmentGroup, person: Person, role_in_group: str) -> None:
        AssignmentGroupMembership.all_objects.update_or_create(
            group=group, person=person, role_in_group=role_in_group,
            defaults={"is_active": True},
        )

    def _print_summary(self, password: str, classrooms: list[AssignmentGroup]) -> None:
        signin = (
            "http://localhost:5173/signin"
            if settings.DEBUG
            else "https://tbe.bunklogs.net/signin"
        )
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("TBE client-test sandbox ready."))
        self.stdout.write(f"  Sign in:  {signin}")
        self.stdout.write(f"  Password: {password}")
        self.stdout.write(f"  Admin:    {ADMIN['email']}")
        for spec in FACULTY:
            self.stdout.write(f"  Faculty:  {spec['email']}")
        for spec in MADRICHIM:
            self.stdout.write(f"  Madrich:  {spec['email']} (grade {spec['grade']})")
        self.stdout.write(f"  Students: {len(STUDENTS)} roster subjects (no login)")
        self.stdout.write(f"  Classes:  {', '.join(g.name for g in classrooms)}")
        self.stdout.write("")
        self.stdout.write(
            f"  Lives in org {ORG_SLUG!r} program {PROGRAM_SLUG!r}. "
            f"Does not touch {REAL_PROGRAM_SLUG!r}.",
        )
        self.stdout.write("  Tear down with: python manage.py cleanup_tbe_client_test --confirm")

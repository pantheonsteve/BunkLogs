"""Seed a self-contained TBE dev/test sandbox for local development.

Creates its own ``dev-test`` Program inside the real ``tbe`` Organization
(never the production-mirroring ``religious-school-2026-27`` program from
``setup_tbe``), an admin user, five madrichim (grades 8-12), two active
``TemplateAssignment`` rows, and a few sample Reflections so dashboards
have realistic content.

Two assignments, not one, so the Story 63 multi-card dashboard is
exercisable locally: the recurring weekly 3-2-1 (the global template from
migration 0037) plus an on-demand "Mid-Year Check-In" owned by the tbe
org, standing in for the kind of ad-hoc form a Director would create. No
sample submissions are seeded for the check-in, so its card starts in the
"missing" state and you can walk the submit flow by hand.

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
from django.utils import timezone

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import ClassroomChallenge
from bunk_logs.core.models import ClassroomChallengeResponse
from bunk_logs.core.models import MadrichAvailability
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
FACULTY_TEMPLATE_SLUG = "faculty-self-reflection"
CHECK_IN_TEMPLATE_SLUG = "tbe-dev-mid-year-check-in"
CHECK_IN_TEMPLATE_NAME = "Mid-Year Check-In"
CHECK_IN_SCHEMA = {
    "fields": [
        {
            "key": "going_well",
            "type": "text",
            "required": True,
            "prompts": {"en": "What is going well for you this year?"},
        },
        {
            "key": "support_needed",
            "type": "text",
            "required": True,
            "prompts": {"en": "What support do you need from your Director?"},
        },
    ],
}

DEV_PASSWORD = "tbedevpass123"  # local dev fixture password
GRADES = [8, 9, 10, 11, 12]
ADMIN_EMAIL = "tbe-dev-admin@example.test"
FACULTY_EMAIL = "tbe-dev-faculty@example.test"
CLASSROOM_SLUG = "dev-test-classroom"
CLASSROOM_NAME = "Grade 9 -- Room 204"

# Leave the last two madrichim without a submission so the admin dashboard
# shows a realistic submitted/missing mix rather than "all done".
SUBMITTING_GRADE_COUNT = 3


def _rolling_session_dates(today: date) -> list[str]:
    """Sundays from 3 weeks back through 16 weeks forward of `today`.

    Recomputed on every run (like the test program's date window) so the
    availability calendar always has upcoming sessions to show, regardless
    of when this command is run.
    """
    days_since_sunday = (today.weekday() - 6) % 7
    last_sunday = today - timedelta(days=days_since_sunday)
    start = last_sunday - timedelta(weeks=3)
    weeks = 20
    return [(start + timedelta(weeks=i)).isoformat() for i in range(weeks)]


def _madrich_email(grade: int) -> str:
    return f"tbe-dev-madrich-{grade}@example.test"


def _all_seed_emails() -> list[str]:
    return [ADMIN_EMAIL, FACULTY_EMAIL, *[_madrich_email(g) for g in GRADES]]


class Command(BaseCommand):
    help = (
        "DEBUG-only. Seed a self-contained TBE dev/test sandbox: a perpetually "
        "operational Program, an admin user, 5 madrichim (grades 8-12), faculty, "
        "madrich + faculty template assignments, and a few sample reflections."
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
        self._ensure_template_assignment(org, program, template, role="madrich")

        check_in = self._ensure_check_in_template(org)
        self._ensure_template_assignment(
            org, program, check_in, start=date.today() - timedelta(days=14), role="madrich",
        )

        faculty_template = self._get_faculty_template()
        self._ensure_template_assignment(org, program, faculty_template, role="faculty")

        admin_person = self._upsert_admin(org, program)
        madrich_people = [self._upsert_madrich(org, program, grade) for grade in GRADES]
        faculty_person = self._upsert_faculty(org, program)

        self._seed_sample_reflections(org, program, template, madrich_people)
        self._seed_sample_availability(org, program, madrich_people)

        classroom = self._ensure_classroom(org, program, madrich_people, faculty_person)
        self._seed_classroom_challenges(org, program, classroom, madrich_people, faculty_person)

        self._print_summary(admin_person, madrich_people, faculty_person)

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

        # Safe only after the program delete above cascaded the Reflections
        # that referenced it.
        n_templates, _ = ReflectionTemplate.all_objects.filter(
            organization=org, slug=CHECK_IN_TEMPLATE_SLUG,
        ).delete()

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
                f"{n_templates} dev template row(s), "
                f"{len(person_ids)} Person record(s), {n_users} User record(s).",
            ),
        )

    # --------------------------------------------------- program + template

    def _ensure_test_program(self, org: Organization) -> Program:
        today = date.today()
        window_start = today - timedelta(days=180)
        window_end = today + timedelta(days=180)
        name = f"{org.name} Dev Test"
        session_dates = _rolling_session_dates(today)

        program, created = Program.all_objects.get_or_create(
            organization=org,
            slug=TEST_PROGRAM_SLUG,
            defaults={
                "name": name,
                "program_type": "religious_school",
                "start_date": window_start,
                "end_date": window_end,
                "settings": {"session_dates": session_dates},
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

        # Step 4_7: keep session_dates rolling forward the same way, so the
        # availability calendar always has upcoming Sundays to mark.
        settings_changed = not created and program.settings.get("session_dates") != session_dates
        if settings_changed:
            merged = dict(program.settings or {})
            merged["session_dates"] = session_dates
            program.settings = merged
            program.save(update_fields=["settings"])

        verb = "Created" if created else "Refreshed" if (window_changed or settings_changed) else "Using existing"
        self.stdout.write(
            f"{verb} test program {TEST_PROGRAM_SLUG!r} ({program.start_date} - {program.end_date}).",
        )
        return program

    def _get_faculty_template(self) -> ReflectionTemplate:
        template = ReflectionTemplate.all_objects.filter(
            organization__isnull=True,
            slug=FACULTY_TEMPLATE_SLUG,
            is_active=True,
        ).order_by("-version").first()
        if template is None:
            msg = (
                f"Global template slug={FACULTY_TEMPLATE_SLUG!r} not found. "
                "Expected it from migration 0066_seed_faculty_self_reflection_template "
                "-- run migrations first."
            )
            raise CommandError(msg)
        return template

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

    def _ensure_check_in_template(self, org: Organization) -> ReflectionTemplate:
        """An org-owned on-demand form, so the dashboard has a second card.

        Owned by ``tbe`` rather than global: this stands in for a form a
        Director built for their own org, which is the case Story 63 has to
        handle alongside the seeded weekly template.
        """
        template, created = ReflectionTemplate.all_objects.update_or_create(
            organization=org,
            slug=CHECK_IN_TEMPLATE_SLUG,
            version=1,
            defaults={
                "name": CHECK_IN_TEMPLATE_NAME,
                "description": "Local dev fixture from seed_tbe_dev_data.",
                "cadence": "on_demand",
                "schema": CHECK_IN_SCHEMA,
                "languages": ["en"],
                "is_active": True,
                "subject_mode": "self",
                "assignment_scope": "none",
                "assignment_group_types": [],
                "author_role_filter": ["madrich"],
                "subject_role_filter": [],
                "required_per_subject_per_period": 1,
                "subject_visible": False,
                "supports_privacy": False,
                "role": "madrich",
                "program_type": "religious_school",
            },
        )
        verb = "Created" if created else "Refreshed"
        self.stdout.write(f"{verb} template {CHECK_IN_TEMPLATE_SLUG!r} (on_demand).")
        return template

    def _ensure_template_assignment(
        self,
        org: Organization,
        program: Program,
        template: ReflectionTemplate,
        *,
        role: str,
        start: date | None = None,
    ) -> TemplateAssignment:
        # Anchored a year back so the assignment is active regardless of the
        # program's rolling window (mirrors api/tests/conftest.py's autoseed).
        if start is None:
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
            f"{verb} TemplateAssignment pk={assignment.pk} for role={role} "
            f"-> {template.slug!r}.",
        )
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

    def _upsert_faculty(self, org: Organization, program: Program) -> Person:
        """Step 4_8: a faculty member who authors the dev classroom."""
        person = self._upsert_user_and_person(
            org, email=FACULTY_EMAIL, first_name="TBE Dev", last_name="Faculty",
        )
        Membership.all_objects.get_or_create(
            program=program, person=person, role="faculty", defaults={"is_active": True},
        )
        self.stdout.write(f"  Faculty: {FACULTY_EMAIL} -> Person pk={person.pk}")
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

    # ------------------------------------------------------- availability

    def _seed_sample_availability(
        self,
        org: Organization,
        program: Program,
        madrich_people: list[Person],
    ) -> None:
        """AC5.4: sample rows for 3 of 5 dev madrichim so the admin matrix is testable."""
        session_dates = [
            date.fromisoformat(s) for s in (program.settings or {}).get("session_dates", [])
        ]
        upcoming = sorted(d for d in session_dates if d >= date.today())[:2]
        if not upcoming:
            self.stdout.write("  No upcoming session_dates on the test program; skipping availability seed.")
            return

        statuses = [
            MadrichAvailability.STATUS_AVAILABLE,
            MadrichAvailability.STATUS_TENTATIVE,
            MadrichAvailability.STATUS_UNAVAILABLE,
        ]
        seeded_people = madrich_people[:SUBMITTING_GRADE_COUNT]
        for person, status_value in zip(seeded_people, statuses, strict=False):
            for session_date in upcoming:
                MadrichAvailability.all_objects.update_or_create(
                    organization=org, program=program, person=person, session_date=session_date,
                    defaults={"status": status_value},
                )
        self.stdout.write(
            f"  Seeded availability for {len(seeded_people)} madrich(im) across "
            f"{len(upcoming)} upcoming session date(s); "
            f"{len(madrich_people) - len(seeded_people)} left unset.",
        )

    # ------------------------------------------------------- classroom (4_8)

    def _ensure_classroom(
        self,
        org: Organization,
        program: Program,
        madrich_people: list[Person],
        faculty_person: Person,
    ) -> AssignmentGroup:
        """A single classroom with 2 Madrichim (subjects) + 1 faculty (author).

        Enough to exercise the peer-redaction and faculty-identity paths
        of Step 4_8 locally without a full roster import.
        """
        classroom, created = AssignmentGroup.all_objects.get_or_create(
            organization=org, program=program, slug=CLASSROOM_SLUG,
            defaults={"name": CLASSROOM_NAME, "group_type": "classroom"},
        )
        subjects = madrich_people[:2]
        for person in subjects:
            AssignmentGroupMembership.all_objects.update_or_create(
                group=classroom, person=person, role_in_group="subject",
                defaults={"is_active": True},
            )
        AssignmentGroupMembership.all_objects.update_or_create(
            group=classroom, person=faculty_person, role_in_group="author",
            defaults={"is_active": True},
        )
        verb = "Created" if created else "Using existing"
        self.stdout.write(
            f"  {verb} classroom {CLASSROOM_NAME!r} with {len(subjects)} Madrich subject(s) "
            "+ 1 faculty author.",
        )
        return classroom

    def _seed_classroom_challenges(
        self,
        org: Organization,
        program: Program,
        classroom: AssignmentGroup,
        madrich_people: list[Person],
        faculty_person: Person,
    ) -> None:
        """One open challenge + one resolved-with-response, per Step 4_8 QA."""
        session_dates = [
            date.fromisoformat(s) for s in (program.settings or {}).get("session_dates", [])
        ]
        past_or_today = sorted(d for d in session_dates if d <= date.today())
        session_date = past_or_today[-1] if past_or_today else date.today()

        madrich_a, madrich_b = madrich_people[0], madrich_people[1]

        open_challenge, _ = ClassroomChallenge.all_objects.update_or_create(
            organization=org, program=program, assignment_group=classroom,
            author=madrich_a, session_date=session_date, category=ClassroomChallenge.CATEGORY_BEHAVIOR,
            defaults={
                "body": "Two students were disruptive during Hebrew drill; we paused twice.",
                "status": ClassroomChallenge.STATUS_OPEN,
            },
        )

        resolved_challenge, resolved_created = ClassroomChallenge.all_objects.update_or_create(
            organization=org, program=program, assignment_group=classroom,
            author=madrich_b, session_date=session_date, category=ClassroomChallenge.CATEGORY_MATERIALS,
            defaults={
                "body": "We ran out of worksheets partway through the session.",
                "status": ClassroomChallenge.STATUS_RESOLVED,
                "resolved_at": timezone.now(),
                "resolved_by": faculty_person,
            },
        )
        if resolved_created or not resolved_challenge.responses.exists():
            ClassroomChallengeResponse.all_objects.create(
                challenge=resolved_challenge, author=faculty_person,
                body="Thanks for flagging -- I've ordered extra copies for next week.",
            )

        self.stdout.write(
            f"  Seeded 1 open + 1 resolved (with faculty response) classroom challenge "
            f"for {CLASSROOM_NAME!r} on {session_date}.",
        )

    # ----------------------------------------------------------- summary

    def _print_summary(
        self, admin_person: Person, madrich_people: list[Person], faculty_person: Person | None = None,
    ) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("TBE dev sandbox ready."))
        self.stdout.write(f"  Shared password: {DEV_PASSWORD}")
        self.stdout.write(f"  Admin:   {ADMIN_EMAIL}")
        for grade in GRADES:
            self.stdout.write(f"  Madrich: {_madrich_email(grade)} (grade {grade})")
        self.stdout.write(f"  Faculty: {FACULTY_EMAIL}")
        self.stdout.write("")
        self.stdout.write(
            "  Each Madrich dashboard shows two cards: the weekly 3-2-1 and "
            f"{CHECK_IN_TEMPLATE_NAME!r} (on-demand, no sample submissions).",
        )
        self.stdout.write(
            f"  {CLASSROOM_NAME!r} (Step 4_8): grade-8 + grade-9 Madrichim are subjects, "
            f"{FACULTY_EMAIL} is the faculty author. One open + one resolved-with-response "
            "challenge is seeded for local QA.",
        )
        self.stdout.write(
            f"Data lives in tbe org's {TEST_PROGRAM_SLUG!r} program -- separate "
            "from setup_tbe's 'religious-school-2026-27' program. "
            "Re-run with --reset to tear it down.",
        )
        _ = admin_person, madrich_people, faculty_person  # kept for future use / clarity

"""Seed a fixed RBAC test bench: one user per Membership.capability + edge cases.

Targets the new multi-tenant ``Membership.capability`` stack documented in
``docs/membership-role-vs-capability.md``. Creates ten Users (each with a Person
+ Membership where applicable), seeds the four reflection templates the
Playwright suite exercises, plus a small AssignmentGroup hierarchy and a few
Reflection rows so dashboards have content.

Idempotent: re-running keeps the same User pks / emails. Pass ``--reset`` to
delete the previously seeded ``rbac-*@example.test`` users (cascades Person +
Membership) and the AssignmentGroups created here, then re-create everything.

Run inside the django container::

    podman-compose -f backend/docker-compose.local.yml exec django \\
        python manage.py seed_rbac_test_users --reset

DEBUG-only: refuses to run unless ``settings.DEBUG=True`` so production cannot
accidentally provision shared-password test accounts.
"""
from __future__ import annotations

from datetime import date
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()

SHARED_PASSWORD = "rbacpass123"  # noqa: S105 — local dev fixture password

CLC_ORG_SLUG = "clc"
CLC_PROGRAM_SLUG = "summer-2026"

TBE_ORG_SLUG = "tbe-test"
TBE_PROGRAM_SLUG = "fall-2026"

# Templates loaded from disk (already shipped under templates/reflection_templates/clc_2026/).
TEMPLATE_FILE_BASE = "templates/reflection_templates/clc_2026"
TEMPLATE_MANIFEST: list[dict[str, str]] = [
    {"role": "counselor", "file": f"{TEMPLATE_FILE_BASE}/counselor.json"},
    {"role": "kitchen_staff", "file": f"{TEMPLATE_FILE_BASE}/kitchen_staff.json"},
    {"role": "leadership_team", "file": f"{TEMPLATE_FILE_BASE}/leadership_team.json"},
    {"role": "camper_care", "file": f"{TEMPLATE_FILE_BASE}/camper_care.json"},
]

# Per-camper "bunk log" template defined inline (subject_mode=single_subject).
# Schema mirrors the legacy BunkLog fields (camper_scores + help-requested
# toggles + daily report) so the manual walkthrough in
# docs/rbac-counselor-walkthrough.md feels like the real bunk-log flow.
SUPERVISOR_TEMPLATE_SLUG = "rbac-test-bunk-daily"
SUPERVISOR_TEMPLATE: dict[str, Any] = {
    "name": "RBAC test — Camper daily check-in",
    "slug": SUPERVISOR_TEMPLATE_SLUG,
    "version": 1,
    "cadence": "daily",
    "program_type": "summer_camp",
    "description": (
        "Per-camper daily check-in. Counselor authors one reflection per camper "
        "subject in their bunk; mirrors the legacy BunkLog field shape."
    ),
    "languages": ["en"],
    "is_active": True,
    "schema": {
        "fields": [
            {
                "key": "not_on_camp",
                "type": "single_choice",
                "required": True,
                "prompts": {"en": "Camper not on camp today"},
                "options": [
                    {"value": "no", "labels": {"en": "No — camper was on camp"}},
                    {"value": "yes", "labels": {"en": "Yes — camper was absent"}},
                ],
            },
            {
                "key": "request_unit_head_help",
                "type": "single_choice",
                "required": True,
                "prompts": {"en": "Unit Head help requested"},
                "options": [
                    {"value": "no", "labels": {"en": "No"}},
                    {"value": "yes", "labels": {"en": "Yes"}},
                ],
            },
            {
                "key": "request_camper_care_help",
                "type": "single_choice",
                "required": True,
                "prompts": {"en": "Camper Care help requested"},
                "options": [
                    {"value": "no", "labels": {"en": "No"}},
                    {"value": "yes", "labels": {"en": "Yes"}},
                ],
            },
            {
                "key": "camper_scores",
                "type": "rating_group",
                "required": False,
                "dashboard_role": "category_ratings",
                "scale": [1, 5],
                "scale_labels": {"en": ["1 — Poor", "2", "3", "4", "5 — Excellent"]},
                "categories": [
                    {
                        "key": "behavior",
                        "labels": {"en": "Behavior — how was this camper's behavior today?"},
                    },
                    {
                        "key": "participation",
                        "labels": {"en": "Participation — joined activities today?"},
                    },
                    {
                        "key": "social",
                        "labels": {"en": "Social — included with peers today?"},
                    },
                ],
            },
            {
                "key": "daily_report",
                "type": "textarea",
                "required": False,
                "prompts": {"en": "Daily report (highlights, anything to flag)"},
            },
        ],
    },
}

# Subjects (campers) used by the supervisor/program_lead paths.
SUBJECT_PERSONS: list[dict[str, str]] = [
    {"first_name": "Alex", "last_name": "RbacCamperA", "email": "rbac-camper-a@example.test"},
    {"first_name": "Bree", "last_name": "RbacCamperB", "email": "rbac-camper-b@example.test"},
]

# Test users. Each row drives both the Django User row and (where applicable)
# Person + Membership rows. Keys mirror the Playwright e2e/fixtures/users.ts.
TEST_USERS: list[dict[str, Any]] = [
    {
        "key": "counselor",
        "email": "rbac-counselor@example.test",
        "first_name": "RBAC",
        "last_name": "Counselor",
        "user_role": "Counselor",
        "is_staff": False,
        "is_superuser": False,
        "org_slug": CLC_ORG_SLUG,
        "program_slug": CLC_PROGRAM_SLUG,
        "membership_role": "counselor",
        "purpose": "participant; can self-reflect; bunk author",
    },
    {
        "key": "kitchen",
        "email": "rbac-kitchen@example.test",
        "first_name": "RBAC",
        "last_name": "Kitchen",
        "user_role": "Counselor",
        "is_staff": False,
        "is_superuser": False,
        "org_slug": CLC_ORG_SLUG,
        "program_slug": CLC_PROGRAM_SLUG,
        "membership_role": "kitchen_staff",
        "purpose": "participant; bilingual /reflect?language=es path",
    },
    {
        "key": "unit_head",
        "email": "rbac-unit-head@example.test",
        "first_name": "RBAC",
        "last_name": "UnitHead",
        "user_role": "Unit Head",
        "is_staff": False,
        "is_superuser": False,
        "org_slug": CLC_ORG_SLUG,
        "program_slug": CLC_PROGRAM_SLUG,
        "membership_role": "unit_head",
        "purpose": "supervisor; descendant-author of bunk via parent unit",
    },
    {
        "key": "leadership",
        "email": "rbac-leadership@example.test",
        "first_name": "RBAC",
        "last_name": "Leadership",
        "user_role": "Leadership",
        "is_staff": False,
        "is_superuser": False,
        "org_slug": CLC_ORG_SLUG,
        "program_slug": CLC_PROGRAM_SLUG,
        "membership_role": "leadership_team",
        "purpose": "program_lead; /team/dashboard",
    },
    {
        "key": "camper_care",
        "email": "rbac-camper-care@example.test",
        "first_name": "RBAC",
        "last_name": "CamperCare",
        "user_role": "Camper Care",
        "is_staff": False,
        "is_superuser": False,
        "org_slug": CLC_ORG_SLUG,
        "program_slug": CLC_PROGRAM_SLUG,
        "membership_role": "camper_care",
        "purpose": "domain_specialist (wellness); /wellness/dashboard",
    },
    {
        "key": "health_center",
        "email": "rbac-health-center@example.test",
        "first_name": "RBAC",
        "last_name": "HealthCenter",
        "user_role": "Camper Care",
        "is_staff": False,
        "is_superuser": False,
        "org_slug": CLC_ORG_SLUG,
        "program_slug": CLC_PROGRAM_SLUG,
        "membership_role": "health_center",
        "purpose": "domain_specialist (wellness, second role); wellness visibility",
    },
    {
        "key": "admin",
        "email": "rbac-admin@example.test",
        "first_name": "RBAC",
        "last_name": "Admin",
        "user_role": "Admin",
        "is_staff": False,
        "is_superuser": False,
        "org_slug": CLC_ORG_SLUG,
        "program_slug": CLC_PROGRAM_SLUG,
        "membership_role": "admin",
        "purpose": "admin via Membership only (is_staff=False)",
    },
    {
        "key": "superuser",
        "email": "rbac-superuser@example.test",
        "first_name": "RBAC",
        "last_name": "Superuser",
        "user_role": "Admin",
        "is_staff": True,
        "is_superuser": True,
        "org_slug": None,
        "program_slug": None,
        "membership_role": None,
        "purpose": "Django superuser, no Person/Membership; sees everything",
    },
    {
        "key": "no_membership",
        "email": "rbac-no-membership@example.test",
        "first_name": "RBAC",
        "last_name": "NoMembership",
        "user_role": "",
        "is_staff": False,
        "is_superuser": False,
        "org_slug": None,
        "program_slug": None,
        "membership_role": None,
        "purpose": "logged in but no Person; 403/empty on /reflect, /tasks",
    },
    {
        "key": "tbe_admin",
        "email": "rbac-tbe-admin@example.test",
        "first_name": "RBAC",
        "last_name": "TbeAdmin",
        "user_role": "Admin",
        "is_staff": False,
        "is_superuser": False,
        "org_slug": TBE_ORG_SLUG,
        "program_slug": TBE_PROGRAM_SLUG,
        "membership_role": "admin",
        "purpose": "admin of a different org; cross-tenant isolation",
    },
]

UNIT_GROUP_NAME = "RBAC Unit Pioneers"
BUNK_GROUP_NAME = "RBAC Bunk Maple"


class Command(BaseCommand):
    help = (
        "DEBUG-only. Seed the RBAC test bench: 10 users (one per capability + "
        "edge cases), templates, AssignmentGroups, and a few reflections."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previously seeded rbac-* users + RBAC AssignmentGroups before re-creating.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Skip the user-matrix summary at the end.",
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            msg = (
                "seed_rbac_test_users is DEBUG-only — it provisions shared-password "
                "fixture accounts. Refusing to run with DEBUG=False."
            )
            raise CommandError(msg)

        if options["reset"]:
            self._reset()

        # 1. Org / program: clc + tbe-test
        self.stdout.write("Ensuring CLC org + Summer 2026 program (setup_crane_lake)…")
        call_command("setup_crane_lake", stdout=self.stdout, stderr=self.stderr)
        clc_org = Organization.objects.get(slug=CLC_ORG_SLUG)
        clc_program = Program.all_objects.get(organization=clc_org, slug=CLC_PROGRAM_SLUG)

        tbe_org, tbe_program = self._ensure_tbe_org()

        # 2. Templates from disk
        self.stdout.write("Seeding 4 reflection templates from disk…")
        for entry in TEMPLATE_MANIFEST:
            call_command(
                "seed_role_template",
                org_slug=CLC_ORG_SLUG,
                role=entry["role"],
                template_file=entry["file"],
                stdout=self.stdout,
                stderr=self.stderr,
            )

        # 3. Inline supervisor template (single_subject -> per_subject_in_group)
        supervisor_template = self._upsert_supervisor_template(clc_org)

        # 4. Subject Persons (campers, not linked to Users)
        subject_persons = [self._upsert_subject_person(clc_org, spec) for spec in SUBJECT_PERSONS]

        # 5. Users + Person + Membership
        users_by_key: dict[str, dict[str, Any]] = {}
        for spec in TEST_USERS:
            org_for_user = None
            program_for_user = None
            if spec["org_slug"] == CLC_ORG_SLUG:
                org_for_user = clc_org
                program_for_user = clc_program
            elif spec["org_slug"] == TBE_ORG_SLUG:
                org_for_user = tbe_org
                program_for_user = tbe_program

            user, person, membership = self._upsert_user_record(
                spec, org_for_user, program_for_user,
            )
            users_by_key[spec["key"]] = {
                "spec": spec,
                "user": user,
                "person": person,
                "membership": membership,
            }

        # 6. AssignmentGroup hierarchy (unit -> bunk) + memberships
        unit_group, bunk_group = self._ensure_assignment_groups(clc_org, clc_program)
        self._wire_group_memberships(
            unit_group=unit_group,
            bunk_group=bunk_group,
            unit_head_person=users_by_key["unit_head"]["person"],
            counselor_person=users_by_key["counselor"]["person"],
            subject_persons=subject_persons,
        )

        # 7. Sample Reflections so dashboards have data
        self._seed_reflections(
            clc_org=clc_org,
            clc_program=clc_program,
            counselor_person=users_by_key["counselor"]["person"],
            counselor_user=users_by_key["counselor"]["user"],
            camper_care_person=users_by_key["camper_care"]["person"],
            camper_care_user=users_by_key["camper_care"]["user"],
            leadership_person=users_by_key["leadership"]["person"],
            leadership_user=users_by_key["leadership"]["user"],
            bunk_group=bunk_group,
            subject_persons=subject_persons,
            supervisor_template=supervisor_template,
        )

        if not options["quiet"]:
            self._print_summary(users_by_key)

    # ----------------------------------------------------------- reset

    def _reset(self) -> None:
        emails = [spec["email"] for spec in TEST_USERS]
        users = User.objects.filter(email__in=emails)
        n_users = users.count()
        # Person FK on user is OneToOne with on_delete=SET_NULL, so delete
        # Person rows explicitly so Memberships cascade away too.
        person_ids = list(
            Person.all_objects.filter(user__email__in=emails).values_list("id", flat=True),
        )
        if person_ids:
            Person.all_objects.filter(id__in=person_ids).delete()
        # Subject Persons (no User attached): match by email pattern.
        Person.all_objects.filter(
            email__in=[spec["email"] for spec in SUBJECT_PERSONS],
        ).delete()
        users.delete()
        # Drop the AssignmentGroup hierarchy created by this command. Match by
        # name so a re-seed with a different program doesn't strand them.
        AssignmentGroup.all_objects.filter(
            name__in=[UNIT_GROUP_NAME, BUNK_GROUP_NAME],
        ).delete()
        self.stdout.write(
            self.style.WARNING(
                f"--reset: deleted {n_users} rbac-* User(s), "
                f"{len(person_ids)} Person record(s), and RBAC AssignmentGroups.",
            ),
        )

    # ----------------------------------------------------------- tbe org

    def _ensure_tbe_org(self) -> tuple[Organization, Program]:
        org, _ = Organization.objects.get_or_create(
            slug=TBE_ORG_SLUG,
            defaults={
                "name": "Temple Beth-El (RBAC test)",
                "settings": {"timezone": "America/New_York", "locale_default": "en"},
                "is_active": True,
            },
        )
        program, _ = Program.all_objects.get_or_create(
            organization=org,
            slug=TBE_PROGRAM_SLUG,
            defaults={
                "name": f"{org.name} - Fall 2026",
                "program_type": "religious_school",
                "start_date": date(2026, 9, 1),
                "end_date": date(2026, 12, 15),
            },
        )
        return org, program

    # -------------------------------------------------- supervisor template

    def _upsert_supervisor_template(self, org: Organization) -> ReflectionTemplate:
        existing = ReflectionTemplate.all_objects.filter(
            organization=org, slug=SUPERVISOR_TEMPLATE_SLUG, version=1,
        ).first()
        defaults = {
            "role": "counselor",
            "name": SUPERVISOR_TEMPLATE["name"],
            "description": SUPERVISOR_TEMPLATE["description"],
            "cadence": SUPERVISOR_TEMPLATE["cadence"],
            "program_type": SUPERVISOR_TEMPLATE["program_type"],
            "schema": SUPERVISOR_TEMPLATE["schema"],
            "languages": SUPERVISOR_TEMPLATE["languages"],
            "is_active": SUPERVISOR_TEMPLATE["is_active"],
            "subject_mode": "single_subject",
            "assignment_scope": "per_subject_in_group",
            "assignment_group_types": ["bunk"],
            "author_role_filter": ["counselor", "unit_head"],
            "subject_role_filter": ["camper"],
            "subject_visible": False,
            "required_per_subject_per_period": 1,
        }
        obj, created = ReflectionTemplate.all_objects.update_or_create(
            organization=org,
            slug=SUPERVISOR_TEMPLATE_SLUG,
            version=1,
            defaults=defaults,
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(f"  {verb} supervisor template {SUPERVISOR_TEMPLATE_SLUG} (pk={obj.pk}).")
        return obj

    # ------------------------------------------------------- subject persons

    def _upsert_subject_person(self, org: Organization, spec: dict[str, str]) -> Person:
        person = Person.all_objects.filter(organization=org, email=spec["email"]).first()
        if person is None:
            person = Person.all_objects.create(
                organization=org,
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                email=spec["email"],
            )
        # Ensure a "camper" Membership so the subject_role_filter passes.
        Membership.all_objects.get_or_create(
            program=Program.all_objects.get(organization=org, slug=CLC_PROGRAM_SLUG),
            person=person,
            role="camper",
            defaults={"is_active": True},
        )
        return person

    # ------------------------------------------------------------- users

    def _upsert_user_record(
        self,
        spec: dict[str, Any],
        org: Organization | None,
        program: Program | None,
    ) -> tuple[User, Person | None, Membership | None]:
        user, created = User.objects.get_or_create(
            email=spec["email"],
            defaults={
                "first_name": spec["first_name"],
                "last_name": spec["last_name"],
                "role": spec["user_role"],
                "is_staff": spec["is_staff"],
                "is_superuser": spec["is_superuser"],
                "is_active": True,
                "is_test_data": True,
            },
        )
        # Always reset password + sync mutable fields so re-runs converge.
        user.set_password(SHARED_PASSWORD)
        user.first_name = spec["first_name"]
        user.last_name = spec["last_name"]
        user.role = spec["user_role"]
        user.is_staff = spec["is_staff"]
        user.is_superuser = spec["is_superuser"]
        user.is_active = True
        user.is_test_data = True
        user.save()

        if org is None or spec["membership_role"] is None:
            verb = "Created" if created else "Synced"
            self.stdout.write(f"  {verb} user {spec['email']} (no Person/Membership).")
            return user, None, None

        person = Person.all_objects.filter(user=user).first()
        if person is None:
            person = Person.all_objects.filter(
                organization=org, email=spec["email"], user__isnull=True,
            ).first()
            if person is not None:
                person.user = user
                person.save(update_fields=["user"])
        if person is None:
            person = Person.all_objects.create(
                organization=org,
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                email=spec["email"],
                user=user,
            )

        membership, m_created = Membership.all_objects.get_or_create(
            program=program,
            person=person,
            role=spec["membership_role"],
            defaults={"is_active": True},
        )
        if not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=["is_active"])

        verb = "Created" if created else "Synced"
        m_verb = "new membership" if m_created else "existing membership"
        self.stdout.write(
            f"  {verb} user {spec['email']} -> Person pk={person.pk} ({m_verb} role={spec['membership_role']}).",
        )
        return user, person, membership

    # ------------------------------------------------- assignment groups

    def _ensure_assignment_groups(
        self, org: Organization, program: Program,
    ) -> tuple[AssignmentGroup, AssignmentGroup]:
        unit, _ = AssignmentGroup.all_objects.get_or_create(
            program=program,
            group_type="unit",
            slug=slugify(UNIT_GROUP_NAME)[:100],
            defaults={
                "organization": org,
                "name": UNIT_GROUP_NAME,
                "is_active": True,
            },
        )
        bunk, _ = AssignmentGroup.all_objects.get_or_create(
            program=program,
            group_type="bunk",
            slug=slugify(BUNK_GROUP_NAME)[:100],
            defaults={
                "organization": org,
                "name": BUNK_GROUP_NAME,
                "parent": unit,
                "is_active": True,
            },
        )
        if bunk.parent_id != unit.pk:
            bunk.parent = unit
            bunk.save(update_fields=["parent"])
        return unit, bunk

    def _wire_group_memberships(
        self,
        *,
        unit_group: AssignmentGroup,
        bunk_group: AssignmentGroup,
        unit_head_person: Person,
        counselor_person: Person,
        subject_persons: list[Person],
    ) -> None:
        # Unit head authors at the unit level (descendant visibility into bunk).
        AssignmentGroupMembership.all_objects.get_or_create(
            group=unit_group,
            person=unit_head_person,
            role_in_group="author",
            defaults={"is_active": True},
        )
        # Unit head also authors at the bunk so supervisor_coverage (which
        # iterates groups the viewer is a *direct* author of) returns content.
        AssignmentGroupMembership.all_objects.get_or_create(
            group=bunk_group,
            person=unit_head_person,
            role_in_group="author",
            defaults={"is_active": True},
        )
        # Counselor authors at the bunk.
        AssignmentGroupMembership.all_objects.get_or_create(
            group=bunk_group,
            person=counselor_person,
            role_in_group="author",
            defaults={"is_active": True},
        )
        # Campers are subjects.
        for camper in subject_persons:
            AssignmentGroupMembership.all_objects.get_or_create(
                group=bunk_group,
                person=camper,
                role_in_group="subject",
                defaults={"is_active": True},
            )

    # ----------------------------------------------------------- reflections

    def _seed_reflections(
        self,
        *,
        clc_org: Organization,
        clc_program: Program,
        counselor_person: Person,
        counselor_user: User,
        camper_care_person: Person,
        camper_care_user: User,
        leadership_person: Person,
        leadership_user: User,
        bunk_group: AssignmentGroup,
        subject_persons: list[Person],
        supervisor_template: ReflectionTemplate,
    ) -> None:
        today = timezone.localdate()

        def _by_slug(slug: str) -> ReflectionTemplate | None:
            return (
                ReflectionTemplate.all_objects.filter(
                    organization=clc_org, slug=slug, is_active=True,
                )
                .order_by("-version")
                .first()
            )

        # 1. Counselor self-reflection (counselor template, subject_mode=self, daily).
        counselor_tpl = _by_slug("clc-2026-counselor-daily")
        if counselor_tpl is not None:
            self._upsert_reflection(
                template=counselor_tpl,
                organization=clc_org,
                program=clc_program,
                subject=counselor_person,
                author=counselor_person,
                submitted_by=counselor_user,
                period_start=today,
                period_end=today,
                answers={
                    "not_on_camp": "no",
                    "request_unit_head_help": "no",
                    "request_camper_care_help": "no",
                    "camper_scores": {"behavior": 4, "participation": 5, "social": 4},
                    "daily_report": "RBAC fixture: solid day across the bunk.",
                },
                language="en",
            )

        # 2. Camper-care wellness reflection (camper_care template, daily, self).
        cc_tpl = _by_slug("clc-2026-camper-care-daily")
        if cc_tpl is not None:
            self._upsert_reflection(
                template=cc_tpl,
                organization=clc_org,
                program=clc_program,
                subject=camper_care_person,
                author=camper_care_person,
                submitted_by=camper_care_user,
                period_start=today,
                period_end=today,
                answers={
                    "follow_ups": "RBAC fixture: two short check-ins; nothing acute.",
                },
                language="en",
            )

        # 3. Leadership biweekly (leadership_team template, biweekly, self).
        lt_tpl = _by_slug("clc-2026-leadership-biweekly")
        if lt_tpl is not None:
            # biweekly cadence: align period to the 14-day window containing today
            monday = today - timedelta(days=today.weekday())
            iso_week = monday.isocalendar()[1]
            period_start = monday if iso_week % 2 == 0 else monday - timedelta(weeks=1)
            period_end = period_start + timedelta(days=13)
            self._upsert_reflection(
                template=lt_tpl,
                organization=clc_org,
                program=clc_program,
                subject=leadership_person,
                author=leadership_person,
                submitted_by=leadership_user,
                period_start=period_start,
                period_end=period_end,
                answers={
                    "unit_pulse": "RBAC fixture: unit morale steady.",
                    "wins_and_risks": "RBAC fixture: programming wins; staffing risk.",
                },
                language="en",
            )

        # NOTE: We deliberately do NOT pre-seed per-camper reflections from
        # the supervisor template here. The manual walkthrough in
        # docs/rbac-counselor-walkthrough.md asks the counselor to fill them
        # in via the UI, so the campers must start as uncovered on /tasks.
        _ = supervisor_template, subject_persons  # kept for future use

    @staticmethod
    def _upsert_reflection(
        *,
        template: ReflectionTemplate,
        organization: Organization,
        program: Program,
        subject: Person,
        author: Person,
        submitted_by: User,
        period_start: date,
        period_end: date,
        answers: dict[str, Any],
        language: str,
        assignment_group: AssignmentGroup | None = None,
    ) -> Reflection:
        existing = Reflection.all_objects.filter(
            template=template,
            program=program,
            subject=subject,
            author=author,
            period_start=period_start,
            period_end=period_end,
        ).first()
        if existing is not None:
            return existing
        reflection = Reflection(
            organization=organization,
            program=program,
            subject=subject,
            author=author,
            submitted_by=submitted_by,
            template=template,
            period_start=period_start,
            period_end=period_end,
            answers=answers,
            language=language,
            assignment_group=assignment_group,
            is_complete=True,
        )
        reflection.full_clean()
        reflection.save()
        return reflection

    # ----------------------------------------------------------- summary

    def _print_summary(self, users_by_key: dict[str, dict[str, Any]]) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("RBAC test bench ready."))
        self.stdout.write(f"  Shared password: {SHARED_PASSWORD}")
        self.stdout.write("")
        header = (
            f"  {'KEY':<14} {'EMAIL':<38} {'CAPABILITY':<18} {'ROLE':<18} PURPOSE"
        )
        self.stdout.write(header)
        self.stdout.write("  " + "-" * (len(header) - 2))
        for key, payload in users_by_key.items():
            spec = payload["spec"]
            membership: Membership | None = payload["membership"]
            cap = membership.capability if membership is not None else "—"
            mrole = membership.role if membership is not None else "—"
            self.stdout.write(
                f"  {key:<14} {spec['email']:<38} {cap:<18} {mrole:<18} {spec['purpose']}",
            )
        self.stdout.write("")
        self.stdout.write(
            "Sign in at http://localhost:5173/signin and verify the matrix in "
            "docs/rbac-test-plan.md.",
        )

"""Tests for the production-safe TBE client-test seed and cleanup commands."""
from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test.utils import override_settings

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.tbe_client_test import ADMIN
from bunk_logs.core.tbe_client_test import CLASSROOMS
from bunk_logs.core.tbe_client_test import FACULTY
from bunk_logs.core.tbe_client_test import FACULTY_TEMPLATE_SLUG
from bunk_logs.core.tbe_client_test import MADRICH_TEMPLATE_SLUG
from bunk_logs.core.tbe_client_test import MADRICHIM
from bunk_logs.core.tbe_client_test import PROGRAM_SLUG
from bunk_logs.core.tbe_client_test import STUDENTS
from bunk_logs.core.tbe_client_test import login_emails

User = get_user_model()

pytestmark = pytest.mark.django_db

PASSWORD = "clienttestpass"

_MINIMAL_SCHEMA = {
    "fields": [
        {"key": "note", "type": "textarea", "required": False, "prompts": {"en": "Notes"}},
    ],
}


@pytest.fixture(autouse=True)
def _debug_true(settings):
    settings.DEBUG = True


@pytest.fixture(autouse=True)
def _ensure_global_templates(db):
    ReflectionTemplate.all_objects.update_or_create(
        organization=None,
        slug=MADRICH_TEMPLATE_SLUG,
        version=1,
        defaults={
            "name": "TBE Madrich Weekly 3-2-1",
            "cadence": "weekly",
            "schema": _MINIMAL_SCHEMA,
            "languages": ["en"],
            "is_active": True,
            "subject_mode": "self",
            "author_role_filter": ["madrich"],
            "role": "madrich",
            "program_type": "religious_school",
        },
    )
    ReflectionTemplate.all_objects.update_or_create(
        organization=None,
        slug=FACULTY_TEMPLATE_SLUG,
        version=1,
        defaults={
            "name": "Faculty Weekly Reflection",
            "cadence": "weekly",
            "schema": _MINIMAL_SCHEMA,
            "languages": ["en"],
            "is_active": True,
            "subject_mode": "self",
            "author_role_filter": ["faculty"],
            "role": "faculty",
            "program_type": "religious_school",
        },
    )


def _setup_tbe():
    call_command("setup_tbe", stdout=StringIO())


def _seed(**kwargs):
    call_command(
        "seed_tbe_client_test",
        password=PASSWORD,
        stdout=StringIO(),
        **kwargs,
    )


def test_requires_tbe_org_to_exist():
    with pytest.raises(CommandError, match="setup_tbe"):
        _seed()


def test_blocked_in_production_without_confirm():
    _setup_tbe()
    with override_settings(DEBUG=False), pytest.raises(CommandError, match="confirm-production"):
        _seed()
    assert not Program.all_objects.filter(slug=PROGRAM_SLUG).exists()
    assert not User.objects.filter(email=ADMIN["email"]).exists()


def test_seeds_program_people_classrooms_and_assignments():
    _setup_tbe()
    _seed()

    org = Organization.objects.get(slug="tbe")
    program = Program.all_objects.get(organization=org, slug=PROGRAM_SLUG)
    assert program.program_type == "religious_school"
    assert program.name.startswith(org.name)

    for email in login_emails():
        user = User.objects.get(email=email)
        assert user.check_password(PASSWORD)
        assert user.is_test_data
        person = Person.all_objects.get(user=user, organization=org)
        assert person.external_ids.get("source") == "tbe_client_test"

    admin_person = Person.all_objects.get(organization=org, email=ADMIN["email"])
    assert Membership.all_objects.filter(
        program=program, person=admin_person, role="admin", is_active=True,
    ).exists()

    assert Membership.all_objects.filter(program=program, role="faculty").count() == len(FACULTY)
    assert Membership.all_objects.filter(program=program, role="madrich").count() == len(MADRICHIM)
    assert Membership.all_objects.filter(program=program, role="student").count() == len(STUDENTS)

    for spec in STUDENTS:
        person = Person.all_objects.get(organization=org, email=spec["email"])
        assert person.user_id is None
        assert not User.objects.filter(email=spec["email"]).exists()

    classrooms = AssignmentGroup.all_objects.filter(
        program=program, group_type="classroom",
    )
    assert classrooms.count() == len(CLASSROOMS)
    for classroom in classrooms:
        authors = AssignmentGroupMembership.all_objects.filter(
            group=classroom, role_in_group="author", is_active=True,
        )
        subjects = AssignmentGroupMembership.all_objects.filter(
            group=classroom, role_in_group="subject", is_active=True,
        )
        assert authors.filter(person__memberships__role="faculty").exists()
        assert subjects.filter(person__memberships__role="student").count() == 4
        assert subjects.filter(person__memberships__role="madrich").count() == 2

    assignments = TemplateAssignment.all_objects.filter(program=program)
    assert set(assignments.values_list("template__slug", flat=True)) == {
        MADRICH_TEMPLATE_SLUG, FACULTY_TEMPLATE_SLUG,
    }
    assert all(a.status == TemplateAssignment.Status.ACTIVE and a.is_required for a in assignments)
    assert not Reflection.all_objects.filter(program=program).exists()


def test_does_not_touch_the_real_tbe_program():
    _setup_tbe()
    real = Program.all_objects.get(organization__slug="tbe", slug="religious-school-2026-27")
    settings_before = dict(real.settings)
    _seed()
    real.refresh_from_db()
    assert real.settings == settings_before
    assert Membership.all_objects.filter(program=real).count() == 0


def test_is_idempotent():
    _setup_tbe()
    _seed()
    _seed()
    org = Organization.objects.get(slug="tbe")
    assert Program.all_objects.filter(organization=org, slug=PROGRAM_SLUG).count() == 1
    assert User.objects.filter(email=ADMIN["email"]).count() == 1
    assert Person.all_objects.filter(organization=org, email__in=login_emails()).count() == 7
    assert Membership.all_objects.filter(
        program__slug=PROGRAM_SLUG, role="student",
    ).count() == len(STUDENTS)


def test_dry_run_writes_nothing():
    _setup_tbe()
    _seed(dry_run=True)
    assert not Program.all_objects.filter(slug=PROGRAM_SLUG).exists()
    assert not User.objects.filter(email=ADMIN["email"]).exists()


def test_cleanup_dry_run_leaves_data():
    _setup_tbe()
    _seed()
    call_command("cleanup_tbe_client_test", stdout=StringIO())
    assert Program.all_objects.filter(slug=PROGRAM_SLUG).exists()
    assert User.objects.filter(email=ADMIN["email"]).exists()


def test_cleanup_removes_sandbox_and_spares_real_tbe_data():
    _setup_tbe()
    _seed()

    org = Organization.objects.get(slug="tbe")
    real_person = Person.all_objects.create(
        organization=org, first_name="Rachel", last_name="Director",
        email="rachel@templebethel.example",
    )
    real_program = Program.all_objects.get(organization=org, slug="religious-school-2026-27")
    Membership.all_objects.create(program=real_program, person=real_person, role="admin")

    call_command("cleanup_tbe_client_test", "--confirm", stdout=StringIO())

    assert Organization.objects.filter(slug="tbe").exists()
    assert Program.all_objects.filter(organization=org, slug="religious-school-2026-27").exists()
    assert Person.all_objects.filter(pk=real_person.pk).exists()
    assert Membership.all_objects.filter(person=real_person, role="admin").exists()

    assert not Program.all_objects.filter(slug=PROGRAM_SLUG).exists()
    assert not User.objects.filter(email__in=login_emails()).exists()
    assert not Person.all_objects.filter(
        organization=org, email__in=[s["email"] for s in STUDENTS],
    ).exists()

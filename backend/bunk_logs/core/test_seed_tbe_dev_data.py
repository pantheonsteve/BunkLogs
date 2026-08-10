"""Tests for the seed_tbe_dev_data local-dev fixture command."""
from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test.utils import override_settings

from bunk_logs.core.management.commands.seed_tbe_dev_data import ADMIN_EMAIL
from bunk_logs.core.management.commands.seed_tbe_dev_data import GRADES
from bunk_logs.core.management.commands.seed_tbe_dev_data import TEST_PROGRAM_SLUG
from bunk_logs.core.management.commands.seed_tbe_dev_data import _madrich_email
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _debug_true(settings):
    settings.DEBUG = True


def _run_setup_tbe():
    call_command("setup_tbe", stdout=StringIO())


def test_blocked_without_debug():
    with override_settings(DEBUG=False), pytest.raises(CommandError, match="DEBUG-only"):
        call_command("seed_tbe_dev_data", stdout=StringIO())


def test_requires_tbe_org_to_exist():
    with pytest.raises(CommandError, match="setup_tbe"):
        call_command("seed_tbe_dev_data", stdout=StringIO())


def test_creates_program_admin_madrichim_and_assignment():
    _run_setup_tbe()
    call_command("seed_tbe_dev_data", stdout=StringIO())

    org = Organization.objects.get(slug="tbe")
    program = Program.all_objects.get(organization=org, slug=TEST_PROGRAM_SLUG)
    assert program.program_type == "religious_school"
    assert program.name.startswith(org.name)

    admin_user = User.objects.get(email=ADMIN_EMAIL)
    admin_person = Person.all_objects.get(user=admin_user, organization=org)
    assert Membership.all_objects.filter(
        program=program, person=admin_person, role="admin", is_active=True,
    ).exists()

    for grade in GRADES:
        user = User.objects.get(email=_madrich_email(grade))
        person = Person.all_objects.get(user=user, organization=org)
        membership = Membership.all_objects.get(
            program=program, person=person, role="madrich",
        )
        assert membership.is_active
        assert membership.grade_level == grade

    assignment = TemplateAssignment.all_objects.get(
        program=program, target_type=TemplateAssignment.TargetType.ROLE,
        target_payload={"role": "madrich"},
    )
    assert assignment.status == TemplateAssignment.Status.ACTIVE
    assert assignment.template.slug == "tbe-madrich-3-2-1-weekly"

    # 3 of 5 madrichim get a sample submission; 2 stay "not submitted".
    assert Reflection.all_objects.filter(program=program).count() == 3


def test_does_not_touch_the_real_setup_tbe_program():
    _run_setup_tbe()
    real_program = Program.all_objects.get(
        organization__slug="tbe", slug="religious-school-2026-27",
    )
    real_program_settings_before = dict(real_program.settings)

    call_command("seed_tbe_dev_data", stdout=StringIO())

    real_program.refresh_from_db()
    assert real_program.settings == real_program_settings_before
    assert Membership.all_objects.filter(program=real_program).count() == 0


def test_is_idempotent():
    _run_setup_tbe()
    call_command("seed_tbe_dev_data", stdout=StringIO())
    call_command("seed_tbe_dev_data", stdout=StringIO())

    org = Organization.objects.get(slug="tbe")
    assert Program.all_objects.filter(organization=org, slug=TEST_PROGRAM_SLUG).count() == 1
    assert User.objects.filter(email=ADMIN_EMAIL).count() == 1
    for grade in GRADES:
        assert User.objects.filter(email=_madrich_email(grade)).count() == 1
    # Re-running should not duplicate the sample reflections either.
    program = Program.all_objects.get(organization=org, slug=TEST_PROGRAM_SLUG)
    assert Reflection.all_objects.filter(program=program).count() == 3


def test_reset_removes_seeded_data_without_touching_the_org():
    _run_setup_tbe()
    call_command("seed_tbe_dev_data", stdout=StringIO())

    call_command("seed_tbe_dev_data", "--reset", stdout=StringIO())

    org = Organization.objects.get(slug="tbe")
    assert Program.all_objects.filter(organization=org, slug=TEST_PROGRAM_SLUG).count() == 1
    assert User.objects.filter(email=ADMIN_EMAIL).count() == 1
    for grade in GRADES:
        assert User.objects.filter(email=_madrich_email(grade)).count() == 1
    program = Program.all_objects.get(organization=org, slug=TEST_PROGRAM_SLUG)
    assert Reflection.all_objects.filter(program=program).count() == 3


def test_reset_alone_wipes_data_without_recreating_when_run_only_once_more():
    """Regression guard: --reset deletes the *previous* run's rows before
    recreating fresh ones, rather than accumulating duplicates.
    """
    _run_setup_tbe()
    call_command("seed_tbe_dev_data", stdout=StringIO())
    org = Organization.objects.get(slug="tbe")
    program_before = Program.all_objects.get(organization=org, slug=TEST_PROGRAM_SLUG)
    first_program_pk = program_before.pk

    call_command("seed_tbe_dev_data", "--reset", stdout=StringIO())

    program_after = Program.all_objects.get(organization=org, slug=TEST_PROGRAM_SLUG)
    # A fresh Program row (new pk) proves the old one was actually deleted,
    # not just reused.
    assert program_after.pk != first_program_pk
    assert Membership.all_objects.filter(program__pk=first_program_pk).count() == 0


def test_test_program_window_stays_operational_across_reruns():
    from datetime import date

    from bunk_logs.core.program_scope import is_program_operational

    _run_setup_tbe()
    call_command("seed_tbe_dev_data", stdout=StringIO())
    org = Organization.objects.get(slug="tbe")
    program = Program.all_objects.get(organization=org, slug=TEST_PROGRAM_SLUG)

    # Simulate a stale window from a long-ago run, then re-run without --reset.
    program.start_date = date(2020, 1, 1)
    program.end_date = date(2020, 6, 1)
    program.save(update_fields=["start_date", "end_date"])

    call_command("seed_tbe_dev_data", stdout=StringIO())

    program.refresh_from_db()
    assert is_program_operational(program, today=date.today())

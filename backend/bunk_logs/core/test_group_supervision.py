"""Supervision follows group placement for roles marked supervises_group."""
from __future__ import annotations

from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from bunk_logs.core.group_supervision import plan_group_supervision
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision
from bunk_logs.core.time_utils import get_today

pytestmark = pytest.mark.django_db


@pytest.fixture
def org():
    return Organization.objects.create(name="Sync Camp", slug="sync-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Sync Camp Season",
        slug="sync-season",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 15),
    )


@pytest.fixture
def unit(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Upper", slug="upper", group_type="unit", is_active=True,
    )


@pytest.fixture
def unit_head(org, program):
    person = Person.all_objects.create(
        organization=org, first_name="Una", last_name="Head",
    )
    return Membership.all_objects.create(
        program=program, person=person, role="unit_head", is_active=True,
    )


def _place(unit, person):
    return AssignmentGroupMembership.all_objects.create(
        group=unit, person=person, role_in_group="author", is_active=True,
    )


def test_sync_command_dry_run_writes_nothing_and_apply_is_idempotent(org, unit, unit_head):
    _place(unit, unit_head.person)
    out = StringIO()
    call_command("sync_group_supervision", "--org", org.slug, stdout=out)
    assert "1 supervision row(s) to create" in out.getvalue()
    assert "Dry run" in out.getvalue()
    assert Supervision.all_objects.count() == 0

    call_command("sync_group_supervision", "--org", org.slug, "--apply", stdout=StringIO())
    row = Supervision.all_objects.get()
    assert row.target_type == Supervision.TargetType.ASSIGNMENT_GROUP
    assert row.target_group_id == unit.id
    assert row.supervisor_membership_id == unit_head.id
    assert row.end_date is None

    call_command("sync_group_supervision", "--org", org.slug, "--apply", stdout=StringIO())
    assert Supervision.all_objects.count() == 1
    row.refresh_from_db()
    assert row.end_date is None


def test_plan_does_not_supervise_camper_care_from_placement(org, program, unit):
    person = Person.all_objects.create(
        organization=org, first_name="Care", last_name="Lead",
    )
    Membership.all_objects.create(
        program=program, person=person, role="camper_care", is_active=True,
    )
    _place(unit, person)
    plan = plan_group_supervision(org, today=get_today(org))
    assert plan.creates == []

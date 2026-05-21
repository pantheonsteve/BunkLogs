"""Tests for :class:`CamperDayState` (Step 7_6 foundation).

Story 3 criterion 8 / decision C1: off-camp campers appear in a separate
sub-section on the counselor's roster and don't count toward expected
submissions. ``CamperDayState`` is the storage for that flag; this module
covers the model-level invariants (uniqueness, cross-org guards, defaults).
"""
from __future__ import annotations

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from bunk_logs.core.models import CamperDayState
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program


def _seed_org(slug: str = "camp", name: str = "Camp Org") -> tuple[Organization, Program]:
    org = Organization.objects.create(name=name, slug=slug)
    program = Program.all_objects.create(
        organization=org,
        name=f"{name} Summer 2026",
        slug=f"{slug}-2026",
        program_type="summer_camp",
        start_date="2026-06-01",
        end_date="2026-08-15",
    )
    return org, program


@pytest.mark.django_db
def test_camper_day_state_defaults():
    org, program = _seed_org()
    camper = Person.all_objects.create(
        organization=org, first_name="A", last_name="Camper",
    )
    row = CamperDayState.all_objects.create(
        organization=org,
        program=program,
        camper=camper,
        date=date(2026, 7, 15),
    )
    assert row.is_off_camp is False
    assert row.reason == ""
    assert row.set_by_membership is None


@pytest.mark.django_db
def test_camper_day_state_unique_per_camper_per_date():
    org, program = _seed_org()
    camper = Person.all_objects.create(
        organization=org, first_name="A", last_name="Camper",
    )
    CamperDayState.all_objects.create(
        organization=org,
        program=program,
        camper=camper,
        date=date(2026, 7, 15),
        is_off_camp=True,
    )
    with pytest.raises(IntegrityError):
        CamperDayState.all_objects.create(
            organization=org,
            program=program,
            camper=camper,
            date=date(2026, 7, 15),
            is_off_camp=False,
        )


@pytest.mark.django_db
def test_camper_day_state_rejects_cross_org_camper():
    org, program = _seed_org()
    other_org = Organization.objects.create(name="Other", slug="other")
    foreign = Person.all_objects.create(
        organization=other_org, first_name="X", last_name="Camper",
    )
    row = CamperDayState(
        organization=org,
        program=program,
        camper=foreign,
        date=date(2026, 7, 15),
    )
    with pytest.raises(ValidationError):
        row.full_clean()


@pytest.mark.django_db
def test_camper_day_state_rejects_cross_org_program():
    org, _program = _seed_org()
    _other_org, other_program = _seed_org(slug="other", name="Other Org")
    camper = Person.all_objects.create(
        organization=org, first_name="A", last_name="Camper",
    )
    row = CamperDayState(
        organization=org,
        program=other_program,
        camper=camper,
        date=date(2026, 7, 15),
    )
    with pytest.raises(ValidationError):
        row.full_clean()


@pytest.mark.django_db
def test_camper_day_state_records_setter_membership(django_assert_num_queries):
    # Light smoke-test: ``set_by_membership`` is just a nullable FK; this
    # mostly verifies the relation exists and ORM access works.
    org, program = _seed_org()
    person = Person.all_objects.create(
        organization=org, first_name="UH", last_name="Person",
    )
    uh_membership = Membership.all_objects.create(
        person=person,
        program=program,
        role="unit_head",
    )
    camper = Person.all_objects.create(
        organization=org, first_name="A", last_name="Camper",
    )
    row = CamperDayState.all_objects.create(
        organization=org,
        program=program,
        camper=camper,
        date=date(2026, 7, 15),
        is_off_camp=True,
        reason="home visit",
        set_by_membership=uh_membership,
    )
    row.refresh_from_db()
    assert row.set_by_membership == uh_membership
    assert row.reason == "home visit"

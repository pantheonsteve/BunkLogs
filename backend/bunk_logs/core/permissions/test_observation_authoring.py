"""Observation subject tagging is org-wide for anyone who may write observations."""

from __future__ import annotations

from datetime import date

import pytest

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.permissions.observation_authoring import can_author_observation
from bunk_logs.core.permissions.observation_authoring import observation_authorable_subject_queryset
from bunk_logs.core.permissions.subject_note_authoring import can_author_subject_note

pytestmark = pytest.mark.django_db


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Obs Org", slug="obs-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Obs Org Summer",
        slug="obs-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


def _person(org, first, last):
    return Person.all_objects.create(organization=org, first_name=first, last_name=last)


def _membership(program, person, role):
    return Membership.all_objects.create(
        program=program, person=person, role=role, is_active=True,
    )


def test_counselor_can_tag_any_org_person_on_observation(org, program):
    counselor = _person(org, "Ann", "Counselor")
    _membership(program, counselor, "counselor")
    distant_camper = _person(org, "Far", "Away")
    _membership(program, distant_camper, "camper")

    assert can_author_observation(counselor, distant_camper, org, user=None) is True
    assert can_author_subject_note(counselor, distant_camper, org, user=None) is False

    searchable = observation_authorable_subject_queryset(counselor, org)
    assert distant_camper.id in set(searchable.values_list("id", flat=True))


def test_kitchen_staff_cannot_tag_observation_subjects(org, program):
    staff = _person(org, "Kit", "Chen")
    _membership(program, staff, "kitchen_staff")
    camper = _person(org, "Pat", "Camper")
    _membership(program, camper, "camper")

    assert can_author_observation(staff, camper, org, user=None) is False
    assert observation_authorable_subject_queryset(staff, org).count() == 0

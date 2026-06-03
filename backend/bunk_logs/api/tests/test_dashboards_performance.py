"""Tests for /api/v1/dashboards/groups/performance/."""
from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()
pytestmark = pytest.mark.django_db

URL = "/api/v1/dashboards/groups/performance/"


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Perf Org", slug="perf-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Perf Org Summer 2026", slug="summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


def _person(org, first, last, user=None):
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )


def _user(email: str):
    return User.objects.create_user(email=email, password="pw")


@pytest.fixture
def scored_camper_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Camper Daily", slug="camper-daily",
        cadence="daily",
        subject_mode="single_subject", assignment_scope="per_subject_in_group",
        assignment_group_types=["bunk"], author_role_filter=["counselor"],
        subject_role_filter=["camper"],
        schema={
            "fields": [
                {
                    "key": "overall",
                    "type": "single_rating",
                    "scale": [1, 5],
                    "prompts": {"en": "Overall"},
                },
            ],
        },
    )


@pytest.fixture
def unit_and_bunks(org, program):
    unit = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Unit Aleph",
        slug="unit-aleph", group_type="unit",
    )
    maple = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Maple",
        slug="bunk-maple", group_type="bunk", parent=unit,
    )
    return unit, maple


def _assign_template(org, program, template, *, group=None):
    TemplateAssignment.all_objects.create(
        organization=org,
        program=program,
        template=template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=group,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        status=TemplateAssignment.Status.ACTIVE,
    )


def test_supervisor_sees_supervised_bunk_with_completion(api_client, org, program, unit_and_bunks, scored_camper_template):
    unit, maple = unit_and_bunks
    day = date(2026, 7, 10)

    counselor_user = _user("counselor@test.com")
    counselor = _person(org, "Sam", "Counselor", user=counselor_user)
    uh_user = _user("uh@test.com")
    uh = _person(org, "Pat", "UnitHead", user=uh_user)

    Membership.all_objects.create(
        program=program, person=uh, role="unit_head", is_active=True,
    )
    Membership.all_objects.create(
        program=program, person=counselor, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=unit, person=uh, role_in_group="author", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=maple, person=counselor, role_in_group="author", is_active=True,
    )

    camper_a = _person(org, "Cam", "One")
    camper_b = _person(org, "Cam", "Two")
    for camper in (camper_a, camper_b):
        AssignmentGroupMembership.all_objects.create(
            group=maple, person=camper, role_in_group="subject", is_active=True,
        )

    _assign_template(org, program, scored_camper_template, group=maple)

    Reflection.all_objects.create(
        organization=org, program=program, template=scored_camper_template,
        subject=camper_a, author=counselor, assignment_group=maple,
        period_start=day, period_end=day,
        answers={"overall": 4}, language="en", is_complete=True,
    )

    api_client.force_authenticate(user=uh_user)
    resp = api_client.get(
        URL,
        {"date": day.isoformat(), "group_type": "bunk", "program": program.id},
        **_hdr(org.slug),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["program"]["name"] == "Perf Org Summer 2026"
    assert len(data["groups"]) == 1
    group = data["groups"][0]
    assert group["name"] == "Bunk Maple"
    assert group["parent_name"] == "Unit Aleph"
    assert group["author_names"] == ["Sam C."]
    assert group["completion"]["submitted"] == 1
    assert group["completion"]["expected"] == 2
    assert group["completion"]["percent"] == 50
    assert group["completion"]["is_complete"] is False
    assert group["scores"]["distribution"]["4"] == 1


def test_unauthorized_viewer_gets_empty_groups(api_client, org, program, unit_and_bunks, scored_camper_template):
    _, maple = unit_and_bunks
    stranger_user = _user("stranger@test.com")
    _person(org, "Str", "Anger", user=stranger_user)
    _assign_template(org, program, scored_camper_template, group=maple)

    api_client.force_authenticate(user=stranger_user)
    resp = api_client.get(URL, **_hdr(org.slug))
    assert resp.status_code == 200
    assert resp.json()["groups"] == []

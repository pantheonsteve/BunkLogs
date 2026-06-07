"""Tests for /api/v1/dashboards/groups/performance/."""
from __future__ import annotations

from datetime import date
from datetime import timedelta

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
from bunk_logs.core.models import Supervision
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.time_utils import get_today

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
    assert group["program_name"] == "Perf Org Summer 2026"
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


def _setup_admin(api_client, org, program):
    admin_user = _user("admin@perf.com")
    admin = _person(org, "Ad", "Min", user=admin_user)
    Membership.all_objects.create(
        program=program, person=admin, role="admin", is_active=True,
    )
    api_client.force_authenticate(user=admin_user)
    return admin_user


def test_defaults_to_current_program_without_filter(
    api_client, org, unit_and_bunks, scored_camper_template,
):
    """Omitting ?program= scopes groups to the program active today."""
    unit, maple = unit_and_bunks
    today = get_today(org)
    program = maple.program
    program.start_date = today - timedelta(days=5)
    program.end_date = today + timedelta(days=10)
    program.save(update_fields=["start_date", "end_date"])

    program2 = Program.all_objects.create(
        organization=org, name="Perf Org Session 2", slug="session-2",
        program_type="summer_camp",
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=10),
    )
    AssignmentGroup.all_objects.create(
        organization=org, program=program2, name="Bunk Birch",
        slug="bunk-birch", group_type="bunk",
    )
    _setup_admin(api_client, org, program)

    resp = api_client.get(
        URL, {"group_type": "bunk", "date": today.isoformat()}, **_hdr(org.slug),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_program"]["id"] == program.id
    assert data["program"]["id"] == program.id
    assert {g["name"] for g in data["groups"]} == {"Bunk Maple"}
    assert data["today"] == today.isoformat()
    prog = data["programs"][0]
    assert "start_date" in prog
    assert "end_date" in prog
    assert "is_active" in prog


def test_explicit_past_program_filter(
    api_client, org, scored_camper_template,
):
    today = get_today(org)
    past_program = Program.all_objects.create(
        organization=org, name="Perf Org Past", slug="past-session",
        program_type="summer_camp",
        start_date=today - timedelta(days=60),
        end_date=today - timedelta(days=31),
    )
    past_bunk = AssignmentGroup.all_objects.create(
        organization=org, program=past_program, name="Bunk Past",
        slug="bunk-past", group_type="bunk",
    )
    _assign_template(org, past_program, scored_camper_template, group=past_bunk)
    _setup_admin(api_client, org, past_program)

    resp = api_client.get(
        URL,
        {
            "group_type": "bunk",
            "program": past_program.id,
            "date": past_program.end_date.isoformat(),
        },
        **_hdr(org.slug),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["program"]["id"] == past_program.id
    assert data["current_program"] is None
    assert {g["name"] for g in data["groups"]} == {"Bunk Past"}


def test_no_current_program_returns_empty_groups(
    api_client, org, scored_camper_template,
):
    today = get_today(org)
    past_program = Program.all_objects.create(
        organization=org, name="Perf Org Only Past", slug="only-past",
        program_type="summer_camp",
        start_date=today - timedelta(days=60),
        end_date=today - timedelta(days=31),
    )
    past_bunk = AssignmentGroup.all_objects.create(
        organization=org, program=past_program, name="Bunk Old",
        slug="bunk-old", group_type="bunk",
    )
    _assign_template(org, past_program, scored_camper_template, group=past_bunk)
    _setup_admin(api_client, org, past_program)

    resp = api_client.get(
        URL, {"group_type": "bunk", "date": today.isoformat()}, **_hdr(org.slug),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_program"] is None
    assert data["program"] is None
    assert data["groups"] == []
    assert len(data["programs"]) == 1


def test_uh_supervision_only_sees_bunk_and_parent_unit(
    api_client, org, program, unit_and_bunks,
):
    """UH with Supervision to bunk (no AGM author) sees bunk + parent unit."""
    unit, maple = unit_and_bunks
    birch = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Birch",
        slug="bunk-birch", group_type="bunk", parent=unit,
    )
    uh_user = _user("uh-super@test.com")
    uh = _person(org, "Pat", "Supervisor", user=uh_user)
    uh_membership = Membership.all_objects.create(
        program=program, person=uh, role="unit_head", is_active=True,
    )
    Supervision.all_objects.create(
        supervisor_membership=uh_membership,
        target_type=Supervision.TargetType.BUNK,
        target_bunk=maple,
        start_date=date(2026, 6, 1),
    )

    api_client.force_authenticate(user=uh_user)
    resp = api_client.get(
        URL,
        {"group_type": "bunk", "program": program.id, "date": "2026-07-10"},
        **_hdr(org.slug),
    )
    assert resp.status_code == 200
    names = {g["name"] for g in resp.json()["groups"]}
    assert names == {"Bunk Maple"}
    assert "roster" in resp.json()["groups"][0]

    resp_unit = api_client.get(
        URL,
        {"group_type": "unit", "program": program.id, "date": "2026-07-10"},
        **_hdr(org.slug),
    )
    assert {g["name"] for g in resp_unit.json()["groups"]} == {"Unit Aleph"}

    resp_all = api_client.get(
        URL,
        {"program": program.id, "date": "2026-07-10"},
        **_hdr(org.slug),
    )
    all_names = {g["name"] for g in resp_all.json()["groups"]}
    assert "Bunk Maple" in all_names
    assert "Unit Aleph" in all_names
    assert "Bunk Birch" not in all_names


def test_cc_caseload_only_sees_assigned_bunks(api_client, org, program, unit_and_bunks):
    unit, maple = unit_and_bunks
    cc_user = _user("cc@test.com")
    cc = _person(org, "Care", "Staff", user=cc_user)
    cc_membership = Membership.all_objects.create(
        program=program, person=cc, role="camper_care", is_active=True,
    )
    Supervision.all_objects.create(
        supervisor_membership=cc_membership,
        target_type=Supervision.TargetType.BUNK,
        target_bunk=maple,
        start_date=date(2026, 6, 1),
    )

    api_client.force_authenticate(user=cc_user)
    resp = api_client.get(
        URL,
        {"group_type": "bunk", "program": program.id, "date": "2026-07-10"},
        **_hdr(org.slug),
    )
    assert resp.status_code == 200
    assert {g["name"] for g in resp.json()["groups"]} == {"Bunk Maple"}


def test_leadership_team_sees_all_program_bunks(
    api_client, org, program, unit_and_bunks,
):
    unit, maple = unit_and_bunks
    AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Birch",
        slug="bunk-birch", group_type="bunk", parent=unit,
    )
    lt_user = _user("lt@test.com")
    lt = _person(org, "Lead", "Team", user=lt_user)
    Membership.all_objects.create(
        program=program, person=lt, role="leadership_team", is_active=True,
    )

    api_client.force_authenticate(user=lt_user)
    resp = api_client.get(
        URL,
        {"group_type": "bunk", "program": program.id, "date": "2026-07-10"},
        **_hdr(org.slug),
    )
    assert resp.status_code == 200
    assert {g["name"] for g in resp.json()["groups"]} == {"Bunk Maple", "Bunk Birch"}


def test_counselor_sees_only_own_bunk_not_sibling(
    api_client, org, program, unit_and_bunks,
):
    unit, maple = unit_and_bunks
    birch = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Birch",
        slug="bunk-birch", group_type="bunk", parent=unit,
    )
    counselor_user = _user("counselor-only@test.com")
    counselor = _person(org, "Sam", "Counselor", user=counselor_user)
    Membership.all_objects.create(
        program=program, person=counselor, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=maple, person=counselor, role_in_group="author", is_active=True,
    )

    api_client.force_authenticate(user=counselor_user)
    resp = api_client.get(
        URL,
        {"group_type": "bunk", "program": program.id, "date": "2026-07-10"},
        **_hdr(org.slug),
    )
    assert resp.status_code == 200
    names = {g["name"] for g in resp.json()["groups"]}
    assert names == {"Bunk Maple"}
    assert "Bunk Birch" not in names

    resp_unit = api_client.get(
        URL,
        {"group_type": "unit", "program": program.id, "date": "2026-07-10"},
        **_hdr(org.slug),
    )
    assert resp_unit.json()["groups"] == []

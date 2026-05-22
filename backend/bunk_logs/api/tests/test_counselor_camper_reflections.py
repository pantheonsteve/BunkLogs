"""Tests for ``GET /api/v1/counselor/camper-reflections/?date=`` (Story 3).

Covers roster shape, submitter attribution rules, off-camp segregation,
date param parsing, and the read-only flag for past dates.
"""
from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import CamperDayState
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()

SCHEMA = {
    "fields": [
        {"key": "note", "type": "textarea", "required": False, "prompts": {"en": "Notes"}},
    ],
}


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="CR Camp", slug="cr-camp", settings={"rollover_hour": 0, "timezone": "UTC"})


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="CR Camp Summer 2026",
        slug="cr-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="cnsl@cr.test", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org,
        first_name="Mira",
        last_name="Sand",
        user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )


@pytest.fixture
def bunk(org, program):
    return AssignmentGroup.objects.create(
        organization=org,
        program=program,
        name="Bunk Cedar",
        slug="bunk-cedar",
        group_type="bunk",
        is_active=True,
    )


@pytest.fixture
def counselor_as_author(bunk, counselor_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk, person=counselor_person, role_in_group="author", is_active=True,
    )


@pytest.fixture
def co_counselor_person(org):
    user = User.objects.create_user(email="co@cr.test", password="pw")
    return Person.all_objects.create(
        organization=org, first_name="Jordan", last_name="Patel", user=user,
    )


@pytest.fixture
def co_counselor_membership(program, co_counselor_person):
    return Membership.all_objects.create(
        program=program, person=co_counselor_person, role="counselor", is_active=True,
    )


@pytest.fixture
def co_as_author(bunk, co_counselor_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk, person=co_counselor_person, role_in_group="author", is_active=True,
    )


@pytest.fixture
def campers(org, bunk):
    persons = []
    for first, last in [("Sarah", "Levin"), ("Maya", "Cohen")]:
        p = Person.all_objects.create(
            organization=org, first_name=first, last_name=last, preferred_name=first,
        )
        AssignmentGroupMembership.objects.create(
            group=bunk, person=p, role_in_group="subject", is_active=True,
        )
        persons.append(p)
    return persons


@pytest.fixture
def template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Bunk Log",
        slug="bunk-log-cr",
        cadence="daily",
        subject_mode="single_subject",
        assignment_group_types=["bunk"],
        schema=SCHEMA,
        languages=["en"],
        is_active=True,
        program_type="summer_camp",
        author_role_filter=["counselor"],
    )


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


# ---------------------------------------------------------------------------
# Roster shape
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_returns_one_bunk_with_two_campers(
    org, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, template,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/camper-reflections/")
    assert resp.status_code == 200
    assert len(resp.data["bunks"]) == 1
    bunk_row = resp.data["bunks"][0]
    assert bunk_row["name"] == "Bunk Cedar"
    assert bunk_row["total"] == 2
    assert bunk_row["covered"] == 0
    names = {row["name"] for row in bunk_row["campers"]}
    assert "Sarah L." in names
    assert "Maya C." in names


@pytest.mark.django_db
def test_list_shows_submitter_when_not_self(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author,
    co_counselor_person, co_counselor_membership, co_as_author,
    campers, template,
):
    today = date.today()
    Reflection.all_objects.create(
        organization=org,
        program=program,
        author=co_counselor_person,
        subject=campers[0],
        assignment_group=bunk,
        template=template,
        period_start=today,
        period_end=today,
        answers={"note": "ok"},
        is_complete=True,
        language="en",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/camper-reflections/")
    rows = resp.data["bunks"][0]["campers"]
    sarah = next(r for r in rows if r["name"] == "Sarah L.")
    assert sarah["submitted"] is True
    assert sarah["submitter"]["is_self"] is False
    assert sarah["submitter"]["name"] == "Jordan P."


@pytest.mark.django_db
def test_list_hides_submitter_name_when_self(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, template,
):
    today = date.today()
    Reflection.all_objects.create(
        organization=org,
        program=program,
        author=counselor_person,
        subject=campers[0],
        assignment_group=bunk,
        template=template,
        period_start=today,
        period_end=today,
        answers={"note": "ok"},
        is_complete=True,
        language="en",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/camper-reflections/")
    rows = resp.data["bunks"][0]["campers"]
    sarah = next(r for r in rows if r["name"] == "Sarah L.")
    assert sarah["submitted"] is True
    assert sarah["submitter"]["is_self"] is True
    assert sarah["submitter"]["name"] is None


# ---------------------------------------------------------------------------
# Off-camp handling
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_segregates_off_camp_campers(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, template,
):
    today = date.today()
    CamperDayState.objects.create(
        organization=org, program=program, camper=campers[-1], date=today, is_off_camp=True,
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/camper-reflections/")
    bunk_row = resp.data["bunks"][0]
    assert bunk_row["total"] == 1  # off-camp removed
    assert len(bunk_row["off_camp"]) == 1
    assert bunk_row["off_camp"][0]["preferred_name"] == "Maya"


# ---------------------------------------------------------------------------
# Date parameter / editability
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_rejects_invalid_date(
    org, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, template,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/camper-reflections/?date=nope")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_list_for_past_date_marks_not_editable(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, campers, template,
):
    yesterday = date.today() - timedelta(days=1)
    Reflection.all_objects.create(
        organization=org,
        program=program,
        author=counselor_person,
        subject=campers[0],
        assignment_group=bunk,
        template=template,
        period_start=yesterday,
        period_end=yesterday,
        answers={"note": "ok"},
        is_complete=True,
        language="en",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/counselor/camper-reflections/?date={yesterday.isoformat()}")
    assert resp.data["editable"] is False
    rows = resp.data["bunks"][0]["campers"]
    submitted_row = next(r for r in rows if r["submitted"])
    assert submitted_row["editable"] is False


@pytest.mark.django_db
def test_list_no_membership_returns_empty(org, counselor_user, counselor_person):
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/camper-reflections/")
    assert resp.status_code == 200
    assert resp.data["bunks"] == []

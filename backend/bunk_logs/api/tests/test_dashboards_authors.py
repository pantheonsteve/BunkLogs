"""Tests for /api/v1/dashboards/authors/."""
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

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Au Org", slug="au-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Au Org Summer", slug="au-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


def _person(org, first, last, user=None):
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )


def _user(email):
    return User.objects.create_user(email=email, password="pw")


def _bunk_obs(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Bunk Obs", slug="au-bunk-obs",
        cadence="daily",
        subject_mode="single_subject", assignment_scope="per_subject_in_group",
        assignment_group_types=["bunk"],
        author_role_filter=["counselor"], subject_role_filter=["camper"],
        schema={"fields": [{"key": "n", "type": "text", "prompts": {"en": "n"}}]},
    )


@pytest.fixture
def setup(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk",
        slug="au-bunk", group_type="bunk",
    )


def test_lone_counselor_blocked_403(api_client, org, program, setup):
    """A counselor with a single bunk and no descendants is not a 'supervisor'."""
    bunk = setup
    cu = _user("cns@a.com")
    p = _person(org, "C", "Ns", cu)
    Membership.all_objects.create(
        program=program, person=p, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=p, role_in_group="author", is_active=True,
    )
    api_client.force_authenticate(user=cu)
    r = api_client.get("/api/v1/dashboards/authors/", **_hdr(org.slug))
    assert r.status_code == 403


def test_unit_head_with_descendant_bunks_allowed(api_client, org, program):
    unit = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="U",
        slug="au-unit", group_type="unit",
    )
    AssignmentGroup.all_objects.create(
        organization=org, program=program, name="B",
        slug="au-b", group_type="bunk", parent=unit,
    )
    uhu = _user("uh@a.com")
    p = _person(org, "U", "H", uhu)
    Membership.all_objects.create(
        program=program, person=p, role="unit_head", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=unit, person=p, role_in_group="author", is_active=True,
    )
    api_client.force_authenticate(user=uhu)
    r = api_client.get("/api/v1/dashboards/authors/", **_hdr(org.slug))
    assert r.status_code == 200


def test_admin_allowed_and_sees_per_author_counts(api_client, org, program, setup):
    bunk = setup
    tpl = _bunk_obs(org)
    # Counselors A and B both submitting reflections
    a_user = _user("a@a.com")
    a = _person(org, "Cou", "A", a_user)
    Membership.all_objects.create(
        program=program, person=a, role="counselor", is_active=True,
    )
    b_user = _user("b@a.com")
    b = _person(org, "Cou", "B", b_user)
    Membership.all_objects.create(
        program=program, person=b, role="counselor", is_active=True,
    )
    camper = _person(org, "Cam", "Per")
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=camper, role_in_group="subject", is_active=True,
    )
    today = date.today()
    for _ in range(3):
        Reflection.all_objects.create(
            organization=org, program=program, template=tpl,
            subject=camper, author=a, assignment_group=bunk,
            period_start=today, period_end=today, answers={"n": "x"},
            language="en", is_complete=True,
        )
    Reflection.all_objects.create(
        organization=org, program=program, template=tpl,
        subject=camper, author=b, assignment_group=bunk,
        period_start=today, period_end=today, answers={"n": "y"},
        language="en", is_complete=True,
    )

    admin_user = _user("admin@a.com")
    p = _person(org, "Ad", "Min", admin_user)
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    api_client.force_authenticate(user=admin_user)
    r = api_client.get(
        f"/api/v1/dashboards/authors/?date_start={today.isoformat()}"
        f"&date_end={today.isoformat()}",
        **_hdr(org.slug),
    )
    assert r.status_code == 200
    body = r.json()
    by_id = {row["author_id"]: row for row in body["authors"]}
    assert by_id[a.id]["total_reflections"] == 3
    assert by_id[b.id]["total_reflections"] == 1
    assert by_id[a.id]["per_day"][0]["count"] == 3


def test_assignment_group_filter(api_client, org, program, setup):
    bunk = setup
    other_bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Other",
        slug="au-other", group_type="bunk",
    )
    tpl = _bunk_obs(org)
    a_user = _user("a@a.com")
    a = _person(org, "Cou", "A", a_user)
    Membership.all_objects.create(
        program=program, person=a, role="counselor", is_active=True,
    )
    camper = _person(org, "Cam", "Per")
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=camper, role_in_group="subject", is_active=True,
    )
    today = date.today()
    Reflection.all_objects.create(
        organization=org, program=program, template=tpl,
        subject=camper, author=a, assignment_group=bunk,
        period_start=today, period_end=today, answers={"n": "x"},
        language="en", is_complete=True,
    )
    Reflection.all_objects.create(
        organization=org, program=program, template=tpl,
        subject=camper, author=a, assignment_group=other_bunk,
        period_start=today, period_end=today, answers={"n": "x"},
        language="en", is_complete=True,
    )
    admin_user = _user("admin@a.com")
    p = _person(org, "Ad", "Min", admin_user)
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    api_client.force_authenticate(user=admin_user)
    r = api_client.get(
        f"/api/v1/dashboards/authors/?assignment_group={bunk.id}"
        f"&date_start={today.isoformat()}&date_end={today.isoformat()}",
        **_hdr(org.slug),
    )
    body = r.json()
    by_id = {row["author_id"]: row for row in body["authors"]}
    assert by_id[a.id]["total_reflections"] == 1

"""Tests for /api/v1/dashboards/coverage/."""
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

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Cov Org", slug="cov-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Cov Org Summer", slug="cov-prog",
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
def bunk_obs_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Bunk Obs", slug="bunk-obs",
        cadence="daily",
        subject_mode="single_subject", assignment_scope="per_subject_in_group",
        assignment_group_types=["bunk"], author_role_filter=["counselor"],
        subject_role_filter=["camper"],
        schema={"fields": [{"key": "n", "type": "text", "prompts": {"en": "n"}}]},
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
    oak = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Oak",
        slug="bunk-oak", group_type="bunk", parent=unit,
    )
    return unit, maple, oak


def _add_subjects(group, persons):
    for p in persons:
        AssignmentGroupMembership.all_objects.create(
            group=group, person=p, role_in_group="subject", is_active=True,
        )


def _make_reflection(org, program, template, *, subject, author, group, day: date):
    return Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=subject, author=author, assignment_group=group,
        period_start=day, period_end=day,
        answers={"n": "ok"}, language="en", is_complete=True,
    )


# ── Visibility & permissions ──────────────────────────────────────────────────


def test_unauthenticated_returns_401(api_client, org):
    r = api_client.get("/api/v1/dashboards/coverage/", **_hdr(org.slug))
    assert r.status_code == 401


def test_user_with_no_supervised_groups_sees_empty_groups(
    api_client, org, program, unit_and_bunks, bunk_obs_template,
):
    u = _user("nobody@a.com")
    p = _person(org, "No", "Body", u)
    Membership.all_objects.create(
        program=program, person=p, role="counselor", is_active=True,
    )
    api_client.force_authenticate(user=u)
    r = api_client.get("/api/v1/dashboards/coverage/", **_hdr(org.slug))
    assert r.status_code == 200
    assert r.json()["groups"] == []


def test_org_admin_sees_all_groups(
    api_client, org, program, unit_and_bunks, bunk_obs_template,
):
    unit, maple, oak = unit_and_bunks
    u = _user("admin@a.com")
    p = _person(org, "Ad", "Min", u)
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    camper = _person(org, "Cam", "Per")
    _add_subjects(maple, [camper])
    api_client.force_authenticate(user=u)
    r = api_client.get("/api/v1/dashboards/coverage/", **_hdr(org.slug))
    assert r.status_code == 200
    body = r.json()
    names = {g["name"] for g in body["groups"]}
    assert {"Unit Aleph", "Bunk Maple", "Bunk Oak"} <= names


def test_unit_head_sees_unit_and_descendant_bunks(
    api_client, org, program, unit_and_bunks, bunk_obs_template,
):
    unit, maple, oak = unit_and_bunks
    u = _user("uh@a.com")
    p = _person(org, "U", "H", u)
    Membership.all_objects.create(
        program=program, person=p, role="unit_head", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=unit, person=p, role_in_group="author", is_active=True,
    )
    api_client.force_authenticate(user=u)
    r = api_client.get("/api/v1/dashboards/coverage/", **_hdr(org.slug))
    body = r.json()
    names = {g["name"] for g in body["groups"]}
    assert {"Unit Aleph", "Bunk Maple", "Bunk Oak"} <= names


def test_counselor_only_sees_own_bunk(
    api_client, org, program, unit_and_bunks, bunk_obs_template,
):
    unit, maple, oak = unit_and_bunks
    u = _user("cns@a.com")
    p = _person(org, "C", "Ns", u)
    Membership.all_objects.create(
        program=program, person=p, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=maple, person=p, role_in_group="author", is_active=True,
    )
    api_client.force_authenticate(user=u)
    r = api_client.get("/api/v1/dashboards/coverage/", **_hdr(org.slug))
    body = r.json()
    names = {g["name"] for g in body["groups"]}
    assert "Bunk Maple" in names
    assert "Bunk Oak" not in names


def test_group_type_filter(
    api_client, org, program, unit_and_bunks, bunk_obs_template,
):
    unit, maple, oak = unit_and_bunks
    u = _user("admin@a.com")
    p = _person(org, "Ad", "Min", u)
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    api_client.force_authenticate(user=u)
    r = api_client.get(
        "/api/v1/dashboards/coverage/?group_type=bunk", **_hdr(org.slug),
    )
    body = r.json()
    types = {g["group_type"] for g in body["groups"]}
    assert types == {"bunk"}


# ── Coverage percentages and tier mapping ────────────────────────────────────


def test_complete_day_returns_green(
    api_client, org, program, unit_and_bunks, bunk_obs_template,
):
    _, maple, _ = unit_and_bunks
    campers = [_person(org, f"C{i}", f"L{i}") for i in range(4)]
    _add_subjects(maple, campers)
    counselor = _person(org, "Co", "Un")
    Membership.all_objects.create(
        program=program, person=counselor, role="counselor", is_active=True,
    )
    today = date.today()
    for c in campers:
        _make_reflection(
            org, program, bunk_obs_template,
            subject=c, author=counselor, group=maple, day=today,
        )
    u = _user("admin@a.com")
    p = _person(org, "Ad", "Min", u)
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    api_client.force_authenticate(user=u)
    r = api_client.get(
        f"/api/v1/dashboards/coverage/?date_start={today.isoformat()}"
        f"&date_end={today.isoformat()}",
        **_hdr(org.slug),
    )
    body = r.json()
    maple_row = next(g for g in body["groups"] if g["name"] == "Bunk Maple")
    today_cell = maple_row["days"][0]
    assert today_cell["percent"] == 100
    assert today_cell["status"] == "green"


def test_partial_completion_tiers(
    api_client, org, program, unit_and_bunks, bunk_obs_template,
):
    _, maple, _ = unit_and_bunks
    campers = [_person(org, f"C{i}", f"L{i}") for i in range(10)]
    _add_subjects(maple, campers)
    counselor = _person(org, "Co", "Un")
    Membership.all_objects.create(
        program=program, person=counselor, role="counselor", is_active=True,
    )
    today = date.today()
    # 5 of 10 subjects covered = 50% -> orange
    for c in campers[:5]:
        _make_reflection(
            org, program, bunk_obs_template,
            subject=c, author=counselor, group=maple, day=today,
        )
    u = _user("admin@a.com")
    p = _person(org, "Ad", "Min", u)
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    api_client.force_authenticate(user=u)
    r = api_client.get(
        f"/api/v1/dashboards/coverage/?date_start={today.isoformat()}"
        f"&date_end={today.isoformat()}",
        **_hdr(org.slug),
    )
    body = r.json()
    maple_row = next(g for g in body["groups"] if g["name"] == "Bunk Maple")
    today_cell = maple_row["days"][0]
    assert today_cell["percent"] == 50
    assert today_cell["status"] == "orange"


def test_no_roster_returns_inactive_status(
    api_client, org, program, unit_and_bunks, bunk_obs_template,
):
    """A bunk with zero subject memberships shows 'inactive' on every day."""
    _, _, oak = unit_and_bunks
    u = _user("admin@a.com")
    p = _person(org, "Ad", "Min", u)
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    api_client.force_authenticate(user=u)
    today = date.today()
    r = api_client.get(
        f"/api/v1/dashboards/coverage/?date_start={today.isoformat()}"
        f"&date_end={today.isoformat()}",
        **_hdr(org.slug),
    )
    body = r.json()
    oak_row = next(g for g in body["groups"] if g["name"] == "Bunk Oak")
    assert oak_row["days"][0]["status"] == "inactive"


def test_org_summary_aggregates_across_groups(
    api_client, org, program, unit_and_bunks, bunk_obs_template,
):
    _, maple, oak = unit_and_bunks
    maple_subjects = [_person(org, f"M{i}", f"L{i}") for i in range(4)]
    oak_subjects = [_person(org, f"O{i}", f"L{i}") for i in range(4)]
    _add_subjects(maple, maple_subjects)
    _add_subjects(oak, oak_subjects)
    counselor = _person(org, "Co", "Un")
    Membership.all_objects.create(
        program=program, person=counselor, role="counselor", is_active=True,
    )
    today = date.today()
    # 4/4 maple, 2/4 oak -> 6/8 = 75%
    for c in maple_subjects:
        _make_reflection(
            org, program, bunk_obs_template,
            subject=c, author=counselor, group=maple, day=today,
        )
    for c in oak_subjects[:2]:
        _make_reflection(
            org, program, bunk_obs_template,
            subject=c, author=counselor, group=oak, day=today,
        )
    u = _user("admin@a.com")
    p = _person(org, "Ad", "Min", u)
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    api_client.force_authenticate(user=u)
    r = api_client.get(
        f"/api/v1/dashboards/coverage/?group_type=bunk"
        f"&date_start={today.isoformat()}&date_end={today.isoformat()}",
        **_hdr(org.slug),
    )
    body = r.json()
    assert body["org_summary"]["covered"] == 6
    assert body["org_summary"]["total"] == 8
    assert body["org_summary"]["percent"] == 75.0


def test_window_clamped_to_max(api_client, org, program, unit_and_bunks):
    u = _user("admin@a.com")
    p = _person(org, "Ad", "Min", u)
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    api_client.force_authenticate(user=u)
    end = date.today()
    start = end - timedelta(days=180)
    r = api_client.get(
        f"/api/v1/dashboards/coverage/?date_start={start.isoformat()}"
        f"&date_end={end.isoformat()}",
        **_hdr(org.slug),
    )
    assert r.status_code == 200
    body = r.json()
    # Window should have been clamped to MAX_WINDOW_DAYS = 60
    assert (date.fromisoformat(body["period"]["end"])
            - date.fromisoformat(body["period"]["start"])).days <= 59

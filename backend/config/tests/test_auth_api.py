"""Tests for the auth-status payload (per-org capability + membership roles)."""

import json
from datetime import date
from datetime import timedelta

import pytest
from django.test import RequestFactory

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.users.models import User
from config.auth_api import get_auth_status


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Test Camp", slug="test-camp")


@pytest.fixture
def program(db, org):
    return Program.all_objects.create(
        organization=org,
        name="Test Camp Summer",
        slug="summer",
        program_type="summer_camp",
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        is_active=True,
    )


@pytest.mark.django_db
def test_unauthenticated_returns_not_authenticated(rf):
    from django.contrib.auth.models import AnonymousUser

    request = rf.get("/fake/")
    request.user = AnonymousUser()
    response = get_auth_status(request)
    data = json.loads(response.content)
    assert data["isAuthenticated"] is False


@pytest.mark.django_db
def test_auth_status_includes_org_context(rf, org, program):
    user = User.objects.create_user(
        email="c@test.com", password="pass", first_name="Cara", last_name="C",
    )
    person = Person.all_objects.create(
        organization=org, first_name="Cara", last_name="C", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )

    request = rf.get("/fake/")
    request.user = user
    data = json.loads(get_auth_status(request).content)

    assert data["isAuthenticated"] is True
    assert data["user"]["membership_roles"] == ["counselor"]
    orgs = data["user"]["organizations"]
    assert len(orgs) == 1
    assert orgs[0]["slug"] == "test-camp"
    assert orgs[0]["capability"] == "participant"
    assert orgs[0]["roles"] == ["counselor"]


@pytest.mark.django_db
def test_auth_status_no_memberships_yields_empty_org_context(rf):
    user = User.objects.create_user(email="lonely@test.com", password="pass")

    request = rf.get("/fake/")
    request.user = user
    data = json.loads(get_auth_status(request).content)

    assert data["isAuthenticated"] is True
    assert data["user"]["membership_roles"] == []
    assert data["user"]["organizations"] == []


@pytest.mark.django_db
def test_stale_higher_priority_role_does_not_shadow_current_operational_role(
    rf, org,
):
    """Regression test: a person reassigned between sessions should surface
    their CURRENT role, not a stale higher-priority role left active on an
    ended program (e.g. a Session 1 leadership_team membership that outranks
    a Session 2 unit_head membership in the frontend's home-routing priority
    list, per the "Carly Kahan can't see her bunks" incident).
    """
    ended_program = Program.all_objects.create(
        organization=org,
        name="Test Camp - Session 1",
        slug="session-1",
        program_type="summer_camp",
        start_date=date.today() - timedelta(days=60),
        end_date=date.today() - timedelta(days=30),
        is_active=True,
    )
    current_program = Program.all_objects.create(
        organization=org,
        name="Test Camp - Session 2",
        slug="session-2",
        program_type="summer_camp",
        start_date=date.today() - timedelta(days=5),
        end_date=date.today() + timedelta(days=25),
        is_active=True,
    )
    user = User.objects.create_user(
        email="carly@test.com", password="pass", first_name="Carly", last_name="K",
    )
    person = Person.all_objects.create(
        organization=org, first_name="Carly", last_name="K", user=user,
    )
    # Stale leadership_team role from the ended session -- never deactivated.
    Membership.all_objects.create(
        program=ended_program, person=person, role="leadership_team", is_active=True,
    )
    # Current, correct role for the running session.
    Membership.all_objects.create(
        program=current_program, person=person, role="unit_head", is_active=True,
    )

    request = rf.get("/fake/")
    request.user = user
    data = json.loads(get_auth_status(request).content)

    orgs = data["user"]["organizations"]
    assert len(orgs) == 1
    # Only the operational (Session 2) role should surface, not the stale one.
    assert orgs[0]["roles"] == ["unit_head"]
    assert orgs[0]["capability"] == "supervisor"
    assert data["user"]["membership_roles"] == ["unit_head"]


@pytest.mark.django_db
def test_no_operational_program_falls_back_to_all_active_roles(rf, org):
    """Between sessions (no program currently operational), roles should
    still surface from all active memberships rather than going empty.
    """
    ended_program = Program.all_objects.create(
        organization=org,
        name="Test Camp - Session 1",
        slug="session-1",
        program_type="summer_camp",
        start_date=date.today() - timedelta(days=60),
        end_date=date.today() - timedelta(days=30),
        is_active=True,
    )
    user = User.objects.create_user(email="offseason@test.com", password="pass")
    person = Person.all_objects.create(
        organization=org, first_name="Off", last_name="Season", user=user,
    )
    Membership.all_objects.create(
        program=ended_program, person=person, role="admin", is_active=True,
    )

    request = rf.get("/fake/")
    request.user = user
    data = json.loads(get_auth_status(request).content)

    assert data["user"]["organizations"][0]["roles"] == ["admin"]
    assert data["user"]["membership_roles"] == ["admin"]

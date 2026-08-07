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

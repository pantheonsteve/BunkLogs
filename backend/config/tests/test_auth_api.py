"""Tests for config.auth_api (step 6_2 legacy cleanup)."""

import json

import pytest
from django.contrib.auth.models import AnonymousUser
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
    return Organization.objects.create(name="Test Org", slug="test-org")


@pytest.fixture
def program(db, org):
    from datetime import date
    from datetime import timedelta

    today = date.today()
    return Program.objects.create(
        organization=org,
        name="Test Org Summer",
        slug="summer",
        program_type="summer_camp",
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=60),
    )


@pytest.mark.django_db
def test_unauthenticated_returns_not_authenticated(rf):
    request = rf.get("/fake/")
    request.user = AnonymousUser()
    response = get_auth_status(request)
    data = json.loads(response.content)
    assert data["isAuthenticated"] is False


@pytest.mark.django_db
def test_authenticated_user_includes_membership_roles(rf, org, program):
    user = User.objects.create_user(
        email="maint@test.com",
        password="pass",
        role=User.COUNSELOR,
    )
    person = Person.objects.create(
        organization=org,
        first_name="M",
        last_name="T",
        user=user,
    )
    Membership.objects.create(
        program=program,
        person=person,
        role="maintenance",
        capability="participant",
        is_active=True,
    )

    request = rf.get("/fake/")
    request.user = user
    response = get_auth_status(request)
    data = json.loads(response.content)

    assert data["isAuthenticated"] is True
    assert data["user"]["membership_roles"] == ["maintenance"]

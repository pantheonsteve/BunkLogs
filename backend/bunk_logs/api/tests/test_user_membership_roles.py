"""Profile payload exposes active Membership roles for frontend nav gating."""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def org():
    return Organization.objects.create(name="MR Org", slug="mr-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="MR Org Summer",
        slug="mr-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


def _make_member(org, program, email, role):
    user = User.objects.create_user(email=email, password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="M", last_name="R", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role=role, is_active=True,
    )
    return user


def test_membership_roles_in_profile(org, program):
    user = _make_member(org, program, "maint-roles@mr.com", "maintenance")
    api = APIClient()
    api.force_authenticate(user=user)
    r = api.get(f"/api/v1/users/email/{user.email}/")
    assert r.status_code == 200, r.content
    assert "maintenance" in r.json()["membership_roles"]


def test_membership_roles_in_token_login(org, program):
    user = _make_member(org, program, "maint-token@mr.com", "maintenance")
    api = APIClient()
    r = api.post("/api/auth/token/", {"email": user.email, "password": "pw"}, format="json")
    assert r.status_code == 200, r.content
    assert "maintenance" in r.json()["user"]["membership_roles"]


def test_no_memberships_returns_empty_list(org):
    user = User.objects.create_user(email="no-member@mr.com", password="pw")
    api = APIClient()
    api.force_authenticate(user=user)
    r = api.get(f"/api/v1/users/email/{user.email}/")
    assert r.status_code == 200, r.content
    assert r.json()["membership_roles"] == []

"""Tests for operational-program scoping on dashboard group lists."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.api.tests.conftest import make_active_assignment
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.time_utils import get_today

User = get_user_model()
pytestmark = pytest.mark.django_db

DASHBOARD_URL = "/api/v1/counselor/dashboard/"
MY_TASKS_URL = "/api/v1/reflections/my-tasks/"

SELF_SCHEMA = {
    "fields": [
        {"key": "note", "type": "textarea", "required": False, "prompts": {"en": "Note"}},
    ],
}


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="Scope Org",
        slug="scope-org",
        settings={"rollover_hour": 0, "timezone": "UTC"},
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="scope-counselor@test.com", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org,
        first_name="Sam",
        last_name="Lee",
        user=counselor_user,
    )


def _operational_program(org, *, slug: str, name: str) -> Program:
    today = get_today(org)
    return Program.all_objects.create(
        organization=org,
        name=name,
        slug=slug,
        program_type="summer_camp",
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=60),
        is_active=True,
    )


def _ended_program(org, *, slug: str, name: str) -> Program:
    today = get_today(org)
    return Program.all_objects.create(
        organization=org,
        name=name,
        slug=slug,
        program_type="summer_camp",
        start_date=today - timedelta(days=120),
        end_date=today - timedelta(days=30),
        is_active=False,
    )


def _author_bunk(org, program, person, *, name: str) -> AssignmentGroup:
    bunk = AssignmentGroup.objects.create(
        organization=org,
        program=program,
        name=name,
        slug=name.lower().replace(" ", "-"),
        group_type="bunk",
        is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk,
        person=person,
        role_in_group="author",
        is_active=True,
    )
    return bunk


def test_counselor_dashboard_shows_bunk_in_operational_program(
    api_client, org, counselor_user, counselor_person,
):
    program = _operational_program(org, slug="current", name="Scope Org Current")
    Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )
    _author_bunk(org, program, counselor_person, name="Maple")

    api_client.force_authenticate(user=counselor_user)
    with organization_context(org):
        resp = api_client.get(f"{DASHBOARD_URL}?nocache=1", **_hdr(org.slug))

    assert resp.status_code == 200
    bunk_names = [b["name"] for b in resp.json()["bunks"]]
    assert bunk_names == ["Maple"]


def test_counselor_dashboard_hides_bunk_in_ended_program(
    api_client, org, counselor_user, counselor_person,
):
    current = _operational_program(org, slug="current", name="Scope Org Current")
    ended = _ended_program(org, slug="past", name="Scope Org Past")
    Membership.all_objects.create(
        program=current, person=counselor_person, role="counselor", is_active=True,
    )
    Membership.all_objects.create(
        program=ended, person=counselor_person, role="counselor", is_active=True,
    )
    _author_bunk(org, current, counselor_person, name="Maple")
    _author_bunk(org, ended, counselor_person, name="Old Birch")

    api_client.force_authenticate(user=counselor_user)
    with organization_context(org):
        resp = api_client.get(f"{DASHBOARD_URL}?nocache=1", **_hdr(org.slug))

    assert resp.status_code == 200
    bunk_names = [b["name"] for b in resp.json()["bunks"]]
    assert bunk_names == ["Maple"]


def test_counselor_dashboard_empty_when_only_ended_memberships(
    api_client, org, counselor_user, counselor_person,
):
    ended = _ended_program(org, slug="past-only", name="Scope Org Past Only")
    Membership.all_objects.create(
        program=ended, person=counselor_person, role="counselor", is_active=True,
    )
    _author_bunk(org, ended, counselor_person, name="Old Birch")

    api_client.force_authenticate(user=counselor_user)
    with organization_context(org):
        resp = api_client.get(f"{DASHBOARD_URL}?nocache=1", **_hdr(org.slug))

    assert resp.status_code == 200
    body = resp.json()
    assert body["bunks"] == []
    assert body["viewer"]["role"] is None


def test_my_tasks_excludes_assignments_in_ended_program(
    api_client, org, counselor_user, counselor_person,
):
    current = _operational_program(org, slug="tasks-current", name="Scope Org Tasks Current")
    ended = _ended_program(org, slug="tasks-past", name="Scope Org Tasks Past")
    Membership.all_objects.create(
        program=current, person=counselor_person, role="counselor", is_active=True,
    )
    Membership.all_objects.create(
        program=ended, person=counselor_person, role="counselor", is_active=True,
    )

    current_tpl = ReflectionTemplate.all_objects.create(
        organization=org,
        name="Current self tpl",
        slug="scope-current-self",
        cadence="daily",
        role="counselor",
        subject_mode="self",
        schema=SELF_SCHEMA,
        is_active=True,
    )
    ended_tpl = ReflectionTemplate.all_objects.create(
        organization=org,
        name="Ended self tpl",
        slug="scope-ended-self",
        cadence="daily",
        role="counselor",
        subject_mode="self",
        schema=SELF_SCHEMA,
        is_active=True,
    )
    make_active_assignment(
        template=current_tpl,
        program=current,
        target_role="counselor",
    )
    make_active_assignment(
        template=ended_tpl,
        program=ended,
        target_role="counselor",
    )

    api_client.force_authenticate(user=counselor_user)
    with organization_context(org):
        resp = api_client.get(MY_TASKS_URL, **_hdr(org.slug))

    assert resp.status_code == 200
    task_names = [t["template"]["name"] for t in resp.json()["tasks"]]
    assert "Current self tpl" in task_names
    assert "Ended self tpl" not in task_names

"""Tests for ``GET /api/v1/faculty/dashboard/`` — Step 7_24.

Coverage
--------
* faculty sees a card per classroom they author, carrying weekly
  completion, next-session availability, and the open-challenge count.
* only classrooms the viewer authors appear (a room they don't teach is
  invisible even inside the same program).
* madrich and counselor get 403 -- the faculty role gates the endpoint.
* faculty holding no classrooms gets an empty list, not an error.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import ClassroomChallenge
from bunk_logs.core.models import MadrichAvailability
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.time_utils import get_today

User = get_user_model()
pytestmark = pytest.mark.django_db

URL = "/api/v1/faculty/dashboard/"


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Faculty Home TBE", slug="faculty-home-tbe")


@pytest.fixture
def next_sunday(org):
    today = get_today(org)
    return today + timedelta(days=(6 - today.weekday()) % 7 or 7)


@pytest.fixture
def program(org, next_sunday):
    today = get_today(org)
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Religious School",
        slug="faculty-home-rs",
        program_type="religious_school",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=200),
        settings={"session_dates": [next_sunday.isoformat()]},
    )


@pytest.fixture
def classroom(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Tzedakah 101",
        slug="tzedakah-101", group_type="classroom", is_active=True,
    )


def _make_person(org, *, first, last, email=None):
    user = User.objects.create_user(email=email, password="pw") if email else None
    person = Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )
    return person, user


def _enroll_madrich(org, program, classroom, *, first):
    person, _ = _make_person(org, first=first, last="Rich")
    Membership.all_objects.create(
        program=program, person=person, role="madrich",
        grade_level=10, is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=classroom, person=person, role_in_group="subject", is_active=True,
    )
    return person


def _authenticate(api, org, program, *, role, email, classroom=None):
    person, user = _make_person(org, first="Fay", last="Viewer", email=email)
    Membership.all_objects.create(
        program=program, person=person, role=role, is_active=True,
    )
    if classroom is not None:
        AssignmentGroupMembership.all_objects.create(
            group=classroom, person=person,
            role_in_group="author", is_active=True,
        )
    api.force_authenticate(user=user)
    return person


def _get(api, org):
    with organization_context(org):
        return api.get(URL, **_hdr(org.slug))


class TestFacultyDashboard:
    def test_classroom_card_carries_every_signal(
        self, api, org, program, classroom, next_sunday,
    ):
        filed = _enroll_madrich(org, program, classroom, first="Ari")
        missing = _enroll_madrich(org, program, classroom, first="Bex")
        today = get_today(org)
        monday = today - timedelta(days=today.weekday())
        template = ReflectionTemplate.all_objects.get(
            slug="tbe-madrich-3-2-1-weekly",
        )
        Reflection.all_objects.create(
            organization=org, program=program, template=template,
            author=filed, subject=filed,
            period_start=monday, period_end=monday + timedelta(days=6),
            answers={}, language="en", is_complete=True,
        )
        MadrichAvailability.objects.create(
            organization=org, program=program, person=filed,
            session_date=next_sunday,
            status=MadrichAvailability.STATUS_AVAILABLE,
        )
        faculty = _authenticate(
            api, org, program, role="faculty",
            email="fac-home@tbe.test", classroom=classroom,
        )
        ClassroomChallenge.objects.create(
            organization=org, program=program, assignment_group=classroom,
            author=missing, category="behavior", session_date=today,
            body="Need help with a group dynamic.",
            status=ClassroomChallenge.STATUS_OPEN,
        )

        resp = _get(api, org)
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["header"]["role_label"] == "Faculty"
        assert body["header"]["name"] == "Fay Viewer"
        assert body["header"]["program_name"] == program.name

        assert len(body["classrooms"]) == 1
        card = body["classrooms"][0]
        assert card["id"] == classroom.id
        assert card["name"] == "Tzedakah 101"
        assert card["url"] == f"/dashboards/group/{classroom.id}"
        assert card["subject_count"] == 2
        assert card["reflections"] == {
            "submitted": 1,
            "expected": 2,
            "template_name": template.name,
        }
        assert card["availability"] == {
            "date": next_sunday.isoformat(),
            "available": 1,
            "unset": 1,
        }
        assert card["open_challenge_count"] == 1
        assert faculty.id  # sanity: the viewer resolved to a Person

    def test_only_authored_classrooms_appear(
        self, api, org, program, classroom,
    ):
        other = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Torah 201",
            slug="torah-201", group_type="classroom", is_active=True,
        )
        _enroll_madrich(org, program, other, first="Cy")
        _authenticate(
            api, org, program, role="faculty",
            email="fac-scope@tbe.test", classroom=classroom,
        )
        resp = _get(api, org)
        assert resp.status_code == 200, resp.content
        names = [c["name"] for c in resp.json()["classrooms"]]
        assert names == ["Tzedakah 101"]

    def test_faculty_without_classrooms_gets_empty_list(
        self, api, org, program,
    ):
        _authenticate(
            api, org, program, role="faculty", email="fac-empty@tbe.test",
        )
        resp = _get(api, org)
        assert resp.status_code == 200, resp.content
        assert resp.json()["classrooms"] == []

    @pytest.mark.parametrize("role", ["madrich", "counselor"])
    def test_non_faculty_denied(self, api, org, program, classroom, role):
        _authenticate(
            api, org, program, role=role,
            email=f"{role}-home@tbe.test", classroom=classroom,
        )
        assert _get(api, org).status_code == 403

    def test_anonymous_denied(self, api, org):
        assert _get(api, org).status_code in (401, 403)

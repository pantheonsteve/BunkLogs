"""Tests for the classroom-scoped faculty availability view — Step 4_7 AC4.4.

Coverage
--------
* faculty classroom author sees only the Madrichim who are ``subject``
  members of that same classroom (never the full-org matrix).
* faculty gets 403 hitting the org-admin matrix endpoint.
* a non-author (or non-faculty/madrich role) gets 403 on the classroom
  endpoint.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import MadrichAvailability
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.time_utils import get_today

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Faculty Availability TBE", slug="faculty-availability-tbe")


@pytest.fixture
def session_dates(org):
    today = get_today(org)
    first = today + timedelta(days=(6 - today.weekday()) % 7 + 14)
    return [first, first + timedelta(days=7)]


@pytest.fixture
def program(org, session_dates):
    today = get_today(org)
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Religious School",
        slug="faculty-availability-rs",
        program_type="religious_school",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=200),
        settings={"session_dates": [d.isoformat() for d in session_dates]},
    )


@pytest.fixture
def classroom(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Grade 5 Classroom",
        slug="grade-5-classroom", group_type="classroom",
    )


@pytest.fixture
def other_classroom(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Grade 6 Classroom",
        slug="grade-6-classroom", group_type="classroom",
    )


def _make_person(org, first, last, user=None):
    return Person.all_objects.create(organization=org, first_name=first, last_name=last, user=user)


@pytest.fixture
def faculty_author(org, program, classroom):
    user = User.objects.create_user(email="faculty@availability.test", password="pw")
    person = _make_person(org, "Fay", "Faculty", user=user)
    Membership.all_objects.create(program=program, person=person, role="faculty", is_active=True)
    AssignmentGroupMembership.all_objects.create(group=classroom, person=person, role_in_group="author")
    return user, person


@pytest.fixture
def classroom_madrichim(org, program, classroom):
    def _make(first, last, grade_level):
        person = _make_person(org, first, last)
        Membership.all_objects.create(
            program=program, person=person, role="madrich", is_active=True, grade_level=grade_level,
        )
        AssignmentGroupMembership.all_objects.create(group=classroom, person=person, role_in_group="subject")
        return person
    return [_make("Maya", "Alpha", 8), _make("Ben", "Beta", 10)]


@pytest.fixture
def other_classroom_madrich(org, program, other_classroom):
    """Belongs to a different classroom -- must never leak into this classroom's view."""
    person = _make_person(org, "Not", "InThisClassroom")
    Membership.all_objects.create(program=program, person=person, role="madrich", is_active=True)
    AssignmentGroupMembership.all_objects.create(group=other_classroom, person=person, role_in_group="subject")
    return person


class TestFacultyClassroomAvailability:
    def test_faculty_sees_only_classroom_subjects(
        self, api, org, program, classroom, faculty_author, classroom_madrichim,
        other_classroom_madrich, session_dates,
    ):
        user, _ = faculty_author
        api.force_authenticate(user=user)
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=classroom_madrichim[0],
            session_date=session_dates[0], status="available",
        )

        with organization_context(org):
            r = api.get(
                f"/api/v1/faculty/classrooms/{classroom.id}/availability/", **_hdr(org.slug),
            )
        assert r.status_code == 200
        data = r.json()
        names = {row["display_name"] for row in data["rows"]}
        assert names == {"Maya Alpha", "Ben Beta"}
        assert "Not InThisClassroom" not in names

        maya_row = next(row for row in data["rows"] if row["display_name"] == "Maya Alpha")
        first_cell = maya_row["cells"][0]
        assert first_cell["status"] == "available"

    def test_faculty_403_on_admin_matrix(self, api, org, faculty_author):
        user, _ = faculty_author
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/admin/madrich-availability/", **_hdr(org.slug))
        assert r.status_code == 403

    def test_non_author_gets_403(self, api, org, program, classroom):
        user = User.objects.create_user(email="notauthor@availability.test", password="pw")
        person = _make_person(org, "Not", "Author", user=user)
        Membership.all_objects.create(program=program, person=person, role="counselor", is_active=True)
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                f"/api/v1/faculty/classrooms/{classroom.id}/availability/", **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_unauthenticated_gets_401_or_403(self, api, org, classroom):
        with organization_context(org):
            r = api.get(
                f"/api/v1/faculty/classrooms/{classroom.id}/availability/", **_hdr(org.slug),
            )
        assert r.status_code in (401, 403)

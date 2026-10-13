"""School screens follow writer and supervisor seats once group_types is saved.

No saved key: the subject-seat paths stay, and the existing madrich,
faculty, challenge, cohort, and coverage tests cover them. This module
covers the saved class shape.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from bunk_logs.api.admin_flow.director import ungrouped_madrichim
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import ClassroomChallenge
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.reflection_threads import cohort_group_ids
from bunk_logs.core.time_utils import get_today

User = get_user_model()
pytestmark = pytest.mark.django_db

CLASSROOM = {
    "classroom": {
        "enabled": True,
        "members": [
            {"role": "madrich", "placed_as": "author", "supervises_group": False},
            {"role": "student", "placed_as": "subject", "supervises_group": False},
            {"role": "faculty", "placed_as": "author", "supervises_group": True},
        ],
    },
    "cohort": {
        "enabled": True,
        "members": [
            {"role": "madrich", "placed_as": "author", "supervises_group": False},
            {"role": "madrich", "placed_as": "subject", "supervises_group": False},
        ],
    },
}


def session_sunday(org):
    today = get_today(org)
    return today + timedelta(days=(6 - today.weekday()) % 7 or 7)


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    organization = Organization.objects.create(name="Seat School", slug="seat-school")
    organization.settings = {"group_types": CLASSROOM}
    organization.save(update_fields=["settings"])
    return organization


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
        name="Seat School Year",
        slug="seat-school-year",
        program_type="religious_school",
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=200),
        settings={"session_dates": [d.isoformat() for d in session_dates]},
    )


def _person(org, first, last, email):
    user = User.objects.create_user(email=email, password="pw")
    person = Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )
    return user, person


def _member(program, person, role):
    return Membership.all_objects.create(
        program=program, person=person, role=role, is_active=True,
    )


def _group(org, program, name, slug, group_type):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name=name, slug=slug, group_type=group_type,
    )


def _seat(group, person, role_in_group):
    return AssignmentGroupMembership.all_objects.create(
        group=group, person=person, role_in_group=role_in_group, is_active=True,
    )


@pytest.fixture
def grade3(org, program):
    return _group(org, program, "Grade 3", "grade-3", "classroom")


@pytest.fixture
def grade4(org, program):
    return _group(org, program, "Grade 4", "grade-4", "classroom")


@pytest.fixture
def maya(org, program, grade3):
    user, person = _person(org, "Maya", "Alpha", "maya@seat-school.test")
    _member(program, person, "madrich")
    _seat(grade3, person, "author")
    return user, person


@pytest.fixture
def peer(org, program, grade3):
    user, person = _person(org, "Ben", "Beta", "ben@seat-school.test")
    _member(program, person, "madrich")
    _seat(grade3, person, "author")
    return user, person


@pytest.fixture
def ivy(org, program, grade4):
    user, person = _person(org, "Ivy", "Other", "ivy@seat-school.test")
    _member(program, person, "madrich")
    _seat(grade4, person, "author")
    return user, person


@pytest.fixture
def faculty(org, program, grade3):
    user, person = _person(org, "Fay", "Faculty", "fay@seat-school.test")
    _member(program, person, "faculty")
    _seat(grade3, person, "author")
    return user, person


def _file(api, org, user, group, body="The room was too loud."):
    api.force_authenticate(user=user)
    with organization_context(org):
        return api.post(
            "/api/v1/madrich/challenges/",
            {
                "assignment_group_id": group.id,
                "category": ClassroomChallenge.CATEGORY_BEHAVIOR,
                "body": body,
            },
            format="json",
            **_hdr(org.slug),
        )


def test_writer_files_for_their_class_and_not_another(api, org, grade3, grade4, maya, peer):
    created = _file(api, org, maya[0], grade3)
    assert created.status_code == 201
    assert created.json()["author"]["redacted"] is False
    assert created.json()["author"]["display_name"] == "Maya Alpha"

    refused = _file(api, org, maya[0], grade4)
    assert refused.status_code == 403

    api.force_authenticate(user=peer[0])
    with organization_context(org):
        listed = api.get("/api/v1/madrich/challenges/", **_hdr(org.slug))
    assert listed.status_code == 200
    row = listed.json()["results"][0]
    assert row["author"] == {"display": "A Madrich", "redacted": True}
    assert "id" not in row["author"]


def test_subject_seat_cannot_file_and_old_rows_stay_readable(
    api, org, program, grade3, maya,
):
    user, person = _person(org, "Sol", "Subject", "sol@seat-school.test")
    _member(program, person, "madrich")
    _seat(grade3, person, "subject")
    assert _file(api, org, user, grade3).status_code == 403

    candidate = ClassroomChallenge(
        organization=org,
        program=program,
        assignment_group=grade3,
        author=person,
        session_date=session_sunday(org),
        category=ClassroomChallenge.CATEGORY_OTHER,
        body="Filed before the seats moved.",
    )
    with pytest.raises(ValidationError):
        candidate.full_clean()
    stored = ClassroomChallenge.all_objects.create(
        organization=org,
        program=program,
        assignment_group=grade3,
        author=person,
        session_date=session_sunday(org),
        category=ClassroomChallenge.CATEGORY_OTHER,
        body="Filed before the seats moved.",
    )

    api.force_authenticate(user=user)
    with organization_context(org):
        detail = api.get(f"/api/v1/madrich/challenges/{stored.id}/", **_hdr(org.slug))
    assert detail.status_code == 200
    assert detail.json()["body"] == "Filed before the seats moved."


def test_faculty_sees_writers_they_supervise_and_not_another_class(
    api, org, program, grade3, grade4, maya, ivy, faculty, session_dates,
):
    assert _file(api, org, maya[0], grade3).status_code == 201
    ClassroomChallenge.all_objects.create(
        organization=org,
        program=program,
        assignment_group=grade4,
        author=ivy[1],
        session_date=session_dates[0],
        category=ClassroomChallenge.CATEGORY_SCHEDULE,
        body="Grade 4 only.",
    )

    api.force_authenticate(user=faculty[0])
    with organization_context(org):
        challenges = api.get("/api/v1/faculty/challenges/", **_hdr(org.slug))
        roster = api.get("/api/v1/faculty/roster/", **_hdr(org.slug))
        dashboard = api.get("/api/v1/faculty/dashboard/", **_hdr(org.slug))
    assert challenges.status_code == 200
    bodies = [row["body_preview"] for row in challenges.json()["results"]]
    assert any("too loud" in body for body in bodies)
    assert all("Grade 4" not in body for body in bodies)
    assert challenges.json()["results"][0]["author"]["display_name"] == "Maya Alpha"

    names = [row["display_name"] for row in roster.json()["results"]]
    assert names == ["Maya Alpha"]
    assert roster.json()["roster_term"] == "counselor"
    assert dashboard.json()["roster_term"] == "counselor"

    loose_user, loose = _person(org, "Loose", "Rich", "loose@seat-school.test")
    _member(program, loose, "madrich")
    del loose_user
    with organization_context(org):
        missing = ungrouped_madrichim(program)
    ids = {person["person_id"] for person in missing["people"]}
    assert loose.id in ids
    assert maya[1].id not in ids


def test_cohort_seat_is_the_teaching_team_not_a_classroom_author_seat(
    api, org, program, grade3,
):
    user, person = _person(org, "Cora", "Cohort", "cora@seat-school.test")
    _member(program, person, "madrich")
    _seat(grade3, person, "author")
    team = _group(org, program, "Teaching Team", "teaching-team", "cohort")
    _seat(team, person, "subject")

    assert cohort_group_ids(person, program) == [team.id]

    api.force_authenticate(user=user)
    with organization_context(org):
        members = api.get("/api/v1/cohort/members/", **_hdr(org.slug))
    assert members.status_code == 200
    body = members.json()
    assert [cohort["name"] for cohort in body["cohorts"]] == ["Teaching Team"]
    assert body["results"][0]["display_name"] == "Cora Cohort"
    assert body["results"][0]["is_me"] is True

    _user, subject = _person(org, "Sam", "Subject", "sam@seat-school.test")
    _member(program, subject, "madrich")
    _seat(grade3, subject, "subject")
    assert cohort_group_ids(subject, program) == [grade3.id]

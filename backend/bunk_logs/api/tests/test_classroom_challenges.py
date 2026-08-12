"""Tests for the TBE Classroom Challenge Log — Step 4_8, MA7.

Coverage
--------
* Madrich create: subject succeeds, non-member 403, bad category/body 400.
* Peer redaction: a second classroom Madrich sees "A Madrich", not the name.
* Self view: the author always sees their own name.
* Faculty: full author identity; a reply auto-acknowledges an open challenge.
* Faculty PATCH resolved sets ``resolved_at``/``resolved_by``.
* Withdraw: succeeds before any response, 403 after one exists.
* Admin: org-wide list + CSV export include author names.
* Cross-org isolation on every namespace.
* Classroom dashboard payload: faculty sees ``challenges.open_count``;
  a Madrich viewer of the same dashboard gets no ``challenges`` key.
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
from bunk_logs.core.models import ClassroomChallengeResponse
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
    return Organization.objects.create(name="Challenge Log TBE", slug="challenge-log-tbe")


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
        slug="challenge-log-rs",
        program_type="religious_school",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=200),
        settings={"session_dates": [d.isoformat() for d in session_dates]},
    )


@pytest.fixture
def classroom(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Grade 7 Classroom",
        slug="grade-7-classroom", group_type="classroom",
    )


@pytest.fixture
def other_classroom(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Grade 8 Classroom",
        slug="grade-8-classroom", group_type="classroom",
    )


def _make_person(org, first, last, user=None):
    return Person.all_objects.create(organization=org, first_name=first, last_name=last, user=user)


@pytest.fixture
def madrich_a(org, program, classroom):
    user = User.objects.create_user(email="madrich-a@challenge.test", password="pw")
    person = _make_person(org, "Maya", "Alpha", user=user)
    Membership.all_objects.create(program=program, person=person, role="madrich", is_active=True)
    AssignmentGroupMembership.all_objects.create(group=classroom, person=person, role_in_group="subject")
    return user, person


@pytest.fixture
def madrich_b(org, program, classroom):
    """A peer Madrich in the same classroom -- must never see madrich_a's identity."""
    user = User.objects.create_user(email="madrich-b@challenge.test", password="pw")
    person = _make_person(org, "Ben", "Beta", user=user)
    Membership.all_objects.create(program=program, person=person, role="madrich", is_active=True)
    AssignmentGroupMembership.all_objects.create(group=classroom, person=person, role_in_group="subject")
    return user, person


@pytest.fixture
def non_member(org, program):
    user = User.objects.create_user(email="not-in-classroom@challenge.test", password="pw")
    person = _make_person(org, "Not", "InClassroom", user=user)
    Membership.all_objects.create(program=program, person=person, role="madrich", is_active=True)
    return user, person


@pytest.fixture
def faculty(org, program, classroom):
    user = User.objects.create_user(email="faculty@challenge.test", password="pw")
    person = _make_person(org, "Fay", "Faculty", user=user)
    Membership.all_objects.create(program=program, person=person, role="faculty", is_active=True)
    AssignmentGroupMembership.all_objects.create(group=classroom, person=person, role_in_group="author")
    return user, person


@pytest.fixture
def admin_user(org, program):
    user = User.objects.create_user(email="admin@challenge.test", password="pw")
    person = _make_person(org, "Ada", "Admin", user=user)
    Membership.all_objects.create(program=program, person=person, role="admin", is_active=True)
    return user, person


@pytest.fixture
def challenge(org, program, classroom, madrich_a, session_dates):
    _, person = madrich_a
    return ClassroomChallenge.all_objects.create(
        organization=org, program=program, assignment_group=classroom, author=person,
        session_date=session_dates[0], category=ClassroomChallenge.CATEGORY_BEHAVIOR,
        body="Two students were disruptive during Hebrew drill.",
    )


# ---------------------------------------------------------------------------
# Madrich create
# ---------------------------------------------------------------------------


class TestMadrichChallengeCreate:
    def test_subject_creates_challenge(self, api, org, classroom, madrich_a, session_dates):
        user, person = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                "/api/v1/madrich/challenges/",
                {
                    "assignment_group_id": classroom.id,
                    "session_date": session_dates[0].isoformat(),
                    "category": "behavior",
                    "body": "Two students were disruptive.",
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 201, r.json()
        data = r.json()
        assert data["author"]["redacted"] is False
        assert data["author"]["display_name"] == "Maya Alpha"
        assert data["status"] == "open"
        assert ClassroomChallenge.all_objects.filter(author=person, assignment_group=classroom).exists()

    def test_non_member_gets_403(self, api, org, classroom, non_member, session_dates):
        user, _ = non_member
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                "/api/v1/madrich/challenges/",
                {
                    "assignment_group_id": classroom.id,
                    "session_date": session_dates[0].isoformat(),
                    "category": "behavior",
                    "body": "Should not be allowed.",
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_bad_category_400(self, api, org, classroom, madrich_a, session_dates):
        user, _ = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                "/api/v1/madrich/challenges/",
                {
                    "assignment_group_id": classroom.id,
                    "session_date": session_dates[0].isoformat(),
                    "category": "not-a-real-category",
                    "body": "Body text.",
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400

    def test_empty_body_400(self, api, org, classroom, madrich_a, session_dates):
        user, _ = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                "/api/v1/madrich/challenges/",
                {
                    "assignment_group_id": classroom.id,
                    "session_date": session_dates[0].isoformat(),
                    "category": "behavior",
                    "body": "   ",
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400

    def test_default_session_date_when_omitted(self, api, org, classroom, madrich_a, session_dates):
        user, _ = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                "/api/v1/madrich/challenges/",
                {"assignment_group_id": classroom.id, "category": "other", "body": "No date given."},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 201, r.json()
        assert r.json()["session_date"] == session_dates[0].isoformat()


# ---------------------------------------------------------------------------
# Peer redaction + self view
# ---------------------------------------------------------------------------


class TestMadrichChallengeRedaction:
    def test_peer_sees_redacted_author(self, api, org, challenge, madrich_b):
        user, _ = madrich_b
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/madrich/challenges/", **_hdr(org.slug))
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 1
        row = results[0]
        assert row["author"] == {"display": "A Madrich", "redacted": True}
        assert "id" not in row["author"]
        assert row["body_preview"]

    def test_peer_sees_redacted_author_on_detail(self, api, org, challenge, madrich_b):
        user, _ = madrich_b
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(f"/api/v1/madrich/challenges/{challenge.id}/", **_hdr(org.slug))
        assert r.status_code == 200
        assert r.json()["author"]["redacted"] is True

    def test_self_sees_own_name_on_list_and_detail(self, api, org, challenge, madrich_a):
        user, _ = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            list_r = api.get("/api/v1/madrich/challenges/", **_hdr(org.slug))
            detail_r = api.get(f"/api/v1/madrich/challenges/{challenge.id}/", **_hdr(org.slug))
        assert list_r.json()["results"][0]["author"]["redacted"] is False
        assert detail_r.json()["author"]["display_name"] == "Maya Alpha"

    def test_mine_filter_returns_only_own_submissions(self, api, org, challenge, madrich_a, madrich_b, classroom, session_dates):
        _, person_b = madrich_b
        ClassroomChallenge.all_objects.create(
            organization=org, program=challenge.program, assignment_group=classroom, author=person_b,
            session_date=session_dates[1], category=ClassroomChallenge.CATEGORY_OTHER, body="Peer's own report.",
        )
        user, _ = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/madrich/challenges/?mine=1", **_hdr(org.slug))
        results = r.json()["results"]
        assert len(results) == 1
        assert results[0]["id"] == str(challenge.id)

    def test_non_member_gets_403_on_detail(self, api, org, challenge, non_member):
        user, _ = non_member
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(f"/api/v1/madrich/challenges/{challenge.id}/", **_hdr(org.slug))
        assert r.status_code == 403

    def test_classrooms_view_lists_membership(self, api, org, classroom, madrich_a):
        user, _ = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/madrich/challenges/classrooms/", **_hdr(org.slug))
        assert r.status_code == 200
        rows = r.json()["classrooms"]
        assert [row["assignment_group_id"] for row in rows] == [classroom.id]
        assert rows[0]["session_date_default"]


# ---------------------------------------------------------------------------
# Withdraw
# ---------------------------------------------------------------------------


class TestMadrichChallengeWithdraw:
    def test_author_withdraws_before_response(self, api, org, challenge, madrich_a):
        user, _ = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(f"/api/v1/madrich/challenges/{challenge.id}/close/", **_hdr(org.slug))
        assert r.status_code == 204
        assert not ClassroomChallenge.all_objects.filter(id=challenge.id).exists()

    def test_withdraw_fails_after_response(self, api, org, challenge, madrich_a, faculty):
        _, faculty_person = faculty
        ClassroomChallengeResponse.all_objects.create(
            challenge=challenge, author=faculty_person, body="Noted, will follow up.",
        )
        user, _ = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(f"/api/v1/madrich/challenges/{challenge.id}/close/", **_hdr(org.slug))
        assert r.status_code == 403
        assert ClassroomChallenge.all_objects.filter(id=challenge.id).exists()

    def test_non_author_cannot_withdraw(self, api, org, challenge, madrich_b):
        user, _ = madrich_b
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(f"/api/v1/madrich/challenges/{challenge.id}/close/", **_hdr(org.slug))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Faculty
# ---------------------------------------------------------------------------


class TestFacultyChallenge:
    def test_faculty_lists_with_full_author(self, api, org, challenge, faculty):
        user, _ = faculty
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/faculty/challenges/", **_hdr(org.slug))
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 1
        assert results[0]["author"]["display_name"] == "Maya Alpha"
        assert results[0]["assignment_group"]["id"] == challenge.assignment_group_id

    def test_faculty_reply_creates_response_and_acknowledges(self, api, org, challenge, faculty):
        user, _ = faculty
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/faculty/challenges/{challenge.id}/responses/",
                {"body": "Thanks -- I'll address this next week."},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 201, r.json()
        data = r.json()
        assert data["status"] == "acknowledged"
        assert len(data["responses"]) == 1
        assert data["responses"][0]["author"]["display_name"] == "Fay Faculty"
        challenge.refresh_from_db()
        assert challenge.status == ClassroomChallenge.STATUS_ACKNOWLEDGED
        assert ClassroomChallengeResponse.all_objects.filter(challenge=challenge).count() == 1

    def test_faculty_resolve_sets_timestamps(self, api, org, challenge, faculty):
        user, person = faculty
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/faculty/challenges/{challenge.id}/",
                {"status": "resolved"},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200, r.json()
        data = r.json()
        assert data["status"] == "resolved"
        assert data["resolved_at"] is not None
        assert data["resolved_by"]["display_name"] == "Fay Faculty"
        challenge.refresh_from_db()
        assert challenge.resolved_by_id == person.id
        assert challenge.resolved_at is not None

    def test_faculty_403_on_other_classroom_challenge(self, api, org, program, other_classroom, faculty, session_dates):
        outside_madrich = _make_person(org, "Out", "Side")
        Membership.all_objects.create(program=program, person=outside_madrich, role="madrich", is_active=True)
        AssignmentGroupMembership.all_objects.create(
            group=other_classroom, person=outside_madrich, role_in_group="subject",
        )
        other_challenge = ClassroomChallenge.all_objects.create(
            organization=org, program=program, assignment_group=other_classroom, author=outside_madrich,
            session_date=session_dates[0], category=ClassroomChallenge.CATEGORY_OTHER, body="Not this faculty's room.",
        )
        user, _ = faculty
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(f"/api/v1/faculty/challenges/{other_challenge.id}/", **_hdr(org.slug))
        assert r.status_code == 403

    def test_madrich_403_on_faculty_endpoints(self, api, org, challenge, madrich_a):
        user, _ = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/faculty/challenges/", **_hdr(org.slug))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


class TestAdminClassroomChallenges:
    def test_admin_list_includes_author_names(self, api, org, challenge, admin_user):
        user, _ = admin_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/admin/classroom-challenges/", **_hdr(org.slug))
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 1
        assert results[0]["author"]["display_name"] == "Maya Alpha"

    def test_admin_csv_export_includes_author_names(self, api, org, challenge, admin_user):
        user, _ = admin_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/admin/classroom-challenges/export.csv", **_hdr(org.slug))
        assert r.status_code == 200
        content = r.content.decode("utf-8")
        assert "Maya" in content
        assert "Alpha" in content

    def test_non_admin_gets_403(self, api, org, challenge, faculty):
        user, _ = faculty
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/admin/classroom-challenges/", **_hdr(org.slug))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Cross-org isolation
# ---------------------------------------------------------------------------


class TestCrossOrgIsolation:
    def test_other_org_user_gets_403_on_all_namespaces(self, api, challenge):
        other_org = Organization.objects.create(name="Crane Lake", slug="clc-challenge-test")
        other_program = Program.all_objects.create(
            organization=other_org, name="Crane Lake Summer", slug="clc-summer",
            program_type="summer_camp",
            start_date=challenge.session_date - timedelta(days=90),
            end_date=challenge.session_date + timedelta(days=30),
        )
        user = User.objects.create_user(email="clc-counselor@challenge.test", password="pw")
        person = Person.all_objects.create(
            organization=other_org, first_name="CLC", last_name="Person", user=user,
        )
        Membership.all_objects.create(program=other_program, person=person, role="counselor", is_active=True)
        api.force_authenticate(user=user)

        with organization_context(other_org):
            r_madrich = api.get("/api/v1/madrich/challenges/", **_hdr(other_org.slug))
            r_faculty = api.get("/api/v1/faculty/challenges/", **_hdr(other_org.slug))
            r_admin = api.get("/api/v1/admin/classroom-challenges/", **_hdr(other_org.slug))
        assert r_madrich.status_code == 403
        assert r_faculty.status_code == 403
        assert r_admin.status_code == 403


# ---------------------------------------------------------------------------
# Classroom dashboard payload integration
# ---------------------------------------------------------------------------


class TestClassroomDashboardChallengesBlock:
    def test_faculty_sees_open_count(self, api, org, classroom, challenge, faculty):
        user, _ = faculty
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(f"/api/v1/dashboards/group/{classroom.id}/", **_hdr(org.slug))
        assert r.status_code == 200
        data = r.json()
        assert data["challenges"]["open_count"] == 1
        assert data["challenges"]["list_url"] == f"/faculty/challenges?classroom={classroom.id}"
        assert len(data["challenges"]["recent"]) == 1

    def test_madrich_subject_gets_403(self, api, org, classroom, challenge, madrich_a):
        """A pure classroom "subject" Madrich has no author AGM row -- denied outright."""
        user, _ = madrich_a
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(f"/api/v1/dashboards/group/{classroom.id}/", **_hdr(org.slug))
        assert r.status_code == 403

    def test_madrich_author_gets_no_challenges_key(self, api, org, program, classroom, challenge):
        """A Madrich who is (unusually) an AGM author still isn't Faculty -- no challenges block."""
        user = User.objects.create_user(email="madrich-author@challenge.test", password="pw")
        person = _make_person(org, "Mad", "Rich", user=user)
        Membership.all_objects.create(program=program, person=person, role="madrich", is_active=True)
        AssignmentGroupMembership.all_objects.create(group=classroom, person=person, role_in_group="author")
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(f"/api/v1/dashboards/group/{classroom.id}/", **_hdr(org.slug))
        assert r.status_code == 200
        assert "challenges" not in r.json()

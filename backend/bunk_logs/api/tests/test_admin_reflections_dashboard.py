"""Tests for the TBE admin reflections completion dashboard (Step 4_4).

Covers:

* ``GET /api/v1/admin/reflections/teams/<role>/`` -- weekly completion
  roster, grade-level filtering, permission gate.
* ``GET /api/v1/admin/reflections/teams/<role>/export/`` -- board-report
  CSV (no free-text answer content).
* ``GET /api/v1/admin/reflections/teams/<role>/members/<id>/`` -- one
  member's reflection history.
* Cross-org isolation across all three endpoints.

Relies on the ``_autobind_role_assignments_to_new_programs`` autouse
fixture in ``api/tests/conftest.py``, which auto-creates the
``TemplateAssignment`` binding the globally-seeded
``tbe-madrich-3-2-1-weekly`` template (migration 0037) to any
``Program`` created in a test -- mirroring how the madrich flow tests
already rely on it.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.api.leadership_team.common import resolve_period
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.time_utils import get_today

User = get_user_model()
pytestmark = pytest.mark.django_db

MADRICH_TEMPLATE_SLUG = "tbe-madrich-3-2-1-weekly"


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


def _madrich_template() -> ReflectionTemplate:
    return ReflectionTemplate.all_objects.get(
        slug=MADRICH_TEMPLATE_SLUG, organization__isnull=True,
    )


def _valid_answers() -> dict:
    return {
        "wins": ["a", "b", "c"],
        "improvements": ["x", "y"],
        "question_or_concern": "none",
        "ratings": {
            "reliability_punctuality": 4,
            "initiative": 3,
            "communication": 3,
            "problem_solving": 3,
            "interpersonal": 4,
        },
    }


def _submit_reflection(person, program, org, *, period_start, period_end):
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        subject=person,
        author=person,
        template=_madrich_template(),
        period_start=period_start,
        period_end=period_end,
        answers=_valid_answers(),
        is_complete=True,
    )


def _make_admin(org, program, email) -> User:
    user = User.objects.create_user(email=email, password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ada", last_name="Admin", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )
    return user


def _make_madrich(org, program, *, first, last, grade_level):
    person = Person.all_objects.create(organization=org, first_name=first, last_name=last)
    membership = Membership.all_objects.create(
        program=program, person=person, role="madrich", is_active=True, grade_level=grade_level,
    )
    return person, membership


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Admin Reflections TBE", slug="admin-reflections-tbe")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="Admin Reflections Other", slug="admin-reflections-other")


@pytest.fixture
def program(org):
    today = get_today(org)
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Religious School",
        slug="admin-reflections-rs",
        program_type="religious_school",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=200),
    )


@pytest.fixture
def other_program(other_org):
    today = get_today(other_org)
    return Program.all_objects.create(
        organization=other_org,
        name=f"{other_org.name} Religious School",
        slug="admin-reflections-other-rs",
        program_type="religious_school",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=200),
    )


@pytest.fixture
def admin_user(org, program):
    return _make_admin(org, program, "admin@tbe-reflections.test")


@pytest.fixture
def other_admin_user(other_org, other_program):
    return _make_admin(other_org, other_program, "admin@other-reflections.test")


# ---------------------------------------------------------------------------
# Team completion roster
# ---------------------------------------------------------------------------


class TestAdminReflectionsTeamDashboard:
    def test_renders_weekly_completion_for_tbe_admin(self, api, org, program, admin_user):
        person_a, _ = _make_madrich(org, program, first="Maya", last="Alpha", grade_level=8)
        _make_madrich(org, program, first="Ben", last="Beta", grade_level=10)

        today = get_today(org)
        period_start, period_end = resolve_period(
            _madrich_template(), anchor=today, program=program,
        )
        _submit_reflection(person_a, program, org, period_start=period_start, period_end=period_end)

        api.force_authenticate(user=admin_user)
        resp = api.get("/api/v1/admin/reflections/teams/madrich/", **_hdr(org.slug))

        assert resp.status_code == 200
        data = resp.json()
        assert data["header"]["role"] == "madrich"
        assert data["header"]["role_label"] == "Madrich"
        assert data["header"]["member_count"] == 2
        assert data["header"]["period"]["cadence"] == "weekly"
        assert data["submission_status"] == {
            "submitted": 1, "day_off": 0, "not_submitted": 1, "total": 2,
        }
        status_by_name = {m["person_name"]: m["status"] for m in data["members"]}
        grade_by_name = {m["person_name"]: m["grade_level"] for m in data["members"]}
        assert status_by_name["Maya A."] == "submitted"
        assert status_by_name["Ben B."] == "not_submitted"
        assert grade_by_name["Maya A."] == 8
        assert grade_by_name["Ben B."] == 10

    def test_grade_level_filter_narrows_members(self, api, org, program, admin_user):
        _make_madrich(org, program, first="Eight", last="Grader", grade_level=8)
        _make_madrich(org, program, first="Ten", last="Grader", grade_level=10)
        _make_madrich(org, program, first="Twelve", last="Grader", grade_level=12)

        api.force_authenticate(user=admin_user)
        resp = api.get(
            "/api/v1/admin/reflections/teams/madrich/",
            {"grade_level": "8,10"},
            **_hdr(org.slug),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["header"]["member_count"] == 2
        assert sorted(m["grade_level"] for m in data["members"]) == [8, 10]

    def test_non_admin_gets_403(self, api, org, program):
        user = User.objects.create_user(email="madrich-self@tbe-reflections.test", password="pw")
        person = Person.all_objects.create(organization=org, first_name="Self", last_name="Madrich", user=user)
        Membership.all_objects.create(
            program=program, person=person, role="madrich", is_active=True, grade_level=9,
        )

        api.force_authenticate(user=user)
        resp = api.get("/api/v1/admin/reflections/teams/madrich/", **_hdr(org.slug))
        assert resp.status_code == 403

    def test_cross_org_isolation(
        self, api, org, program, admin_user, other_org, other_program, other_admin_user,
    ):
        _make_madrich(org, program, first="Home", last="Madrich", grade_level=9)
        _make_madrich(other_org, other_program, first="Away", last="Madrich", grade_level=9)

        api.force_authenticate(user=admin_user)
        resp = api.get("/api/v1/admin/reflections/teams/madrich/", **_hdr(org.slug))
        assert resp.status_code == 200
        assert {m["person_name"] for m in resp.json()["members"]} == {"Home M."}

        # Same admin cannot borrow the other org's data by switching the header --
        # they have no admin Membership there.
        resp_wrong_org = api.get("/api/v1/admin/reflections/teams/madrich/", **_hdr(other_org.slug))
        assert resp_wrong_org.status_code == 403

        api.force_authenticate(user=other_admin_user)
        resp2 = api.get("/api/v1/admin/reflections/teams/madrich/", **_hdr(other_org.slug))
        assert resp2.status_code == 200
        assert {m["person_name"] for m in resp2.json()["members"]} == {"Away M."}


# ---------------------------------------------------------------------------
# Member detail / history
# ---------------------------------------------------------------------------


class TestAdminReflectionsMemberDetail:
    def test_member_history_and_cross_org_404(
        self, api, org, program, admin_user, other_org, other_program, other_admin_user,
    ):
        person, membership = _make_madrich(org, program, first="Maya", last="History", grade_level=9)
        today = get_today(org)
        period_start, period_end = resolve_period(
            _madrich_template(), anchor=today, program=program,
        )
        _submit_reflection(person, program, org, period_start=period_start, period_end=period_end)

        api.force_authenticate(user=admin_user)
        resp = api.get(
            f"/api/v1/admin/reflections/teams/madrich/members/{membership.id}/", **_hdr(org.slug),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["person_name"] == "Maya H."
        assert data["grade_level"] == 9
        assert len(data["history"]) == 1
        assert data["history"][0]["status"] == "submitted"

        _make_madrich(other_org, other_program, first="Away", last="Madrich", grade_level=9)
        api.force_authenticate(user=other_admin_user)
        resp2 = api.get(
            f"/api/v1/admin/reflections/teams/madrich/members/{membership.id}/",
            **_hdr(other_org.slug),
        )
        assert resp2.status_code == 404


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


class TestAdminReflectionsExport:
    def test_export_returns_board_safe_csv(self, api, org, program, admin_user):
        person, _ = _make_madrich(org, program, first="Csv", last="Export", grade_level=11)
        today = get_today(org)
        period_start, period_end = resolve_period(
            _madrich_template(), anchor=today, program=program,
        )
        _submit_reflection(person, program, org, period_start=period_start, period_end=period_end)

        api.force_authenticate(user=admin_user)
        resp = api.get("/api/v1/admin/reflections/teams/madrich/export/", **_hdr(org.slug))

        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/csv")
        content = resp.content.decode()
        assert "person_name,grade_level,status,submitted_at,period_start,period_end" in content
        assert "Csv E.,11,submitted" in content
        # Board export must not leak free-text reflection content.
        assert "question_or_concern" not in content
        assert "none" not in content

"""Tests for the admin growth-by-grade dashboard.

Covers:

* ``GET /api/v1/admin/reflections/growth/`` -- per-grade theme mix, rating
  means, coverage reporting, derived milestone slopes, grade filtering.
* ``GET /api/v1/admin/reflections/growth/export/`` -- long-format CSV with no
  free-text leakage.
* ``GET /api/v1/admin/reflections/growth/examples/`` -- the drill-down that is
  allowed to return excerpts.
* Permission gate and cross-org isolation.

Relies on the ``_autobind_role_assignments_to_new_programs`` autouse fixture
in ``api/tests/conftest.py``, which binds the globally-seeded
``tbe-madrich-3-2-1-weekly`` template (migration 0037) to any Program created
in a test.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import ReflectionThemeTag
from bunk_logs.core.models import ReflectionThemeTagging
from bunk_logs.core.theme_tagging.taxonomy import TAXONOMY_VERSION
from bunk_logs.core.time_utils import get_today

User = get_user_model()
pytestmark = pytest.mark.django_db

MADRICH_TEMPLATE_SLUG = "tbe-madrich-3-2-1-weekly"
GROWTH_URL = "/api/v1/admin/reflections/growth/"
EXPORT_URL = "/api/v1/admin/reflections/growth/export/"
EXAMPLES_URL = "/api/v1/admin/reflections/growth/examples/"

SECRET_TEXT = "Two students keep fighting and I do not know what to do"


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


def _madrich_template() -> ReflectionTemplate:
    return ReflectionTemplate.all_objects.get(
        slug=MADRICH_TEMPLATE_SLUG, organization__isnull=True,
    )


def _answers(*, initiative=3, concern=SECRET_TEXT) -> dict:
    return {
        "wins": ["a", "b", "c"],
        "improvements": ["x", "y"],
        "question_or_concern": concern,
        "ratings": {
            "reliability_punctuality": 4,
            "initiative": initiative,
            "communication": 3,
            "problem_solving": 3,
            "interpersonal": 4,
        },
    }


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
    person = Person.all_objects.create(
        organization=org, first_name=first, last_name=last,
    )
    Membership.all_objects.create(
        program=program, person=person, role="madrich",
        is_active=True, grade_level=grade_level,
    )
    return person


def _submit(person, program, org, *, period_start, answers=None):
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        subject=person,
        author=person,
        template=_madrich_template(),
        period_start=period_start,
        period_end=period_start + timedelta(days=6),
        answers=answers if answers is not None else _answers(),
        is_complete=True,
    )


def _tag(reflection, *, grade_level, themes, status=None):
    """Attach theme tags to ``reflection`` the way the Celery task would.

    ``themes`` is a list of ``(field_key, dashboard_role, theme_key)``.
    """
    record = ReflectionThemeTagging.all_objects.create(
        organization=reflection.organization,
        reflection=reflection,
        taxonomy_version=TAXONOMY_VERSION,
        status=status or ReflectionThemeTagging.Status.COMPLETED,
    )
    for field_key, dashboard_role, theme_key in themes:
        ReflectionThemeTag.all_objects.create(
            tagging=record,
            organization=reflection.organization,
            reflection=reflection,
            program=reflection.program,
            field_key=field_key,
            dashboard_role=dashboard_role,
            theme_key=theme_key,
            grade_level=grade_level,
            period_start=reflection.period_start,
        )
    return record


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Growth TBE", slug="growth-tbe")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="Growth Other", slug="growth-other")


@pytest.fixture
def program(org):
    today = get_today(org)
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Religious School",
        slug="growth-rs",
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
        slug="growth-other-rs",
        program_type="religious_school",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=200),
    )


@pytest.fixture
def admin_user(org, program):
    return _make_admin(org, program, "admin@growth-tbe.test")


@pytest.fixture
def other_admin_user(other_org, other_program):
    return _make_admin(other_org, other_program, "admin@growth-other.test")


@pytest.fixture
def seeded(org, program):
    """Two grades with deliberately different theme mixes and rating levels.

    Grade 8 raises a tier-1 fundamentals concern; grade 11 raises a tier-3
    concern and rates itself higher. That is the shape the dashboard exists
    to surface, so the assertions can check real contrast rather than
    incidental numbers.
    """
    today = get_today(org)
    last_week = today - timedelta(days=today.weekday() + 7)

    eighth = _make_madrich(org, program, first="Ellie", last="Eight", grade_level=8)
    eleventh = _make_madrich(org, program, first="Eli", last="Eleven", grade_level=11)

    r8 = _submit(eighth, program, org, period_start=last_week, answers=_answers(initiative=2))
    r11 = _submit(eleventh, program, org, period_start=last_week, answers=_answers(initiative=4))

    _tag(r8, grade_level=8, themes=[
        ("question_or_concern", "open_concern", "classroom_management"),
        ("wins", "wins", "own_confidence"),
    ])
    _tag(r11, grade_level=11, themes=[
        ("question_or_concern", "open_concern", "conflict_resolution"),
        ("improvements", "improvements", "family_communication"),
    ])
    return {"r8": r8, "r11": r11}


# ---------------------------------------------------------------------------
# Growth dashboard
# ---------------------------------------------------------------------------


class TestAdminGrowthDashboard:
    def test_groups_themes_ratings_and_milestones_by_grade(
        self, api, org, program, admin_user, seeded,
    ):
        api.force_authenticate(user=admin_user)
        resp = api.get(GROWTH_URL, **_hdr(org.slug))

        assert resp.status_code == 200
        data = resp.json()

        assert data["header"]["role"] == "madrich"
        assert data["header"]["taxonomy_version"] == TAXONOMY_VERSION
        assert data["header"]["program"]["id"] == program.id
        assert data["header"]["coverage"] == {
            "reflections": 2, "tagged": 2, "pending": 0, "failed": 0, "untagged": 0,
        }

        by_grade = {g["grade_level"]: g for g in data["grades"]}
        assert set(by_grade) == {8, 11}
        assert by_grade[8]["member_count"] == 1
        assert by_grade[8]["reflection_count"] == 1

        # 8th grade raised a fundamentals concern, 11th a sophisticated one.
        concerns_8 = {
            t["theme_key"]: t["open_concern_count"]
            for t in by_grade[8]["themes"] if t["open_concern_count"]
        }
        concerns_11 = {
            t["theme_key"]: t["open_concern_count"]
            for t in by_grade[11]["themes"] if t["open_concern_count"]
        }
        assert concerns_8 == {"classroom_management": 1}
        assert concerns_11 == {"conflict_resolution": 1}

        # The complexity index is the derived developmental signal.
        assert by_grade[8]["concern_complexity_index"] == 1.0
        assert by_grade[11]["concern_complexity_index"] == 3.0

        # Non-concern roles are counted separately, not folded into concerns.
        wins_8 = {t["theme_key"]: t["wins_count"] for t in by_grade[8]["themes"]}
        assert wins_8["own_confidence"] == 1

        ratings_8 = {r["category_key"]: r["mean"] for r in by_grade[8]["ratings"]}
        ratings_11 = {r["category_key"]: r["mean"] for r in by_grade[11]["ratings"]}
        assert ratings_8["initiative"] == 2.0
        assert ratings_11["initiative"] == 4.0

        milestones = {m["metric_key"]: m for m in data["milestones"]}
        initiative = milestones["initiative"]
        # (8, 2.0) -> (11, 4.0) is a slope of 2/3 per grade.
        assert initiative["slope"] == pytest.approx(0.6667, abs=1e-3)
        assert initiative["direction"] == "improving"
        assert milestones["__concern_complexity"]["direction"] == "improving"

    def test_grade_level_filter_narrows_payload(
        self, api, org, program, admin_user, seeded,
    ):
        api.force_authenticate(user=admin_user)
        resp = api.get(GROWTH_URL, {"grade_level": "11"}, **_hdr(org.slug))

        assert resp.status_code == 200
        grades = resp.json()["grades"]
        assert [g["grade_level"] for g in grades] == [11]

    def test_no_free_text_in_payload(self, api, org, program, admin_user, seeded):
        api.force_authenticate(user=admin_user)
        resp = api.get(GROWTH_URL, **_hdr(org.slug))
        assert SECRET_TEXT not in resp.content.decode()

    def test_untagged_reflections_show_in_coverage(
        self, api, org, program, admin_user,
    ):
        """A grade with no themes must be explainable as a tagging backlog."""
        today = get_today(org)
        last_week = today - timedelta(days=today.weekday() + 7)
        person = _make_madrich(org, program, first="Una", last="Tagged", grade_level=9)
        _submit(person, program, org, period_start=last_week)

        api.force_authenticate(user=admin_user)
        resp = api.get(GROWTH_URL, **_hdr(org.slug))

        assert resp.status_code == 200
        data = resp.json()
        assert data["header"]["coverage"] == {
            "reflections": 1, "tagged": 0, "pending": 0, "failed": 0, "untagged": 1,
        }
        by_grade = {g["grade_level"]: g for g in data["grades"]}
        assert by_grade[9]["themes"] == []
        assert by_grade[9]["concern_complexity_index"] is None

    def test_empty_org_returns_no_grades(self, api, org, program, admin_user):
        api.force_authenticate(user=admin_user)
        resp = api.get(GROWTH_URL, **_hdr(org.slug))
        assert resp.status_code == 200
        data = resp.json()
        assert data["grades"] == []
        assert data["milestones"] == []
        assert data["header"]["coverage"]["reflections"] == 0
        # The taxonomy still ships so the UI can render labels and ordering.
        assert len(data["taxonomy"]) > 0

    def test_single_grade_slope_is_insufficient_data(
        self, api, org, program, admin_user,
    ):
        today = get_today(org)
        last_week = today - timedelta(days=today.weekday() + 7)
        person = _make_madrich(org, program, first="Solo", last="Grade", grade_level=8)
        reflection = _submit(person, program, org, period_start=last_week)
        _tag(reflection, grade_level=8, themes=[
            ("question_or_concern", "open_concern", "own_confidence"),
        ])

        api.force_authenticate(user=admin_user)
        resp = api.get(GROWTH_URL, **_hdr(org.slug))

        milestones = {m["metric_key"]: m for m in resp.json()["milestones"]}
        assert milestones["initiative"]["slope"] is None
        assert milestones["initiative"]["direction"] == "insufficient_data"

    def test_invalid_window_is_rejected(self, api, org, program, admin_user):
        api.force_authenticate(user=admin_user)
        resp = api.get(
            GROWTH_URL, {"start": "2026-10-01", "end": "2026-09-01"}, **_hdr(org.slug),
        )
        assert resp.status_code == 400

    def test_non_admin_gets_403(self, api, org, program):
        user = User.objects.create_user(email="madrich@growth-tbe.test", password="pw")
        person = Person.all_objects.create(
            organization=org, first_name="Self", last_name="Madrich", user=user,
        )
        Membership.all_objects.create(
            program=program, person=person, role="madrich",
            is_active=True, grade_level=9,
        )

        api.force_authenticate(user=user)
        assert api.get(GROWTH_URL, **_hdr(org.slug)).status_code == 403

    def test_cross_org_isolation(
        self, api, org, program, admin_user, seeded,
        other_org, other_program, other_admin_user,
    ):
        today = get_today(other_org)
        last_week = today - timedelta(days=today.weekday() + 7)
        away = _make_madrich(
            other_org, other_program, first="Away", last="Madrich", grade_level=8,
        )
        away_reflection = _submit(away, other_program, other_org, period_start=last_week)
        _tag(away_reflection, grade_level=8, themes=[
            ("question_or_concern", "open_concern", "logistics_scheduling"),
        ])

        # The home admin sees only their own themes for grade 8.
        api.force_authenticate(user=admin_user)
        resp = api.get(GROWTH_URL, **_hdr(org.slug))
        home_8 = next(g for g in resp.json()["grades"] if g["grade_level"] == 8)
        assert {t["theme_key"] for t in home_8["themes"]} == {
            "classroom_management", "own_confidence",
        }

        # Switching the header does not borrow the other tenant's data.
        assert api.get(GROWTH_URL, **_hdr(other_org.slug)).status_code == 403

        api.force_authenticate(user=other_admin_user)
        resp2 = api.get(GROWTH_URL, **_hdr(other_org.slug))
        away_8 = next(g for g in resp2.json()["grades"] if g["grade_level"] == 8)
        assert {t["theme_key"] for t in away_8["themes"]} == {"logistics_scheduling"}


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


class TestAdminGrowthExport:
    def test_csv_is_long_format_and_omits_free_text(
        self, api, org, program, admin_user, seeded,
    ):
        api.force_authenticate(user=admin_user)
        resp = api.get(EXPORT_URL, **_hdr(org.slug))

        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv"
        body = resp.content.decode()
        lines = body.strip().splitlines()
        assert lines[0] == (
            "grade_level,member_count,reflection_count,"
            "metric_type,metric_key,metric_label,value"
        )
        assert "theme_open_concern" in body
        assert "rating_mean" in body
        assert "__concern_complexity" in body
        # A board export must never carry reflection contents.
        assert SECRET_TEXT not in body

    def test_non_admin_gets_403(self, api, org, program):
        user = User.objects.create_user(email="nobody@growth-tbe.test", password="pw")
        api.force_authenticate(user=user)
        assert api.get(EXPORT_URL, **_hdr(org.slug)).status_code == 403


# ---------------------------------------------------------------------------
# Examples drill-down
# ---------------------------------------------------------------------------


class TestAdminGrowthExamples:
    def test_returns_excerpts_for_a_grade_and_theme(
        self, api, org, program, admin_user, seeded,
    ):
        api.force_authenticate(user=admin_user)
        resp = api.get(
            EXAMPLES_URL,
            {"theme": "conflict_resolution", "grade_level": "11"},
            **_hdr(org.slug),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"]["key"] == "conflict_resolution"
        assert data["theme"]["complexity_tier"] == 3
        assert data["count"] == 1
        item = data["items"][0]
        assert item["grade_level"] == 11
        assert item["field_key"] == "question_or_concern"
        # This endpoint is the one place excerpts are allowed.
        assert item["excerpt"] == SECRET_TEXT

    def test_grade_filter_excludes_other_cohorts(
        self, api, org, program, admin_user, seeded,
    ):
        api.force_authenticate(user=admin_user)
        resp = api.get(
            EXAMPLES_URL,
            {"theme": "conflict_resolution", "grade_level": "8"},
            **_hdr(org.slug),
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_missing_theme_is_400(self, api, org, program, admin_user):
        api.force_authenticate(user=admin_user)
        assert api.get(EXAMPLES_URL, **_hdr(org.slug)).status_code == 400

    def test_unknown_theme_is_400(self, api, org, program, admin_user):
        api.force_authenticate(user=admin_user)
        resp = api.get(EXAMPLES_URL, {"theme": "made_up"}, **_hdr(org.slug))
        assert resp.status_code == 400

    def test_non_admin_gets_403(self, api, org, program):
        user = User.objects.create_user(email="peeker@growth-tbe.test", password="pw")
        api.force_authenticate(user=user)
        resp = api.get(
            EXAMPLES_URL, {"theme": "conflict_resolution"}, **_hdr(org.slug),
        )
        assert resp.status_code == 403

"""Tests for GET /api/v1/reflections/my-summary/"""
from __future__ import annotations

from datetime import date
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

User = get_user_model()

ORG_HDR = {"HTTP_X_ORGANIZATION_SLUG": "ms-org"}


@pytest.fixture
def org(db):
    return Organization.objects.create(name="MS Org", slug="ms-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="MS Org - Summer 2026",
        slug="ms-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def daily_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Daily Tpl",
        slug="daily-ms",
        cadence="daily",
        role="counselor",
        schema={"fields": [{"key": "note", "type": "text", "prompts": {"en": "Note"}}]},
    )


@pytest.fixture
def weekly_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Weekly Tpl",
        slug="weekly-ms",
        cadence="weekly",
        role="unit_head",
        schema={"fields": [{"key": "note", "type": "text", "prompts": {"en": "Note"}}]},
    )


@pytest.fixture
def counselor_user(org, program, daily_template):
    u = User.objects.create_user(email="counselor-ms@example.test", password="pw")
    p = Person.all_objects.create(organization=org, first_name="C", last_name="MS", user=u)
    Membership.all_objects.create(program=program, person=p, role="counselor", is_active=True)
    from bunk_logs.api.tests.conftest import make_active_assignment

    make_active_assignment(template=daily_template, program=program, target_role="counselor")
    return u, p


@pytest.fixture
def unit_head_user(org, program, weekly_template):
    u = User.objects.create_user(email="uh-ms@example.test", password="pw")
    p = Person.all_objects.create(organization=org, first_name="UH", last_name="MS", user=u)
    Membership.all_objects.create(program=program, person=p, role="unit_head", is_active=True)
    from bunk_logs.api.tests.conftest import make_active_assignment

    make_active_assignment(template=weekly_template, program=program, target_role="unit_head")
    return u, p


@pytest.fixture
def api():
    return APIClient()


def _make_reflection(org, program, person, template, period_end, is_complete=True):
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        subject=person,
        author=person,
        template=template,
        period_start=period_end,
        period_end=period_end,
        answers={"note": "ok"},
        language="en",
        is_complete=is_complete,
    )


# ---------------------------------------------------------------------------
# Auth / access control
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_requires_auth(api, org):
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    assert r.status_code == 401


@pytest.mark.django_db
def test_requires_org_header(api, counselor_user):
    user, _ = counselor_user
    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/")
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_no_membership_returns_404(api, org):
    u = User.objects.create_user(email="nomem-ms@example.test", password="pw")
    Person.all_objects.create(organization=org, first_name="NM", last_name="MS", user=u)
    api.force_authenticate(user=u)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Empty state (no reflections yet)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_reflections_returns_zero_streak(api, org, counselor_user, daily_template):
    user, _ = counselor_user
    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    assert r.status_code == 200
    body = r.json()
    assert body["streak"] == 0
    assert body["total_completed"] == 0
    assert body["current_period"]["submitted"] is False
    assert len(body["history"]) == 14  # 14 daily periods


# ---------------------------------------------------------------------------
# Streak calculation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_streak_counts_consecutive_days(api, org, program, counselor_user, daily_template):
    user, person = counselor_user
    today = date.today()
    for i in range(3):
        _make_reflection(org, program, person, daily_template, today - timedelta(days=i))
    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    assert r.status_code == 200
    body = r.json()
    assert body["streak"] == 3
    assert body["current_period"]["submitted"] is True
    assert body["total_completed"] == 3


@pytest.mark.django_db
def test_streak_breaks_on_gap(api, org, program, counselor_user, daily_template):
    user, person = counselor_user
    today = date.today()
    # Submit today and 2 days ago but NOT yesterday
    _make_reflection(org, program, person, daily_template, today)
    _make_reflection(org, program, person, daily_template, today - timedelta(days=2))
    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    body = r.json()
    # Streak from today = 1 (yesterday missing breaks it)
    assert body["streak"] == 1


@pytest.mark.django_db
def test_streak_no_submission_today(api, org, program, counselor_user, daily_template):
    user, person = counselor_user
    today = date.today()
    # Submitted the last 3 days but not today
    for i in range(1, 4):
        _make_reflection(org, program, person, daily_template, today - timedelta(days=i))
    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    body = r.json()
    # Current period not submitted → streak = 0
    assert body["streak"] == 0
    assert body["current_period"]["submitted"] is False


# ---------------------------------------------------------------------------
# Weekly cadence
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_weekly_history_has_4_periods(api, org, program, unit_head_user, weekly_template):
    user, _ = unit_head_user
    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    assert r.status_code == 200
    body = r.json()
    assert len(body["history"]) == 4


@pytest.mark.django_db
def test_weekly_streak(api, org, program, unit_head_user, weekly_template):
    user, person = unit_head_user
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    # Submit in this week and the previous 2 weeks
    for i in range(3):
        day = monday - timedelta(weeks=i)
        _make_reflection(org, program, person, weekly_template, day)
    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    body = r.json()
    assert body["streak"] == 3


# ---------------------------------------------------------------------------
# Total completed counts all-time, not just the window
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_total_completed_counts_beyond_window(api, org, program, counselor_user, daily_template):
    user, person = counselor_user
    today = date.today()
    # 20 reflections — more than the 14-day window
    for i in range(20):
        _make_reflection(org, program, person, daily_template, today - timedelta(days=i))
    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    body = r.json()
    assert body["total_completed"] == 20
    assert len(body["history"]) == 14  # window still 14


# ---------------------------------------------------------------------------
# Incomplete reflections don't count
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_incomplete_reflection_not_counted(api, org, program, counselor_user, daily_template):
    user, person = counselor_user
    today = date.today()
    _make_reflection(org, program, person, daily_template, today, is_complete=False)
    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    body = r.json()
    assert body["streak"] == 0
    assert body["total_completed"] == 0
    assert body["current_period"]["submitted"] is False


# ---------------------------------------------------------------------------
# program filter
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_program_filter_respected(api, org, program, counselor_user, daily_template):
    user, person = counselor_user
    today = date.today()
    _make_reflection(org, program, person, daily_template, today)
    api.force_authenticate(user=user)
    # Correct program returns the reflection
    r = api.get("/api/v1/reflections/my-summary/", {"program": program.slug}, **ORG_HDR)
    assert r.status_code == 200
    body = r.json()
    assert body["current_period"]["submitted"] is True
    # Non-existent program slug returns 404
    r2 = api.get("/api/v1/reflections/my-summary/", {"program": "no-such"}, **ORG_HDR)
    assert r2.status_code == 404


# ---------------------------------------------------------------------------
# Assignment-aware template resolution (Step 7_21)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_my_summary_uses_assigned_self_template_not_role_fallback(
    api, org, program, counselor_user, daily_template,
):
    """When multiple counselor templates exist, my-summary follows TemplateAssignment."""
    from bunk_logs.api.tests.conftest import make_active_assignment
    from bunk_logs.core.models import TemplateAssignment

    user, person = counselor_user
    # Legacy role lookup would pick this decoy (higher version, same role).
    ReflectionTemplate.all_objects.create(
        organization=org,
        name="Decoy bunk log",
        slug="decoy-bunk-log-ms",
        cadence="daily",
        role="counselor",
        version=99,
        subject_mode="single_subject",
        schema={"fields": [{"key": "note", "type": "text", "prompts": {"en": "Note"}}]},
        is_active=True,
    )
    assigned_tpl = ReflectionTemplate.all_objects.create(
        organization=org,
        name="Staff self log",
        slug="staff-self-log-ms",
        cadence="daily",
        role="counselor",
        subject_mode="self",
        schema={"fields": [{"key": "note", "type": "text", "prompts": {"en": "Note"}}]},
        is_active=True,
    )
    TemplateAssignment.all_objects.filter(program=program, template=daily_template).delete()
    TemplateAssignment.all_objects.filter(
        program=program,
        template__slug="counselor-self-reflection",
        template__organization__isnull=True,
    ).delete()
    make_active_assignment(template=assigned_tpl, program=program, target_role="counselor")
    today = date.today()
    _make_reflection(org, program, person, assigned_tpl, today)

    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    assert r.status_code == 200
    body = r.json()
    assert body["template"]["slug"] == "staff-self-log-ms"
    assert body["current_period"]["submitted"] is True
    assert body["total_completed"] == 1


@pytest.mark.django_db
def test_my_summary_prefers_latest_self_reflection_program(
    api, org, program, counselor_user, daily_template,
):
    """When memberships span programs, scope follows the latest self-reflection."""
    from bunk_logs.api.tests.conftest import make_active_assignment
    from bunk_logs.core.models import TemplateAssignment

    user, person = counselor_user
    pre_camp = Program.all_objects.create(
        organization=org,
        name="MS Org Pre Camp",
        slug="pre-camp-ms",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 20),
    )
    # Newer membership on a program without assignments — would win naive -created_at sort.
    Membership.all_objects.create(
        program=pre_camp, person=person, role="counselor", is_active=True,
    )
    assigned_tpl = ReflectionTemplate.all_objects.create(
        organization=org,
        name="Assigned self",
        slug="assigned-self-ms",
        cadence="daily",
        role="counselor",
        subject_mode="self",
        schema={"fields": [{"key": "note", "type": "text", "prompts": {"en": "Note"}}]},
        is_active=True,
    )
    TemplateAssignment.all_objects.filter(program=program, template=daily_template).delete()
    make_active_assignment(template=assigned_tpl, program=program, target_role="counselor")
    today = date.today()
    _make_reflection(org, program, person, assigned_tpl, today)

    api.force_authenticate(user=user)
    r = api.get("/api/v1/reflections/my-summary/", **ORG_HDR)
    assert r.status_code == 200
    body = r.json()
    assert body["program"] == program.slug
    assert body["template"]["slug"] == "assigned-self-ms"
    assert body["current_period"]["submitted"] is True

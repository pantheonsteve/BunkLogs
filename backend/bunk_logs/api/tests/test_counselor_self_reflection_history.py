"""Tests for ``GET /api/v1/counselor/self-reflection/history/`` (Story 6)."""
from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.time_utils import get_today

User = get_user_model()

SELF_SCHEMA = {
    "fields": [
        {"key": "day_off", "type": "yes_no", "prompts": {"en": "Day off?"}},
        {"key": "elaboration", "type": "textarea", "required": True, "prompts": {"en": "How was today?"}},
    ],
}


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="SH Camp", slug="sh-camp", settings={"rollover_hour": 0, "timezone": "UTC"})


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="SH Camp Summer 2026",
        slug="sh-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="cnsl@sh.test", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org, first_name="Mira", last_name="Sand", user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )


@pytest.fixture
def self_template(org, program):
    from bunk_logs.api.tests.conftest import make_active_assignment

    t = ReflectionTemplate.all_objects.create(
        organization=org,
        name="Counselor Self",
        slug="counselor-self-sh",
        cadence="daily",
        subject_mode="self",
        role="counselor",
        schema=SELF_SCHEMA,
        languages=["en"],
        is_active=True,
        program_type="summer_camp",
    )
    make_active_assignment(template=t, program=program, target_role="counselor")
    return t


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


def _submit(organization, program, person, template, target_date, answers):
    return Reflection.all_objects.create(
        organization=organization,
        program=program,
        author=person,
        subject=person,
        template=template,
        period_start=target_date,
        period_end=target_date,
        answers=answers,
        is_complete=True,
        language="en",
    )


@pytest.mark.django_db
def test_history_empty_when_no_template(
    org, counselor_user, counselor_person, counselor_membership,
):
    # See test_counselor_dashboard.py for rationale — drop the seeded
    # global template so this exercises the "no template configured"
    # path rather than the always-available global path.
    ReflectionTemplate.all_objects.filter(
        organization__isnull=True, slug="counselor-self-reflection",
    ).delete()
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/self-reflection/history/")
    assert resp.status_code == 200
    assert resp.data["results"] == []


@pytest.mark.django_db
def test_history_default_page_returns_14_day_grid(
    org, counselor_user, counselor_person, counselor_membership, self_template,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/self-reflection/history/")
    assert resp.status_code == 200
    assert len(resp.data["results"]) == 14


@pytest.mark.django_db
def test_history_records_submission_and_day_off(
    org, program, counselor_user, counselor_person, counselor_membership, self_template,
):
    today = get_today(org)
    _submit(org, program, counselor_person, self_template, today, {"elaboration": "OK"})
    _submit(
        org, program, counselor_person, self_template, today - timedelta(days=1),
        {"day_off": True},
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/self-reflection/history/")
    by_date = {row["date"]: row for row in resp.data["results"]}
    today_row = by_date[today.isoformat()]
    assert today_row["submitted"] is True
    assert today_row["is_day_off"] is False
    assert today_row["editable"] is True

    yest_row = by_date[(today - timedelta(days=1)).isoformat()]
    assert yest_row["submitted"] is True
    assert yest_row["is_day_off"] is True
    assert yest_row["editable"] is False


@pytest.mark.django_db
def test_history_marks_missing_days_as_gaps(
    org, program, counselor_user, counselor_person, counselor_membership, self_template,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/self-reflection/history/")
    # Every row should have submitted=False / no reflection_id when no
    # reflections exist for the viewer.
    for row in resp.data["results"]:
        assert row["submitted"] is False
        assert row["reflection_id"] is None


@pytest.mark.django_db
def test_history_pagination_advances_window(
    org, program, counselor_user, counselor_person, counselor_membership, self_template,
):
    today = get_today(org)
    _submit(
        org, program, counselor_person, self_template,
        today - timedelta(days=15),
        {"elaboration": "Older"},
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        page_one = c.get("/api/v1/counselor/self-reflection/history/?page=1")
        page_two = c.get("/api/v1/counselor/self-reflection/history/?page=2")
    dates_one = {row["date"] for row in page_one.data["results"]}
    dates_two = {row["date"] for row in page_two.data["results"]}
    assert dates_one.isdisjoint(dates_two)
    older = (today - timedelta(days=15)).isoformat()
    assert older in dates_two


@pytest.mark.django_db
def test_history_returns_text_preview(
    org, program, counselor_user, counselor_person, counselor_membership, self_template,
):
    today = get_today(org)
    _submit(org, program, counselor_person, self_template, today, {"elaboration": "Excellent day"})
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/self-reflection/history/")
    today_row = next(r for r in resp.data["results"] if r["date"] == today.isoformat())
    assert "Excellent" in today_row["preview"]

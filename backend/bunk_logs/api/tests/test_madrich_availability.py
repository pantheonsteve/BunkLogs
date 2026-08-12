"""Tests for the Madrich Sunday availability calendar — Step 4_7.

Coverage
--------
* model: unique constraint, Sunday validation, session-list membership.
* GET: upcoming sessions with correct ``editable`` flag across the
  Saturday-18:00-ET boundary (MA6).
* PUT: upsert across all 3 statuses; 403 after the deadline; 400 for a
  non-session date.
* DELETE: clears the row; 403 after the deadline.
* Cross-org: a Crane Lake madrich/counselor gets 403 on TBE URLs.
* Dashboard: ``availability.upcoming_unset_count`` matches DB state.
"""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import MadrichAvailability
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.time_utils import get_today

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(org_slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": org_slug}


def _next_sunday_on_or_after(d: date) -> date:
    return d + timedelta(days=(6 - d.weekday()) % 7)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org():
    return Organization.objects.create(name="TBE", slug="tbe-availability-test")


@pytest.fixture
def session_dates(org):
    """Two upcoming Sundays, several weeks out to avoid boundary flakiness."""
    today = get_today(org)
    first = _next_sunday_on_or_after(today + timedelta(days=14))
    second = first + timedelta(days=7)
    return [first, second]


@pytest.fixture
def program(org, session_dates):
    today = get_today(org)
    return Program.all_objects.create(
        organization=org,
        name="TBE Religious School 2026-27",
        slug="rs-2026-27",
        program_type="religious_school",
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=300),
        settings={"session_dates": [d.isoformat() for d in session_dates]},
    )


@pytest.fixture
def madrich_user_person(org, program):
    user = User.objects.create_user(email="madrich@tbe.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Maya", last_name="Madrich", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="madrich", is_active=True, grade_level=10,
    )
    return person, user


@pytest.fixture
def other_user(org, program):
    """A user who is NOT a Madrich (counselor role for contrast)."""
    user = User.objects.create_user(email="counselor@tbe.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Other", last_name="User", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    return person, user


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def madrich_api(madrich_user_person, api):
    _, user = madrich_user_person
    api.force_authenticate(user=user)
    return api


# ---------------------------------------------------------------------------
# Model (AC1)
# ---------------------------------------------------------------------------


class TestMadrichAvailabilityModel:
    def test_unique_constraint_per_program_person_session(self, org, program, madrich_user_person, session_dates):
        person, _ = madrich_user_person
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=person,
            session_date=session_dates[0], status="available",
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            MadrichAvailability.all_objects.create(
                organization=org, program=program, person=person,
                session_date=session_dates[0], status="unavailable",
            )

    def test_clean_rejects_non_sunday(self, org, program, madrich_user_person, session_dates):
        person, _ = madrich_user_person
        monday = session_dates[0] - timedelta(days=6)
        row = MadrichAvailability(
            organization=org, program=program, person=person,
            session_date=monday, status="available",
        )
        with pytest.raises(ValidationError):
            row.clean()

    def test_clean_rejects_session_date_not_in_program_list(self, org, program, madrich_user_person, session_dates):
        person, _ = madrich_user_person
        off_list_sunday = session_dates[-1] + timedelta(days=7)
        row = MadrichAvailability(
            organization=org, program=program, person=person,
            session_date=off_list_sunday, status="available",
        )
        with pytest.raises(ValidationError):
            row.clean()

    def test_clean_allows_any_sunday_when_session_list_empty(self, org, madrich_user_person):
        person, _ = madrich_user_person
        empty_program = Program.all_objects.create(
            organization=org, name=f"{org.name} No Sessions Configured", slug="no-sessions",
            program_type="religious_school",
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=300),
        )
        row = MadrichAvailability(
            organization=org, program=empty_program, person=person,
            session_date=_next_sunday_on_or_after(date.today() + timedelta(days=7)),
            status="available",
        )
        row.clean()  # no exception


# ---------------------------------------------------------------------------
# GET (AC2)
# ---------------------------------------------------------------------------


class TestMadrichAvailabilityGet:
    def test_get_returns_upcoming_sessions_unset(self, madrich_api, org, session_dates):
        with organization_context(org):
            r = madrich_api.get("/api/v1/madrich/availability/", **_hdr(org.slug))
        assert r.status_code == 200
        data = r.json()
        assert data["edit_deadline_rule"] == "saturday_18:00_eastern"
        assert [s["session_date"] for s in data["sessions"]] == [d.isoformat() for d in session_dates]
        assert all(s["commitment"] is None for s in data["sessions"])

    def test_get_includes_existing_commitment(self, madrich_api, org, program, madrich_user_person, session_dates):
        person, _ = madrich_user_person
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=person,
            session_date=session_dates[0], status="tentative", note="Might be late",
        )
        with organization_context(org):
            r = madrich_api.get("/api/v1/madrich/availability/", **_hdr(org.slug))
        first = r.json()["sessions"][0]
        assert first["commitment"] == {
            "status": "tentative", "note": "Might be late",
            "updated_at": first["commitment"]["updated_at"],
        }

    def test_get_editable_boundary_across_saturday_18_00_eastern(
        self, madrich_api, org, session_dates,
    ):
        """MA6: editable before Saturday 18:00 ET, locked at/after it."""
        session_date = session_dates[0]
        saturday_before = session_date - timedelta(days=1)
        friday_before = saturday_before - timedelta(days=1)

        friday_evening = datetime(
            friday_before.year, friday_before.month, friday_before.day,
            19, 0, tzinfo=ZoneInfo("America/New_York"),
        )
        with patch("bunk_logs.core.scheduling.availability_windows.timezone") as mock_tz:
            mock_tz.now.return_value = friday_evening
            with organization_context(org):
                r = madrich_api.get("/api/v1/madrich/availability/", **_hdr(org.slug))
        assert r.json()["sessions"][0]["editable"] is True

        saturday_after_deadline = datetime(
            saturday_before.year, saturday_before.month, saturday_before.day,
            19, 0, tzinfo=ZoneInfo("America/New_York"),
        )
        with patch("bunk_logs.core.scheduling.availability_windows.timezone") as mock_tz:
            mock_tz.now.return_value = saturday_after_deadline
            with organization_context(org):
                r = madrich_api.get("/api/v1/madrich/availability/", **_hdr(org.slug))
        assert r.json()["sessions"][0]["editable"] is False

    def test_get_403_for_non_madrich(self, api, org, other_user):
        _, user = other_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/madrich/availability/", **_hdr(org.slug))
        assert r.status_code == 403

    def test_get_403_unauthenticated(self, api, org):
        with organization_context(org):
            r = api.get("/api/v1/madrich/availability/", **_hdr(org.slug))
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT / DELETE (AC2)
# ---------------------------------------------------------------------------


class TestMadrichAvailabilityUpsert:
    def test_put_upserts_across_all_statuses(self, madrich_api, org, session_dates):
        session_date = session_dates[0].isoformat()
        for status in ["available", "tentative", "unavailable"]:
            with organization_context(org):
                r = madrich_api.put(
                    f"/api/v1/madrich/availability/{session_date}/",
                    {"status": status, "note": ""},
                    format="json",
                    **_hdr(org.slug),
                )
            assert r.status_code == 200, r.json()
            assert r.json()["commitment"]["status"] == status
        assert MadrichAvailability.all_objects.filter(session_date=session_dates[0]).count() == 1

    def test_put_400_for_non_session_date(self, madrich_api, org, session_dates):
        off_list_sunday = (session_dates[-1] + timedelta(days=7)).isoformat()
        with organization_context(org):
            r = madrich_api.put(
                f"/api/v1/madrich/availability/{off_list_sunday}/",
                {"status": "available"},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400

    def test_put_403_after_edit_deadline(self, madrich_api, org, session_dates):
        session_date = session_dates[0]
        after_deadline = datetime(
            session_date.year, session_date.month, session_date.day,
            12, 0, tzinfo=ZoneInfo("America/New_York"),
        )
        with patch("bunk_logs.core.scheduling.availability_windows.timezone") as mock_tz:
            mock_tz.now.return_value = after_deadline
            with organization_context(org):
                r = madrich_api.put(
                    f"/api/v1/madrich/availability/{session_date.isoformat()}/",
                    {"status": "available"},
                    format="json",
                    **_hdr(org.slug),
                )
        assert r.status_code == 403

    def test_delete_clears_commitment(self, madrich_api, org, program, madrich_user_person, session_dates):
        person, _ = madrich_user_person
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=person,
            session_date=session_dates[0], status="available",
        )
        with organization_context(org):
            r = madrich_api.delete(
                f"/api/v1/madrich/availability/{session_dates[0].isoformat()}/",
                **_hdr(org.slug),
            )
        assert r.status_code == 204
        assert not MadrichAvailability.all_objects.filter(
            person=person, session_date=session_dates[0],
        ).exists()

    def test_delete_403_after_edit_deadline(self, madrich_api, org, program, madrich_user_person, session_dates):
        person, _ = madrich_user_person
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=person,
            session_date=session_dates[0], status="available",
        )
        session_date = session_dates[0]
        after_deadline = datetime(
            session_date.year, session_date.month, session_date.day,
            12, 0, tzinfo=ZoneInfo("America/New_York"),
        )
        with patch("bunk_logs.core.scheduling.availability_windows.timezone") as mock_tz:
            mock_tz.now.return_value = after_deadline
            with organization_context(org):
                r = madrich_api.delete(
                    f"/api/v1/madrich/availability/{session_date.isoformat()}/",
                    **_hdr(org.slug),
                )
        assert r.status_code == 403

    def test_put_403_for_non_madrich(self, api, org, other_user, session_dates):
        _, user = other_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.put(
                f"/api/v1/madrich/availability/{session_dates[0].isoformat()}/",
                {"status": "available"},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Cross-org isolation
# ---------------------------------------------------------------------------


class TestMadrichAvailabilityCrossOrg:
    def test_other_org_madrich_gets_403(self, api, session_dates):
        other_org = Organization.objects.create(name="Crane Lake", slug="clc-availability-test")
        other_program = Program.all_objects.create(
            organization=other_org, name="Crane Lake Summer", slug="clc-summer",
            program_type="summer_camp",
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=60),
        )
        user = User.objects.create_user(email="clc-madrich@example.test", password="pw")
        person = Person.all_objects.create(
            organization=other_org, first_name="CLC", last_name="Person", user=user,
        )
        Membership.all_objects.create(
            program=other_program, person=person, role="counselor", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(other_org):
            r = api.get("/api/v1/madrich/availability/", **_hdr(other_org.slug))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Dashboard summary (AC3)
# ---------------------------------------------------------------------------


class TestMadrichDashboardAvailabilitySummary:
    def test_dashboard_availability_summary_matches_db(
        self, madrich_api, org, program, madrich_user_person, session_dates,
    ):
        person, _ = madrich_user_person
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=person,
            session_date=session_dates[0], status="available",
        )
        with organization_context(org):
            r = madrich_api.get("/api/v1/madrich/dashboard/", **_hdr(org.slug))
        assert r.status_code == 200
        availability = r.json()["availability"]
        assert availability["upcoming_unset_count"] == 1
        assert availability["next_session_date"] == session_dates[0].isoformat()
        assert availability["next_session_status"] == "available"
        assert availability["calendar_url"] == "/madrich/availability"

    def test_dashboard_availability_all_unset(
        self, madrich_api, org, session_dates,
    ):
        with organization_context(org):
            r = madrich_api.get("/api/v1/madrich/dashboard/", **_hdr(org.slug))
        availability = r.json()["availability"]
        assert availability["upcoming_unset_count"] == len(session_dates)
        assert availability["next_session_status"] is None

"""Tests for the org-admin Madrich availability staffing matrix — Step 4_7 AC4.

Coverage
--------
* admin sees the full matrix (all Madrichim x upcoming sessions) with
  correct ``available``/``unset`` summary counts.
* CSV export returns the expected header row and one data row per
  (Madrich, session) pair.
* non-admin roles are rejected.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
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


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Admin Availability TBE", slug="admin-availability-tbe")


@pytest.fixture
def session_dates(org):
    today = get_today(org)
    first = today + timedelta(days=(6 - today.weekday()) % 7 + 14)
    return [first, first + timedelta(days=7), first + timedelta(days=14)]


@pytest.fixture
def program(org, session_dates):
    today = get_today(org)
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Religious School",
        slug="admin-availability-rs",
        program_type="religious_school",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=200),
        settings={"session_dates": [d.isoformat() for d in session_dates]},
    )


@pytest.fixture
def admin_user(org, program):
    user = User.objects.create_user(email="admin@availability.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ada", last_name="Admin", user=user,
    )
    Membership.all_objects.create(program=program, person=person, role="admin", is_active=True)
    return user


@pytest.fixture
def madrichim(org, program):
    def _make(first, last, grade_level):
        person = Person.all_objects.create(organization=org, first_name=first, last_name=last)
        Membership.all_objects.create(
            program=program, person=person, role="madrich", is_active=True, grade_level=grade_level,
        )
        return person
    return [
        _make("Maya", "Alpha", 8),
        _make("Ben", "Beta", 10),
        _make("Cyd", "Gamma", 12),
    ]


class TestAdminMadrichAvailabilityMatrix:
    def test_admin_sees_full_matrix_with_correct_counts(
        self, api, org, program, admin_user, madrichim, session_dates,
    ):
        api.force_authenticate(user=admin_user)
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=madrichim[0],
            session_date=session_dates[0], status="available",
        )
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=madrichim[1],
            session_date=session_dates[0], status="unavailable",
        )
        # madrichim[2] leaves session_dates[0] unset.

        with organization_context(org):
            r = api.get("/api/v1/admin/madrich-availability/", **_hdr(org.slug))
        assert r.status_code == 200
        data = r.json()
        assert data["program"]["slug"] == program.slug
        assert data["sessions"] == [d.isoformat() for d in session_dates]
        assert len(data["rows"]) == 3
        # Sorted by grade then name.
        assert [row["display_name"] for row in data["rows"]] == ["Maya Alpha", "Ben Beta", "Cyd Gamma"]

        summary = data["summary"]
        assert summary["available_counts"][session_dates[0].isoformat()] == 1
        assert summary["unset_counts"][session_dates[0].isoformat()] == 1

    def test_admin_matrix_defaults_to_next_8_sessions(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/admin/madrich-availability/", **_hdr(org.slug))
        assert r.status_code == 200
        assert len(r.json()["sessions"]) <= 8

    def test_csv_export_headers_and_row_count(
        self, api, org, program, admin_user, madrichim, session_dates,
    ):
        api.force_authenticate(user=admin_user)
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=madrichim[0],
            session_date=session_dates[0], status="available",
        )

        with organization_context(org):
            r = api.get("/api/v1/admin/madrich-availability/export.csv", **_hdr(org.slug))
        assert r.status_code == 200
        assert r["Content-Type"] == "text/csv"
        lines = r.content.decode().strip().splitlines()
        assert lines[0] == "session_date,first_name,last_name,grade_level,status,note,updated_at"
        # One row per (madrich, session) pair.
        assert len(lines) - 1 == len(madrichim) * len(session_dates)

    def test_ignores_later_starting_program_with_no_madrich_members(
        self, api, org, program, admin_user, madrichim, session_dates,
    ):
        """A newer program (e.g. next year's cohort scaffolded early) with no
        active madrich memberships must not shadow the program actually in
        use just because it starts later.
        """
        today = get_today(org)
        Program.all_objects.create(
            organization=org,
            name=f"{org.name} Next Year",
            slug="admin-availability-next-year",
            program_type="religious_school",
            start_date=today + timedelta(days=200),
            end_date=today + timedelta(days=560),
        )

        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/admin/madrich-availability/", **_hdr(org.slug))
        assert r.status_code == 200
        assert r.json()["program"]["slug"] == program.slug

    def test_non_admin_gets_403(self, api, org, program, session_dates):
        user = User.objects.create_user(email="counselor@availability.test", password="pw")
        person = Person.all_objects.create(organization=org, first_name="Not", last_name="Admin", user=user)
        Membership.all_objects.create(program=program, person=person, role="counselor", is_active=True)
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/admin/madrich-availability/", **_hdr(org.slug))
        assert r.status_code == 403

    def test_unauthenticated_gets_401_or_403(self, api, org):
        with organization_context(org):
            r = api.get("/api/v1/admin/madrich-availability/", **_hdr(org.slug))
        assert r.status_code in (401, 403)

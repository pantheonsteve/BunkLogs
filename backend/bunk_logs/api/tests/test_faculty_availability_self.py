"""Tests for a faculty member's own Sunday availability.

Coverage
--------
* GET lists the program's upcoming Sundays with the viewer's commitments.
* PUT upserts, and 403s once the Saturday-18:00 window has closed (MA6).
* a non-faculty viewer is rejected.
* the availability task appears on ``my-tasks`` for faculty, tracks the
  next session, and stays away from programs with no session dates.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

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
    return Organization.objects.create(name="Faculty Self TBE", slug="faculty-self-tbe")


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
        slug="faculty-self-rs",
        program_type="religious_school",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=200),
        settings={"session_dates": [d.isoformat() for d in session_dates]},
    )


@pytest.fixture
def faculty(org, program):
    user = User.objects.create_user(email="fac-self@availability.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Fran", last_name="Teacher", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="faculty", is_active=True,
    )
    return person, user


@pytest.fixture
def faculty_api(api, faculty):
    _, user = faculty
    api.force_authenticate(user=user)
    return api


class TestFacultyAvailabilitySelf:
    def test_get_lists_upcoming_sessions_with_commitments(
        self, faculty_api, org, program, faculty, session_dates,
    ):
        person, _ = faculty
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=person,
            session_date=session_dates[0], status="available", note="Driving myself",
        )
        with organization_context(org):
            r = faculty_api.get("/api/v1/faculty/availability/", **_hdr(org.slug))
        assert r.status_code == 200, r.json()
        body = r.json()
        assert body["program"]["slug"] == program.slug
        assert [s["session_date"] for s in body["sessions"]] == [
            d.isoformat() for d in session_dates
        ]
        assert body["sessions"][0]["commitment"]["status"] == "available"
        assert body["sessions"][0]["commitment"]["note"] == "Driving myself"
        # Unanswered is distinct from "can't come".
        assert body["sessions"][1]["commitment"] is None

    def test_put_upserts_and_locks_after_the_saturday_deadline(
        self, faculty_api, org, session_dates,
    ):
        session_date = session_dates[0]
        with organization_context(org):
            r = faculty_api.put(
                f"/api/v1/faculty/availability/{session_date.isoformat()}/",
                {"status": "tentative", "note": " Might be late "},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200, r.json()
        assert r.json()["commitment"] == {
            "status": "tentative",
            "note": "Might be late",
            "updated_at": r.json()["commitment"]["updated_at"],
        }

        after_deadline = datetime(
            session_date.year, session_date.month, session_date.day,
            12, 0, tzinfo=ZoneInfo("America/New_York"),
        )
        with patch("bunk_logs.core.scheduling.availability_windows.timezone") as mock_tz:
            mock_tz.now.return_value = after_deadline
            with organization_context(org):
                r = faculty_api.put(
                    f"/api/v1/faculty/availability/{session_date.isoformat()}/",
                    {"status": "available"},
                    format="json",
                    **_hdr(org.slug),
                )
        assert r.status_code == 403

    def test_put_400_for_a_date_off_the_program_session_list(
        self, faculty_api, org, session_dates,
    ):
        off_list_sunday = (session_dates[-1] + timedelta(days=7)).isoformat()
        with organization_context(org):
            r = faculty_api.put(
                f"/api/v1/faculty/availability/{off_list_sunday}/",
                {"status": "available"},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400

    def test_delete_clears_the_commitment(
        self, faculty_api, org, program, faculty, session_dates,
    ):
        person, _ = faculty
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=person,
            session_date=session_dates[0], status="available",
        )
        with organization_context(org):
            r = faculty_api.delete(
                f"/api/v1/faculty/availability/{session_dates[0].isoformat()}/",
                **_hdr(org.slug),
            )
        assert r.status_code == 204
        assert not MadrichAvailability.all_objects.filter(person=person).exists()

    def test_non_faculty_viewer_is_rejected(self, api, org, program, session_dates):
        user = User.objects.create_user(email="madrich-self@availability.test", password="pw")
        person = Person.all_objects.create(
            organization=org, first_name="Mo", last_name="Rich", user=user,
        )
        Membership.all_objects.create(
            program=program, person=person, role="madrich", is_active=True,
        )
        api.force_authenticate(user=user)
        with organization_context(org):
            get = api.get("/api/v1/faculty/availability/", **_hdr(org.slug))
            put = api.put(
                f"/api/v1/faculty/availability/{session_dates[0].isoformat()}/",
                {"status": "available"},
                format="json",
                **_hdr(org.slug),
            )
        assert get.status_code == 403
        assert put.status_code == 403


class TestFacultyAvailabilityTask:
    def test_my_tasks_carries_the_availability_row_and_tracks_the_next_session(
        self, faculty_api, org, program, faculty, session_dates,
    ):
        with organization_context(org):
            r = faculty_api.get("/api/v1/reflections/my-tasks/", **_hdr(org.slug))
        assert r.status_code == 200, r.json()
        task = next(t for t in r.json()["tasks"] if t["kind"] == "availability")
        assert task["title"] == "My Sunday availability"
        assert task["availability"]["calendar_url"] == "/faculty/availability"
        assert task["availability"]["next_session_date"] == session_dates[0].isoformat()
        assert task["availability"]["next_session_status"] is None
        assert task["availability"]["upcoming_unset_count"] == len(session_dates)
        # Preview is capped for the card's status strip.
        assert len(task["availability"]["sessions"]) <= 4
        assert task["completion"] == {"covered": 0, "total": 1, "my_count": 0}

        person, _ = faculty
        MadrichAvailability.all_objects.create(
            organization=org, program=program, person=person,
            session_date=session_dates[0], status="available",
        )
        with organization_context(org):
            r = faculty_api.get("/api/v1/reflections/my-tasks/", **_hdr(org.slug))
        task = next(t for t in r.json()["tasks"] if t["kind"] == "availability")
        assert task["availability"]["next_session_status"] == "available"
        assert task["completion"]["covered"] == 1

    def test_no_availability_task_without_configured_session_dates(
        self, faculty_api, org, program,
    ):
        program.settings = {}
        program.save(update_fields=["settings"])
        with organization_context(org):
            r = faculty_api.get("/api/v1/reflections/my-tasks/", **_hdr(org.slug))
        assert r.status_code == 200
        assert all(t["kind"] != "availability" for t in r.json()["tasks"])

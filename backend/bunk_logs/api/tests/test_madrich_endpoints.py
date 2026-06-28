"""Tests for the Madrich (TBE) flow — Step 7_14, Stories 61-65.

Coverage
--------
* dashboard: happy path, missing reflection state, current-week framing,
  permissions (non-madrich gets 403).
* reflection create: happy path with full 3-2-1 schema, idempotency via
  client_submission_id, schema validation (text_list exact counts and
  rating_group required categories), no day_off shortcut, period spans
  Monday-Sunday.
* reflection edit: in-window edit allowed, post-week-close edit blocked.
* reflection history: weekly periods returned, current-week row editable,
  gap rows for weeks without a submission.
* visibility (Story 64): Madrich author, Director (LT supervising madrich),
  and TBE Admin see the reflection; other roles do not.
"""

from __future__ import annotations

import uuid
from datetime import date
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import Supervision
from bunk_logs.core.time_utils import get_today

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(org_slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": org_slug}


def _full_answers() -> dict:
    """A valid TBE 3-2-1 payload that passes schema validation."""
    return {
        "wins": ["Punctual every session", "Helped student lead Torah", "Ran clean tefillah"],
        "improvements": ["Plan ahead more", "Engage quieter students"],
        "question_or_concern": "Can we get more time for one-on-ones?",
        "ratings": {
            "reliability_punctuality": 4,
            "initiative": 3,
            "communication": 3,
            "problem_solving": 3,
            "interpersonal": 4,
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org():
    return Organization.objects.create(name="TBE", slug="tbe-madrich-test")


@pytest.fixture
def program(org):
    today = get_today(org)
    return Program.all_objects.create(
        organization=org,
        name="TBE Religious School 2026-27",
        slug="rs-2026-27",
        program_type="religious_school",
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=200),
    )


@pytest.fixture
def madrich_user_person(org, program):
    user = User.objects.create_user(email="madrich@tbe.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Maya", last_name="Madrich", user=user,
        preferred_language="en",
    )
    Membership.all_objects.create(
        program=program, person=person, role="madrich", is_active=True,
        grade_level=10,
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
# Dashboard tests (Story 61)
# ---------------------------------------------------------------------------


class TestMadrichDashboard:
    def test_dashboard_happy_path(self, madrich_api, org, program, madrich_user_person):
        with organization_context(org):
            r = madrich_api.get("/api/v1/madrich/dashboard/", **_hdr(org.slug))
        assert r.status_code == 200
        data = r.json()
        assert data["header"]["role_label"] == "Madrich"
        assert data["header"]["name"] == "Maya Madrich"
        assert data["header"]["grade_level"] == 10
        assert data["header"]["program_name"] == program.name
        assert data["period"]["cadence"] == "weekly"
        assert data["my_reflection"]["state"] == "missing"

    def test_dashboard_period_is_monday_to_sunday(self, madrich_api, org):
        """Story 61 c5.i + MA1: period framing 'Week of [start]-[end]', Mon-Sun."""
        with organization_context(org):
            r = madrich_api.get("/api/v1/madrich/dashboard/", **_hdr(org.slug))
        period = r.json()["period"]
        start = date.fromisoformat(period["start"])
        end = date.fromisoformat(period["end"])
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6  # Sunday
        assert (end - start).days == 6

    def test_dashboard_state_complete_after_submission(
        self, madrich_api, org, program, madrich_user_person,
    ):
        with organization_context(org):
            madrich_api.post(
                "/api/v1/madrich/reflection/",
                {
                    "answers": _full_answers(),
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
            r = madrich_api.get("/api/v1/madrich/dashboard/", **_hdr(org.slug))
        body = r.json()
        assert body["my_reflection"]["state"] == "complete"
        assert body["my_reflection"]["editable"] is True

    def test_dashboard_403_for_non_madrich(self, api, org, other_user):
        _, user = other_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get("/api/v1/madrich/dashboard/", **_hdr(org.slug))
        assert r.status_code == 403

    def test_dashboard_403_unauthenticated(self, api, org):
        with organization_context(org):
            r = api.get("/api/v1/madrich/dashboard/", **_hdr(org.slug))
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Reflection create (Story 62)
# ---------------------------------------------------------------------------


class TestMadrichReflectionCreate:
    def test_create_happy_path_with_full_3_2_1_payload(
        self, madrich_api, org, program,
    ):
        with organization_context(org):
            r = madrich_api.post(
                "/api/v1/madrich/reflection/",
                {
                    "answers": _full_answers(),
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 201, r.json()
        data = r.json()
        assert data["answers"]["wins"] == _full_answers()["wins"]
        # Period spans Monday-Sunday per MA1.
        start = date.fromisoformat(data["period_start"])
        end = date.fromisoformat(data["period_end"])
        assert start.weekday() == 0
        assert end.weekday() == 6

    def test_create_rejects_fewer_than_three_wins(self, madrich_api, org):
        answers = _full_answers()
        answers["wins"] = ["Only one"]
        with organization_context(org):
            r = madrich_api.post(
                "/api/v1/madrich/reflection/",
                {
                    "answers": answers,
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "wins" in str(r.json()).lower() or "at least 3" in str(r.json())

    def test_create_rejects_more_than_two_improvements(self, madrich_api, org):
        answers = _full_answers()
        answers["improvements"] = ["A", "B", "C"]
        with organization_context(org):
            r = madrich_api.post(
                "/api/v1/madrich/reflection/",
                {
                    "answers": answers,
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "improvements" in str(r.json()).lower() or "at most 2" in str(r.json())

    def test_create_rejects_missing_rating_category(self, madrich_api, org):
        answers = _full_answers()
        del answers["ratings"]["initiative"]
        with organization_context(org):
            r = madrich_api.post(
                "/api/v1/madrich/reflection/",
                {
                    "answers": answers,
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "initiative" in str(r.json())

    def test_create_idempotent(self, madrich_api, org):
        cid = str(uuid.uuid4())
        payload = {
            "answers": _full_answers(),
            "language": "en",
            "client_submission_id": cid,
        }
        with organization_context(org):
            r1 = madrich_api.post(
                "/api/v1/madrich/reflection/", payload, format="json", **_hdr(org.slug),
            )
            r2 = madrich_api.post(
                "/api/v1/madrich/reflection/", payload, format="json", **_hdr(org.slug),
            )
        assert r1.status_code == 201
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]

    def test_create_403_for_non_madrich(self, api, org, other_user):
        _, user = other_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.post(
                "/api/v1/madrich/reflection/",
                {
                    "answers": _full_answers(),
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Reflection edit (Story 62 c5-6)
# ---------------------------------------------------------------------------


class TestMadrichReflectionEdit:
    def _create(self, api, org):
        with organization_context(org):
            r = api.post(
                "/api/v1/madrich/reflection/",
                {
                    "answers": _full_answers(),
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        return r.json()

    def test_edit_within_current_week(self, madrich_api, org):
        reflection = self._create(madrich_api, org)
        new_answers = _full_answers()
        new_answers["question_or_concern"] = "Updated question after reflection."
        with organization_context(org):
            r = madrich_api.patch(
                f"/api/v1/madrich/reflection/{reflection['id']}/",
                {"answers": new_answers},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200, r.json()
        assert r.json()["answers"]["question_or_concern"] == "Updated question after reflection."

    def test_edit_after_week_closes_blocked(self, madrich_api, org):
        reflection = self._create(madrich_api, org)

        ref_obj = Reflection.all_objects.get(id=reflection["id"])
        ref_obj.period_start = date.today() - timedelta(days=21)
        ref_obj.period_end = date.today() - timedelta(days=15)
        ref_obj.save(update_fields=["period_start", "period_end"])

        with organization_context(org):
            r = madrich_api.patch(
                f"/api/v1/madrich/reflection/{reflection['id']}/",
                {"answers": _full_answers()},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_edit_403_for_wrong_user(
        self, api, org, program, madrich_user_person, other_user,
    ):
        _, madrich_user = madrich_user_person
        api.force_authenticate(user=madrich_user)
        reflection = self._create(api, org)

        _, ou = other_user
        api.force_authenticate(user=ou)
        with organization_context(org):
            r = api.patch(
                f"/api/v1/madrich/reflection/{reflection['id']}/",
                {"answers": _full_answers()},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Reflection history (Story 65)
# ---------------------------------------------------------------------------


class TestMadrichReflectionHistory:
    def test_history_returns_weekly_periods(self, madrich_api, org, program):
        with organization_context(org):
            madrich_api.post(
                "/api/v1/madrich/reflection/",
                {
                    "answers": _full_answers(),
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
            r = madrich_api.get(
                "/api/v1/madrich/reflection/history/", **_hdr(org.slug),
            )
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) >= 1
        # First row is current week and editable.
        first = results[0]
        first_start = date.fromisoformat(first["period_start"])
        first_end = date.fromisoformat(first["period_end"])
        assert first_start.weekday() == 0
        assert first_end.weekday() == 6
        assert first["submitted"] is True
        assert first["editable"] is True

    def test_history_includes_gap_rows_for_missing_weeks(
        self, madrich_api, org, program,
    ):
        """Story 65 c4: weeks with no submission appear as gaps."""
        with organization_context(org):
            r = madrich_api.get(
                "/api/v1/madrich/reflection/history/?page_size=5",
                **_hdr(org.slug),
            )
        results = r.json()["results"]
        # No submissions yet -> every row is a gap.
        assert all(row["submitted"] is False for row in results)
        assert all(row["reflection_id"] is None for row in results)

    def test_history_403_for_non_madrich(self, api, org, other_user):
        _, user = other_user
        api.force_authenticate(user=user)
        with organization_context(org):
            r = api.get(
                "/api/v1/madrich/reflection/history/", **_hdr(org.slug),
            )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Visibility (Story 64): Director + TBE Admin see Madrich reflections
# ---------------------------------------------------------------------------


class TestMadrichVisibility:
    """The visibility filter is the source of truth for Story 64."""

    def _create_reflection(self, madrich_api, org):
        with organization_context(org):
            r = madrich_api.post(
                "/api/v1/madrich/reflection/",
                {
                    "answers": _full_answers(),
                    "language": "en",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
                **_hdr(org.slug),
            )
        return r.json()

    def test_madrich_author_sees_own_reflection(
        self, madrich_api, madrich_user_person, org,
    ):
        _, user = madrich_user_person
        self._create_reflection(madrich_api, org)
        with organization_context(org):
            visible = list(reflections_visible_for_user(user))
        assert len(visible) == 1

    def test_director_lt_with_supervision_sees_madrich_reflection(
        self, madrich_api, madrich_user_person, org, program,
    ):
        self._create_reflection(madrich_api, org)

        director_user = User.objects.create_user(
            email="director@tbe.test", password="pw",
        )
        director_person = Person.all_objects.create(
            organization=org, first_name="Rachel", last_name="Director",
            user=director_user,
        )
        director_mem = Membership.all_objects.create(
            program=program, person=director_person, role="leadership_team",
            is_active=True,
        )
        Supervision.objects.create(
            supervisor_membership=director_mem,
            target_type=Supervision.TargetType.ROLE_IN_PROGRAM,
            target_role="madrich",
            target_program=program,
            start_date=date.today() - timedelta(days=30),
        )

        with organization_context(org):
            visible = list(reflections_visible_for_user(director_user))
        assert len(visible) == 1

    def test_tbe_admin_sees_madrich_reflection(
        self, madrich_api, madrich_user_person, org, program,
    ):
        self._create_reflection(madrich_api, org)

        admin_user = User.objects.create_user(
            email="admin@tbe.test", password="pw",
        )
        admin_person = Person.all_objects.create(
            organization=org, first_name="TBE", last_name="Admin",
            user=admin_user,
        )
        Membership.all_objects.create(
            program=program, person=admin_person, role="admin", is_active=True,
        )

        with organization_context(org):
            visible = list(reflections_visible_for_user(admin_user))
        assert len(visible) == 1

    def test_unrelated_role_does_not_see_madrich_reflection(
        self, madrich_api, madrich_user_person, org, other_user,
    ):
        self._create_reflection(madrich_api, org)
        _, other = other_user

        with organization_context(org):
            visible = list(reflections_visible_for_user(other))
        assert len(visible) == 0

    def test_other_madrich_does_not_see_peer_reflection(
        self, madrich_api, madrich_user_person, org, program,
    ):
        """Story 64 c4: a Madrich does not see other Madrichim's reflections."""
        self._create_reflection(madrich_api, org)

        peer_user = User.objects.create_user(
            email="peer-madrich@tbe.test", password="pw",
        )
        peer_person = Person.all_objects.create(
            organization=org, first_name="Peer", last_name="Madrich",
            user=peer_user,
        )
        Membership.all_objects.create(
            program=program, person=peer_person, role="madrich", is_active=True,
        )

        with organization_context(org):
            visible = list(reflections_visible_for_user(peer_user))
        assert len(visible) == 0


# ---------------------------------------------------------------------------
# Wednesday-evening reminder dispatch (Story 61 MA2)
# ---------------------------------------------------------------------------


class TestMadrichWeeklyReminderDispatch:
    """The shared reminder dispatcher should queue Madrich reminders on Wed @ 18.

    The dispatcher inspects each program's
    ``settings['reminder_schedules']`` map and uses
    ``timezone.localtime`` to decide what fires now. We mock the local
    time so the test is deterministic without freezing the actual system
    clock.
    """

    @patch("bunk_logs.core.tasks.send_reflection_reminders.delay")
    @patch("bunk_logs.core.tasks.timezone")
    def test_wednesday_evening_dispatches_madrich(
        self, mock_tz, mock_delay, org, program, madrich_user_person,
    ):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        program.settings = {
            "reminder_schedules": {"madrich": "weekly_wednesday_18:00"},
        }
        program.save()

        from bunk_logs.core.tasks import dispatch_reflection_reminders

        # Wednesday 2026-11-04 at 18:00 in Eastern.
        wed_evening = datetime(2026, 11, 4, 18, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_tz.localtime.return_value = wed_evening
        mock_tz.now.return_value = wed_evening

        result = dispatch_reflection_reminders()
        assert any(
            d["program_id"] == program.pk and d["role"] == "madrich"
            for d in result["dispatched"]
        )
        mock_delay.assert_called_with(program.pk, "madrich")

    @patch("bunk_logs.core.tasks.send_reflection_reminders.delay")
    @patch("bunk_logs.core.tasks.timezone")
    def test_tuesday_evening_does_not_dispatch_madrich(
        self, mock_tz, mock_delay, org, program, madrich_user_person,
    ):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        program.settings = {
            "reminder_schedules": {"madrich": "weekly_wednesday_18:00"},
        }
        program.save()

        from bunk_logs.core.tasks import dispatch_reflection_reminders

        tue_evening = datetime(2026, 11, 3, 18, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_tz.localtime.return_value = tue_evening
        mock_tz.now.return_value = tue_evening

        result = dispatch_reflection_reminders()
        assert not any(
            d["role"] == "madrich" for d in result["dispatched"]
        )
        mock_delay.assert_not_called()

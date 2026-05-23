"""Tests for ``bunk_logs.core.time_utils`` (Step 7_6 foundation).

Story 2 criterion 4 / Story 58 require an org-level rollover hour that
determines what "today" means. The helper is exercised at the millisecond
level here because every dashboard endpoint depends on it.
"""
from __future__ import annotations

from datetime import date
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from bunk_logs.core import time_utils
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program

# ---------------------------------------------------------------------------
# get_rollover_hour
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_default_rollover_for_summer_camp_is_4am():
    org = Organization.objects.create(name="Camp", slug="camp")
    Program.all_objects.create(
        organization=org,
        name="Camp Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date="2026-06-01",
        end_date="2026-08-15",
    )
    assert time_utils.get_rollover_hour(org) == 4


@pytest.mark.django_db
def test_default_rollover_for_religious_school_only_is_midnight():
    org = Organization.objects.create(name="TBE", slug="tbe")
    Program.all_objects.create(
        organization=org,
        name="TBE Religious School 2026-27",
        slug="rs-2026-27",
        program_type="religious_school",
        start_date="2026-09-01",
        end_date="2027-05-31",
    )
    assert time_utils.get_rollover_hour(org) == 0


@pytest.mark.django_db
def test_mixed_program_types_keep_camp_default():
    # An org running both camp and religious school keeps the camp default
    # so late-night camp shifts don't get truncated.
    org = Organization.objects.create(name="Mixed Org", slug="mixed")
    Program.all_objects.create(
        organization=org,
        name="Mixed Org Camp 2026",
        slug="camp-2026",
        program_type="summer_camp",
        start_date="2026-06-01",
        end_date="2026-08-15",
    )
    Program.all_objects.create(
        organization=org,
        name="Mixed Org RS 2026-27",
        slug="rs-2026-27",
        program_type="religious_school",
        start_date="2026-09-01",
        end_date="2027-05-31",
    )
    assert time_utils.get_rollover_hour(org) == 4


@pytest.mark.django_db
def test_explicit_override_in_settings_wins():
    org = Organization.objects.create(
        name="LateNight Camp",
        slug="latenight",
        settings={"rollover_hour": 6},
    )
    Program.all_objects.create(
        organization=org,
        name="LateNight Camp Summer 2026",
        slug="ln-2026",
        program_type="summer_camp",
        start_date="2026-06-01",
        end_date="2026-08-15",
    )
    assert time_utils.get_rollover_hour(org) == 6


@pytest.mark.django_db
def test_invalid_rollover_setting_falls_back_to_default():
    # Settings come from a JSONField; a typo or string value silently
    # falls back so a dashboard request doesn't blow up.
    org = Organization.objects.create(
        name="Bad Org", slug="bad", settings={"rollover_hour": "four"},
    )
    Program.all_objects.create(
        organization=org,
        name="Bad Org Summer 2026",
        slug="b-2026",
        program_type="summer_camp",
        start_date="2026-06-01",
        end_date="2026-08-15",
    )
    assert time_utils.get_rollover_hour(org) == 4


def test_no_org_returns_camp_default():
    assert time_utils.get_rollover_hour(None) == time_utils.CAMP_DEFAULT_ROLLOVER_HOUR


# ---------------------------------------------------------------------------
# get_today: rollover boundary behaviour
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_today_before_rollover_returns_yesterday():
    org = Organization.objects.create(name="Camp", slug="camp")
    Program.all_objects.create(
        organization=org,
        name="Camp Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date="2026-06-01",
        end_date="2026-08-15",
    )
    # 03:30 local time -- still yesterday's camp day.
    now = datetime(2026, 7, 15, 3, 30, tzinfo=ZoneInfo("America/New_York"))
    assert time_utils.get_today(org, now=now).isoformat() == "2026-07-14"


@pytest.mark.django_db
def test_get_today_after_rollover_returns_today():
    org = Organization.objects.create(name="Camp", slug="camp")
    Program.all_objects.create(
        organization=org,
        name="Camp Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date="2026-06-01",
        end_date="2026-08-15",
    )
    # 04:05 local time -- new camp day has started.
    now = datetime(2026, 7, 15, 4, 5, tzinfo=ZoneInfo("America/New_York"))
    assert time_utils.get_today(org, now=now).isoformat() == "2026-07-15"


@pytest.mark.django_db
def test_get_today_for_religious_school_uses_midnight_boundary():
    org = Organization.objects.create(name="TBE", slug="tbe")
    Program.all_objects.create(
        organization=org,
        name="TBE RS 2026-27",
        slug="rs-2026-27",
        program_type="religious_school",
        start_date="2026-09-01",
        end_date="2027-05-31",
    )
    # 00:01 local time -- already today (no late-night rollover).
    now = datetime(2026, 10, 5, 0, 1, tzinfo=ZoneInfo("America/New_York"))
    assert time_utils.get_today(org, now=now).isoformat() == "2026-10-05"


@pytest.mark.django_db
def test_get_today_respects_org_timezone_override():
    org = Organization.objects.create(
        name="West Camp",
        slug="west",
        settings={"timezone": "America/Los_Angeles"},
    )
    Program.all_objects.create(
        organization=org,
        name="West Camp Summer 2026",
        slug="west-2026",
        program_type="summer_camp",
        start_date="2026-06-01",
        end_date="2026-08-15",
    )
    # UTC 06:30 = LA 23:30 the prior calendar day; rollover hasn't happened
    # yet so today is the LA-local date (which is still "yesterday" in UTC).
    now = datetime(2026, 7, 15, 6, 30, tzinfo=ZoneInfo("UTC"))
    assert time_utils.get_today(org, now=now).isoformat() == "2026-07-14"


# ---------------------------------------------------------------------------
# get_current_period — cadence-driven bounds (Step 7_14 MA1)
# ---------------------------------------------------------------------------


class TestGetCurrentPeriodWeekly:
    """Weekly cadence: Monday-Sunday default per MA1, overridable per program."""

    def test_weekly_monday_anchor_returns_monday_to_sunday(self):
        # Wednesday 2026-11-04 -> week is 2026-11-02 (Mon) to 2026-11-08 (Sun).
        start, end = time_utils.get_current_period(
            "weekly", org=None, anchor=date(2026, 11, 4),
        )
        assert start == date(2026, 11, 2)
        assert end == date(2026, 11, 8)

    def test_weekly_when_anchor_is_monday(self):
        start, end = time_utils.get_current_period(
            "weekly", org=None, anchor=date(2026, 11, 2),
        )
        assert start == date(2026, 11, 2)
        assert end == date(2026, 11, 8)

    def test_weekly_when_anchor_is_sunday(self):
        start, end = time_utils.get_current_period(
            "weekly", org=None, anchor=date(2026, 11, 8),
        )
        assert start == date(2026, 11, 2)
        assert end == date(2026, 11, 8)

    @pytest.mark.django_db
    def test_weekly_program_override_changes_boundary_day(self):
        org = Organization.objects.create(name="TBE", slug="tbe-weekly")
        program = Program.all_objects.create(
            organization=org,
            name="TBE Religious School 2026-27",
            slug="rs-2026-27",
            program_type="religious_school",
            start_date=date(2026, 9, 6),
            end_date=date(2027, 5, 30),
            settings={"week_boundary_day": 6},  # Sunday-anchored
        )
        # Wednesday 2026-11-04 -> Sun 2026-11-01 to Sat 2026-11-07.
        start, end = time_utils.get_current_period(
            "weekly", org=org, program=program, anchor=date(2026, 11, 4),
        )
        assert start == date(2026, 11, 1)
        assert end == date(2026, 11, 7)


class TestGetCurrentPeriodOtherCadences:
    def test_daily_cadence_returns_single_day(self):
        start, end = time_utils.get_current_period(
            "daily", org=None, anchor=date(2026, 7, 15),
        )
        assert start == end == date(2026, 7, 15)

    def test_on_demand_cadence_returns_single_day(self):
        start, end = time_utils.get_current_period(
            "on_demand", org=None, anchor=date(2026, 7, 15),
        )
        assert start == end == date(2026, 7, 15)

    def test_monthly_cadence_returns_calendar_month(self):
        start, end = time_utils.get_current_period(
            "monthly", org=None, anchor=date(2026, 11, 4),
        )
        assert start == date(2026, 11, 1)
        assert end == date(2026, 11, 30)

    @pytest.mark.django_db
    def test_biweekly_cadence_anchors_on_program_start(self):
        org = Organization.objects.create(name="Camp", slug="camp-biweekly")
        program = Program.all_objects.create(
            organization=org,
            name="Camp Summer 2026",
            slug="summer-2026",
            program_type="summer_camp",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 31),
        )
        # 12 days after start -> still in first fortnight.
        start, end = time_utils.get_current_period(
            "biweekly", org=org, program=program, anchor=date(2026, 6, 13),
        )
        assert start == date(2026, 6, 1)
        assert end == date(2026, 6, 14)
        # Day 14 -> next fortnight begins.
        start, end = time_utils.get_current_period(
            "biweekly", org=org, program=program, anchor=date(2026, 6, 15),
        )
        assert start == date(2026, 6, 15)
        assert end == date(2026, 6, 28)

    def test_unknown_cadence_falls_back_to_single_day(self):
        start, end = time_utils.get_current_period(
            "frobnicate", org=None, anchor=date(2026, 7, 15),
        )
        assert start == end == date(2026, 7, 15)

"""Tests for reflection reminder email tasks."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.core import mail

from bunk_logs.core.models import (
    Membership,
    Organization,
    Person,
    Program,
    Reflection,
    ReflectionTemplate,
)
from bunk_logs.core.tasks import (
    _parse_reminder_schedule,
    _schedule_is_due,
    dispatch_reflection_reminders,
    send_reflection_reminders,
)

MINIMAL_SCHEMA = {
    "fields": [
        {"key": "highlights", "type": "textarea", "label": {"en": "Highlights", "es": "Logros"}}
    ]
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org():
    return Organization.objects.create(name="Crane Lake", slug="crane-lake-reminders")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Crane Lake - Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        is_active=True,
    )


@pytest.fixture
def template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Counselor Daily",
        slug="counselor-daily",
        cadence="daily",
        role="counselor",
        program_type="summer_camp",
        schema=MINIMAL_SCHEMA,
        languages=["en", "es"],
        is_active=True,
    )


@pytest.fixture
def person_en(org):
    return Person.all_objects.create(
        organization=org,
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        preferred_language="en",
    )


@pytest.fixture
def person_es(org):
    return Person.all_objects.create(
        organization=org,
        first_name="Carlos",
        last_name="Garcia",
        email="carlos@example.com",
        preferred_language="es",
    )


@pytest.fixture
def counselor_en(program, person_en):
    return Membership.all_objects.create(
        program=program,
        person=person_en,
        role="counselor",
        is_active=True,
    )


@pytest.fixture
def counselor_es(program, person_es):
    return Membership.all_objects.create(
        program=program,
        person=person_es,
        role="counselor",
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Unit tests: schedule parsing helpers
# ---------------------------------------------------------------------------


class TestParseReminderSchedule:
    def test_daily(self):
        result = _parse_reminder_schedule("daily_18:00")
        assert result == {"cadence": "daily", "day_of_week": None, "hour": 18, "minute": 0}

    def test_weekly(self):
        result = _parse_reminder_schedule("weekly_friday_15:00")
        assert result["cadence"] == "weekly"
        assert result["day_of_week"] == 4  # Friday
        assert result["hour"] == 15

    def test_biweekly(self):
        result = _parse_reminder_schedule("biweekly_monday_09:00")
        assert result["cadence"] == "biweekly"
        assert result["day_of_week"] == 0  # Monday
        assert result["hour"] == 9

    def test_invalid_returns_empty(self):
        assert _parse_reminder_schedule("unknown_12:00") == {}
        assert _parse_reminder_schedule("") == {}


class TestScheduleIsDue:
    def test_daily_fires_at_correct_hour(self):
        today = date(2026, 6, 10)  # Wednesday
        assert _schedule_is_due("daily_18:00", today, 18) is True
        assert _schedule_is_due("daily_18:00", today, 17) is False

    def test_weekly_fires_on_correct_day(self):
        friday = date(2026, 6, 12)  # a Friday
        wednesday = date(2026, 6, 10)
        assert _schedule_is_due("weekly_friday_15:00", friday, 15) is True
        assert _schedule_is_due("weekly_friday_15:00", wednesday, 15) is False

    def test_biweekly_alternates_weeks(self):
        # ISO week 24 of 2026 is even → should NOT fire (odd weeks only)
        monday_w24 = date(2026, 6, 8)
        assert monday_w24.isocalendar()[1] == 24
        assert _schedule_is_due("biweekly_monday_09:00", monday_w24, 9) is False

        # ISO week 25 is odd → should fire
        monday_w25 = date(2026, 6, 15)
        assert monday_w25.isocalendar()[1] == 25
        assert _schedule_is_due("biweekly_monday_09:00", monday_w25, 9) is True


# ---------------------------------------------------------------------------
# Integration tests: send_reflection_reminders task
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendReflectionReminders:
    def test_sends_to_missing_members(self, counselor_en, counselor_es, program, template):
        result = send_reflection_reminders(program.pk)

        assert result["sent"] == 2
        assert result["skipped"] == 0
        assert len(mail.outbox) == 2

    def test_does_not_remind_those_who_submitted(self, counselor_en, counselor_es, program, template, person_en):
        today = date.today()
        Reflection.all_objects.create(
            organization=program.organization,
            program=program,
            person=person_en,
            template=template,
            period_start=today,
            period_end=today,
            answers={"highlights": "Great day"},
            language="en",
            is_complete=True,
        )

        result = send_reflection_reminders(program.pk)

        assert result["sent"] == 1  # only Carlos
        assert len(mail.outbox) == 1
        assert "carlos@example.com" in mail.outbox[0].to

    def test_email_in_correct_language_english(self, counselor_en, program, template):
        send_reflection_reminders(program.pk)

        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert "Reminder:" in msg.subject
        assert "alice@example.com" in msg.to

    def test_email_in_correct_language_spanish(self, counselor_es, program, template):
        send_reflection_reminders(program.pk)

        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert "Recordatorio:" in msg.subject
        assert "carlos@example.com" in msg.to

    def test_html_alternative_included(self, counselor_en, program, template):
        send_reflection_reminders(program.pk)

        msg = mail.outbox[0]
        alternatives = getattr(msg, "alternatives", [])
        html_bodies = [body for body, mime in alternatives if mime == "text/html"]
        assert html_bodies, "Expected an HTML alternative"
        assert "Submit Reflection" in html_bodies[0]

    def test_spanish_html_content(self, counselor_es, program, template):
        send_reflection_reminders(program.pk)

        msg = mail.outbox[0]
        alternatives = getattr(msg, "alternatives", [])
        html_bodies = [body for body, mime in alternatives if mime == "text/html"]
        assert html_bodies
        assert "Enviar Reflexión" in html_bodies[0]

    def test_skips_person_without_email(self, program, template, org):
        person_no_email = Person.all_objects.create(
            organization=org,
            first_name="No",
            last_name="Email",
            email="",
        )
        Membership.all_objects.create(
            program=program, person=person_no_email, role="counselor", is_active=True
        )

        result = send_reflection_reminders(program.pk)
        assert result["skipped"] >= 1

    def test_role_filter_limits_recipients(self, counselor_en, program, template, org):
        kitchen_person = Person.all_objects.create(
            organization=org,
            first_name="Bob",
            last_name="Cook",
            email="bob@example.com",
        )
        Membership.all_objects.create(
            program=program, person=kitchen_person, role="kitchen_staff", is_active=True
        )

        result = send_reflection_reminders(program.pk, role="counselor")

        # Only counselors should be reminded; template targets counselors too
        assert result["sent"] == 1
        assert mail.outbox[0].to == ["alice@example.com"]

    def test_returns_error_for_missing_program(self):
        result = send_reflection_reminders(999999)
        assert "error" in result

    def test_inactive_memberships_are_excluded(self, program, template, org):
        inactive_person = Person.all_objects.create(
            organization=org,
            first_name="Inactive",
            last_name="Staff",
            email="inactive@example.com",
        )
        Membership.all_objects.create(
            program=program, person=inactive_person, role="counselor", is_active=False
        )

        result = send_reflection_reminders(program.pk)
        assert result["sent"] == 0


# ---------------------------------------------------------------------------
# Integration tests: dispatch_reflection_reminders
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDispatchReflectionReminders:
    def test_dispatches_when_schedule_matches(self, program):
        from datetime import datetime, timezone as dt_tz

        program.settings = {"reminder_schedules": {"counselor": "daily_18:00"}}
        program.save()

        fake_now = datetime(2026, 6, 8, 18, 0, 0, tzinfo=dt_tz.utc)
        with patch("bunk_logs.core.tasks.timezone") as mock_tz:
            mock_tz.now.return_value = fake_now
            mock_tz.localtime.return_value = fake_now
            with patch("bunk_logs.core.tasks.send_reflection_reminders") as mock_task:
                mock_task.delay = mock_task
                result = dispatch_reflection_reminders()

        assert any(d["role"] == "counselor" for d in result["dispatched"])

    def test_does_not_dispatch_when_schedule_does_not_match(self, program):
        from datetime import datetime, timezone as dt_tz

        program.settings = {"reminder_schedules": {"counselor": "daily_18:00"}}
        program.save()

        fake_now = datetime(2026, 6, 8, 10, 0, 0, tzinfo=dt_tz.utc)
        with patch("bunk_logs.core.tasks.timezone") as mock_tz:
            mock_tz.now.return_value = fake_now
            mock_tz.localtime.return_value = fake_now
            result = dispatch_reflection_reminders()

        assert result["dispatched"] == []

    def test_skips_programs_without_schedules(self, program):
        program.settings = {}
        program.save()

        with patch("bunk_logs.core.tasks.send_reflection_reminders") as mock_task:
            result = dispatch_reflection_reminders()

        assert result["dispatched"] == []

"""Idempotency tests for the setup_tbe org/program provisioning command."""

from __future__ import annotations

from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program

pytestmark = pytest.mark.django_db


def _tbe_org() -> Organization:
    return Organization.objects.get(slug="tbe")


def _tbe_program() -> Program:
    return Program.all_objects.get(organization__slug="tbe", slug="religious-school-2026-27")


def test_setup_tbe_creates_org_and_program():
    call_command("setup_tbe")
    org = Organization.objects.get(slug="tbe")
    assert org.name == "Temple Beth-El"
    assert org.settings["timezone"] == "America/New_York"
    assert org.settings["branding"]["display_name"] == "Temple Beth-El"
    program = Program.all_objects.get(organization=org, slug="religious-school-2026-27")
    assert program.program_type == "religious_school"
    assert program.settings["reminder_schedules"] == {"madrich": "weekly_wednesday_18:00"}
    session_dates = program.settings["session_dates"]
    assert all(date.fromisoformat(d).weekday() == 6 for d in session_dates)
    assert "2026-09-20" not in session_dates  # excluded (Sukkot week)


def test_setup_tbe_is_idempotent():
    call_command("setup_tbe")
    call_command("setup_tbe")
    assert Organization.objects.filter(slug="tbe").count() == 1
    assert Program.all_objects.filter(organization__slug="tbe").count() == 1


def test_setup_tbe_backfills_reminder_schedule_on_existing_program():
    """Programs created before Step 4_5 shipped should pick up the schedule on re-run."""
    call_command("setup_tbe")
    program = _tbe_program()
    program.settings = {}
    program.save(update_fields=["settings"])

    call_command("setup_tbe")

    program.refresh_from_db()
    assert program.settings["reminder_schedules"] == {"madrich": "weekly_wednesday_18:00"}


def test_setup_tbe_backfills_terminology_on_an_org_that_predates_it():
    """The production case: an org seeded before terminology existed."""
    call_command("setup_tbe")
    org = _tbe_org()
    del org.settings["terminology"]
    org.save(update_fields=["settings"])

    call_command("setup_tbe")

    org.refresh_from_db()
    assert org.settings["terminology"]["bunk"] == {"one": "class", "other": "classes"}
    assert org.settings["terminology"]["counselor"] == {"one": "faculty", "other": "faculty"}


class TestPreservesAdminEdits:
    """A re-run must never overwrite a value someone set in Django admin."""

    def test_keeps_a_customized_org_name_and_display_name(self):
        call_command("setup_tbe")
        org = _tbe_org()
        org.name = "The Gutterman Religious School at Temple Beth-El"
        org.settings["branding"]["display_name"] = org.name
        org.save(update_fields=["name", "settings"])

        call_command("setup_tbe")

        org.refresh_from_db()
        assert org.name == "The Gutterman Religious School at Temple Beth-El"
        assert org.settings["branding"]["display_name"] == org.name

    def test_keeps_a_customized_term_while_adding_missing_ones(self):
        call_command("setup_tbe")
        org = _tbe_org()
        org.settings["terminology"] = {"camper": {"one": "chanich", "other": "chanichim"}}
        org.save(update_fields=["settings"])

        call_command("setup_tbe")

        org.refresh_from_db()
        terminology = org.settings["terminology"]
        assert terminology["camper"] == {"one": "chanich", "other": "chanichim"}
        assert terminology["bunk"] == {"one": "class", "other": "classes"}

    def test_keeps_a_curated_session_calendar(self):
        call_command("setup_tbe")
        program = _tbe_program()
        program.settings["session_dates"] = ["2026-09-13", "2026-09-27"]
        program.save(update_fields=["settings"])

        call_command("setup_tbe")

        program.refresh_from_db()
        assert program.settings["session_dates"] == ["2026-09-13", "2026-09-27"]

    def test_keeps_a_customized_program_name(self):
        # Still org-prefixed, since `Program.clean` requires that.
        call_command("setup_tbe")
        program = _tbe_program()
        program.name = "Temple Beth-El Sunday School 2026-27"
        program.save(update_fields=["name"])

        call_command("setup_tbe")

        program.refresh_from_db()
        assert program.name == "Temple Beth-El Sunday School 2026-27"


class TestDryRun:
    def test_reports_pending_creation_without_writing(self):
        out = StringIO()
        call_command("setup_tbe", "--dry-run", stdout=out)

        assert "Would create organization" in out.getvalue()
        assert not Organization.objects.filter(slug="tbe").exists()

    def test_reports_pending_backfill_without_writing(self):
        call_command("setup_tbe")
        org = _tbe_org()
        del org.settings["terminology"]
        org.save(update_fields=["settings"])

        out = StringIO()
        call_command("setup_tbe", "--dry-run", stdout=out)

        assert "terminology" in out.getvalue()
        org.refresh_from_db()
        assert "terminology" not in org.settings

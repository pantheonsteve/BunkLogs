"""Idempotency tests for the setup_tbe org/program provisioning command."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program

pytestmark = pytest.mark.django_db


def test_setup_tbe_creates_org_and_program():
    call_command("setup_tbe")
    org = Organization.objects.get(slug="tbe")
    assert org.name == "Temple Beth-El"
    assert org.settings["timezone"] == "America/New_York"
    assert org.settings["branding"]["display_name"] == "Temple Beth-El"
    program = Program.all_objects.get(organization=org, slug="religious-school-2026-27")
    assert program.program_type == "religious_school"


def test_setup_tbe_is_idempotent():
    call_command("setup_tbe")
    call_command("setup_tbe")
    assert Organization.objects.filter(slug="tbe").count() == 1
    assert Program.all_objects.filter(organization__slug="tbe").count() == 1

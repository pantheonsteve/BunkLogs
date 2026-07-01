"""Tests for the ``deactivate_ended_memberships`` management command."""
from __future__ import annotations

from datetime import date

import pytest
from django.core.management import call_command

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Cmd Camp", slug="cmd-camp")


def _program(org, slug, start, end):
    return Program.all_objects.create(
        organization=org,
        name=f"Cmd Camp {slug}",
        slug=slug,
        program_type="summer_camp",
        start_date=start,
        end_date=end,
    )


def _membership(program, org, *, is_active=True, end_date=None):
    person = Person.all_objects.create(organization=org, first_name="A", last_name="B")
    return Membership.all_objects.create(
        program=program, person=person, role="counselor",
        is_active=is_active, end_date=end_date,
    )


@pytest.mark.django_db
def test_deactivates_only_ended_program_memberships(org):
    ended = _program(org, "ended", date(2025, 6, 1), date(2025, 8, 1))
    running = _program(org, "running", date(2026, 6, 1), date(2026, 12, 31))
    m_ended = _membership(ended, org)
    m_running = _membership(running, org)

    call_command("deactivate_ended_memberships", "--apply", "--as-of", "2026-07-01")

    m_ended.refresh_from_db()
    m_running.refresh_from_db()
    assert m_ended.is_active is False
    assert m_ended.end_date == ended.end_date  # backfilled from program
    assert m_running.is_active is True


@pytest.mark.django_db
def test_dry_run_writes_nothing(org):
    ended = _program(org, "ended", date(2025, 6, 1), date(2025, 8, 1))
    m = _membership(ended, org)

    call_command("deactivate_ended_memberships", "--as-of", "2026-07-01")

    m.refresh_from_db()
    assert m.is_active is True


@pytest.mark.django_db
def test_preserves_existing_end_date(org):
    ended = _program(org, "ended", date(2025, 6, 1), date(2025, 8, 1))
    m = _membership(ended, org, end_date=date(2025, 7, 15))

    call_command("deactivate_ended_memberships", "--apply", "--as-of", "2026-07-01")

    m.refresh_from_db()
    assert m.is_active is False
    assert m.end_date == date(2025, 7, 15)  # not overwritten


@pytest.mark.django_db
def test_admin_membership_is_exempt(org):
    """Admin is an org-wide role: its membership survives an ended program."""
    ended = _program(org, "ended", date(2025, 6, 1), date(2025, 8, 1))
    person = Person.all_objects.create(organization=org, first_name="Ad", last_name="Min")
    admin = Membership.all_objects.create(
        program=ended, person=person, role="admin", is_active=True,
    )
    assert admin.capability == "admin"

    call_command("deactivate_ended_memberships", "--apply", "--as-of", "2026-07-01")

    admin.refresh_from_db()
    assert admin.is_active is True
    assert admin.end_date is None

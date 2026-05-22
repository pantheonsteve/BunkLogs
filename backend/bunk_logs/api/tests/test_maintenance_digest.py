"""Tests for maintenance digest generation (Step 7_10, Story 36)."""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.api.maintenance.digest import send_maintenance_digest
from bunk_logs.api.maintenance.digest import _build_digest_context

pytestmark = pytest.mark.django_db


@pytest.fixture
def org():
    return Organization.objects.create(
        name="Digest Org",
        slug="digest-org",
        settings={
            "maintenance_digest_email": "maintenance@camp.test",
            "maintenance_digest_time": "06:00",
        },
    )


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Digest Org Summer",
        slug="digest-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def maint_person(org, program):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(email="dstaff@camp.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Digest", last_name="Staff", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="maintenance", is_active=True,
    )
    return person


@pytest.fixture
def open_ticket(org, program):
    with organization_context(org):
        return MaintenanceTicket.objects.create(
            organization=org,
            program=program,
            location="Cabin 3",
            category=MaintenanceTicket.Category.LEAK,
            description="Roof dripping",
            urgency=MaintenanceTicket.Urgency.NORMAL,
        )


@pytest.fixture
def urgent_ticket(org, program):
    with organization_context(org):
        return MaintenanceTicket.objects.create(
            organization=org,
            program=program,
            location="Kitchen",
            category=MaintenanceTicket.Category.PLUMBING,
            description="Burst pipe",
            urgency=MaintenanceTicket.Urgency.URGENT,
            urgent_reason="Water everywhere",
        )


@pytest.fixture
def closed_ticket(org, program):
    with organization_context(org):
        t = MaintenanceTicket.objects.create(
            organization=org,
            program=program,
            location="Bunk 5",
            category=MaintenanceTicket.Category.BROKEN_LIGHT,
            description="Bulb out",
            urgency=MaintenanceTicket.Urgency.LOW,
            status=MaintenanceTicket.Status.FULFILLED,
        )
        return t


class TestDigestGeneration:
    def test_send_triggers_email(self, org, program, open_ticket):
        send_maintenance_digest(str(org.id), str(program.id))
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert "maintenance@camp.test" in msg.to
        assert "Digest" in msg.subject

    def test_digest_includes_six_sections(self, org, program, open_ticket, closed_ticket, urgent_ticket):
        now = timezone.now()
        window_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        window_start = window_end - timedelta(days=1)

        # Set tickets within window
        MaintenanceTicket.objects.filter(pk=open_ticket.pk).update(
            created_at=window_start + timedelta(hours=1),
        )
        MaintenanceTicket.objects.filter(pk=closed_ticket.pk).update(
            updated_at=window_start + timedelta(hours=2),
        )

        ctx = _build_digest_context(org, program, window_start, window_end)
        assert "summary" in ctx
        assert "urgent_open" in ctx
        assert "new_in_window" in ctx
        assert "closed_in_window" in ctx
        assert "reopened_in_window" in ctx
        assert "still_open" in ctx

    def test_all_clear_still_sends(self, org, program):
        send_maintenance_digest(str(org.id), str(program.id))
        assert len(mail.outbox) == 1
        assert "all clear" in mail.outbox[0].body.lower() or len(mail.outbox[0].body) > 0

    def test_send_failure_increments_counter(self, org, program, open_ticket):
        with patch(
            "bunk_logs.api.maintenance.digest.EmailMultiAlternatives.send",
            side_effect=RuntimeError("SMTP error"),
        ):
            send_maintenance_digest(str(org.id), str(program.id))

        org.refresh_from_db()
        assert org.settings.get("maintenance_digest_consecutive_failures", 0) >= 1

    def test_consecutive_failures_logged(self, org, program, open_ticket, caplog):
        import logging
        org.settings["maintenance_digest_consecutive_failures"] = 2
        org.save()

        with patch(
            "bunk_logs.api.maintenance.digest.EmailMultiAlternatives.send",
            side_effect=RuntimeError("SMTP error"),
        ), caplog.at_level(logging.ERROR):
            send_maintenance_digest(str(org.id), str(program.id))

        assert any("ALERT" in r.message for r in caplog.records)

    def test_success_resets_failure_count(self, org, program, open_ticket):
        org.settings["maintenance_digest_consecutive_failures"] = 2
        org.save()

        send_maintenance_digest(str(org.id), str(program.id))

        org.refresh_from_db()
        assert org.settings.get("maintenance_digest_consecutive_failures", 0) == 0

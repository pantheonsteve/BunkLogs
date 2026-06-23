"""Tests for instant maintenance ticket email alerts."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from bunk_logs.api.maintenance.notifications import send_ticket_created_email
from bunk_logs.api.maintenance.notifications import ticket_reply_to_address
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import TicketPhoto

pytestmark = pytest.mark.django_db

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff"
    b"?\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def org():
    return Organization.objects.create(
        name="Alert Org",
        slug="alert-org",
        settings={
            "maintenance_notification_recipients": [
                {"email": "facilities@camp.test", "instant": True, "digest": False},
                {"email": "manager@camp.test", "instant": False, "digest": True},
            ],
        },
    )


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Alert Org Summer",
        slug="alert-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def ticket(org, program):
    User = get_user_model()
    user = User.objects.create_user(email="c@camp.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Casey", last_name="C", user=user,
    )
    membership = Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    with organization_context(org):
        t = MaintenanceTicket.objects.create(
            organization=org,
            program=program,
            submitted_by=membership,
            location="Bunk 4",
            category=MaintenanceTicket.Category.PLUMBING,
            description="No hot water",
            urgency=MaintenanceTicket.Urgency.URGENT,
            urgent_reason="Campers cannot shower",
        )
        TicketPhoto.objects.create(
            ticket=t,
            image=SimpleUploadedFile("p.png", PNG_BYTES, content_type="image/png"),
            uploaded_by=membership,
            is_followup=False,
        )
        return t


@override_settings(
    FRONTEND_BASE_URL="https://app.test",
    MAILGUN_INBOUND_DOMAIN="reply.test",
    DEFAULT_FROM_EMAIL="noreply@test",
)
def test_sends_to_instant_recipients_only(ticket):
    send_ticket_created_email(str(ticket.id))
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["facilities@camp.test"]
    assert "Bunk 4" in mail.outbox[0].subject
    assert "ticket+" in (mail.outbox[0].extra_headers.get("Reply-To") or "")


@override_settings(
    FRONTEND_BASE_URL="https://app.test",
    MAILGUN_INBOUND_DOMAIN="reply.test",
    DEFAULT_FROM_EMAIL="noreply@test",
)
def test_includes_deep_link_and_description(ticket):
    send_ticket_created_email(str(ticket.id))
    body = mail.outbox[0].body
    assert "No hot water" in body
    assert f"https://app.test/maintenance/tickets/{ticket.id}/" in body


def test_no_recipients_no_send(org, program):
    org.settings = {
        "maintenance_notification_recipients": [
            {"email": "x@camp.test", "instant": False, "digest": True},
        ],
    }
    org.save()
    with organization_context(org):
        t = MaintenanceTicket.objects.create(
            organization=org,
            program=program,
            location="A",
            category="other",
            description="x",
            urgency="normal",
        )
    send_ticket_created_email(str(t.id))
    assert len(mail.outbox) == 0


@override_settings(MAILGUN_INBOUND_DOMAIN="reply.test")
def test_reply_to_address(ticket):
    addr = ticket_reply_to_address(ticket.id)
    assert addr == f"ticket+{ticket.id}@reply.test"


def test_create_dispatches_celery_task(org, program):
    from rest_framework.test import APIClient

    User = get_user_model()
    user = User.objects.create_user(email="new@camp.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="N", last_name="U", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)

    with patch(
        "bunk_logs.api.counselor.maintenance_tickets.send_ticket_created_email.delay",
    ) as mock_delay:
        with organization_context(org):
            resp = client.post(
                "/api/v1/counselor/maintenance-tickets/",
                {
                    "location": "Pool",
                    "category": "other",
                    "description": "Gate broken",
                    "urgency": "normal",
                    "client_submission_id": str(uuid.uuid4()),
                },
                format="json",
            )
    assert resp.status_code == 201
    mock_delay.assert_called_once()


def test_idempotent_replay_skips_email(org, program):
    from rest_framework.test import APIClient

    User = get_user_model()
    user = User.objects.create_user(email="idem@camp.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="I", last_name="D", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    sub_id = str(uuid.uuid4())
    payload = {
        "location": "Dock",
        "category": "other",
        "description": "Loose board",
        "urgency": "normal",
        "client_submission_id": sub_id,
    }
    with patch(
        "bunk_logs.api.counselor.maintenance_tickets.send_ticket_created_email.delay",
    ) as mock_delay:
        with organization_context(org):
            r1 = client.post("/api/v1/counselor/maintenance-tickets/", payload, format="json")
            r2 = client.post("/api/v1/counselor/maintenance-tickets/", payload, format="json")
    assert r1.status_code == 201
    assert r2.status_code == 200
    mock_delay.assert_called_once()

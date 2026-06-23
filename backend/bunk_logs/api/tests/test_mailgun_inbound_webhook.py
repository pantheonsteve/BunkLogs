"""Tests for Mailgun inbound webhook (email replies → ticket notes)."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import date

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

pytestmark = pytest.mark.django_db

API_KEY = "test-mailgun-key"
URL = "/api/v1/webhooks/mailgun/inbound/"


def _sign(timestamp: str, token: str) -> str:
    return hmac.new(
        API_KEY.encode(),
        f"{timestamp}{token}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _post_payload(client, *, recipient: str, body: str, sender: str, **extra):
    timestamp = "1700000000"
    token = "abc123"
    data = {
        "timestamp": timestamp,
        "token": token,
        "signature": _sign(timestamp, token),
        "recipient": recipient,
        "from": sender,
        "stripped-text": body,
        **extra,
    }
    return client.post(URL, data)


@pytest.fixture
def org():
    return Organization.objects.create(
        name="Inbound Org",
        slug="inbound-org",
        settings={
            "maintenance_notification_recipients": [
                {"email": "facilities@camp.test", "instant": True, "digest": False},
            ],
        },
    )


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Inbound Org Summer",
        slug="inbound-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def open_ticket(org, program):
    with organization_context(org):
        return MaintenanceTicket.objects.create(
            organization=org,
            program=program,
            location="Arts",
            category=MaintenanceTicket.Category.OTHER,
            description="Broken shelf",
            urgency=MaintenanceTicket.Urgency.NORMAL,
            status=MaintenanceTicket.Status.NEW,
        )


@pytest.fixture
def api_client():
    return APIClient()


@override_settings(ANYMAIL={"MAILGUN_API_KEY": API_KEY})
def test_valid_reply_creates_note(api_client, open_ticket):
    recipient = f"ticket+{open_ticket.id}@reply.mail.test"
    resp = _post_payload(
        api_client,
        recipient=recipient,
        body="On my way with a ladder.",
        sender="facilities@camp.test",
    )
    assert resp.status_code == 200
    notes = OrderActivityEvent.all_objects.filter(
        content_type="maintenance_ticket",
        content_id=open_ticket.id,
        event_type=OrderActivityEvent.EventType.NOTE,
    )
    assert notes.count() == 1
    note = notes.first()
    assert note.note == "On my way with a ladder."
    assert note.metadata.get("source") == "email"
    assert note.metadata.get("visibility") == "team_only"


@override_settings(ANYMAIL={"MAILGUN_API_KEY": API_KEY})
def test_invalid_signature_rejected(api_client, open_ticket):
    resp = api_client.post(URL, {
        "timestamp": "1",
        "token": "t",
        "signature": "bad",
        "recipient": f"ticket+{open_ticket.id}@reply.mail.test",
        "from": "facilities@camp.test",
        "stripped-text": "nope",
    })
    assert resp.status_code == 403


@override_settings(ANYMAIL={"MAILGUN_API_KEY": API_KEY})
def test_unknown_ticket_404(api_client):
    fake = uuid.uuid4()
    resp = _post_payload(
        api_client,
        recipient=f"ticket+{fake}@reply.mail.test",
        body="hello",
        sender="facilities@camp.test",
    )
    assert resp.status_code == 404


@override_settings(ANYMAIL={"MAILGUN_API_KEY": API_KEY})
def test_unauthorized_sender_still_creates_note(api_client, open_ticket):
    resp = _post_payload(
        api_client,
        recipient=f"ticket+{open_ticket.id}@reply.mail.test",
        body="contractor update",
        sender="stranger@evil.test",
    )
    assert resp.status_code == 200
    note = OrderActivityEvent.all_objects.filter(content_id=open_ticket.id).first()
    assert note is not None
    assert note.note == "contractor update"
    assert note.metadata.get("sender_email") == "stranger@evil.test"


@override_settings(ANYMAIL={"MAILGUN_API_KEY": API_KEY})
def test_angle_bracket_recipient_parsed(api_client, open_ticket):
    recipient = f'"BunkLogs Ticket" <ticket+{open_ticket.id}@reply.mail.test>'
    resp = _post_payload(
        api_client,
        recipient=recipient,
        body="Bracket recipient works.",
        sender="facilities@camp.test",
    )
    assert resp.status_code == 200
    assert OrderActivityEvent.all_objects.filter(content_id=open_ticket.id).exists()


@override_settings(ANYMAIL={"MAILGUN_API_KEY": API_KEY})
def test_message_headers_recipient_parsed(api_client, open_ticket):
    headers = json.dumps([
        ["To", f"ticket+{open_ticket.id}@reply.mail.test"],
        ["From", "facilities@camp.test"],
    ])
    resp = _post_payload(
        api_client,
        recipient="facilities@camp.test",
        body="Header recipient works.",
        sender="facilities@camp.test",
        **{"message-headers": headers},
    )
    assert resp.status_code == 200
    assert OrderActivityEvent.all_objects.filter(content_id=open_ticket.id).exists()


@override_settings(ANYMAIL={"MAILGUN_API_KEY": API_KEY})
def test_stripped_html_body_parsed(api_client, open_ticket):
    resp = _post_payload(
        api_client,
        recipient=f"ticket+{open_ticket.id}@reply.mail.test",
        body="",
        sender="facilities@camp.test",
        **{"stripped-html": "<p>HTML reply body</p>"},
    )
    assert resp.status_code == 200
    note = OrderActivityEvent.all_objects.filter(content_id=open_ticket.id).first()
    assert note.note == "HTML reply body"


@override_settings(ANYMAIL={"MAILGUN_API_KEY": API_KEY})
def test_maintenance_member_sender_allowed(api_client, org, program, open_ticket):
    person = Person.all_objects.create(
        organization=org,
        first_name="M",
        last_name="T",
        email="maint@camp.test",
    )
    Membership.all_objects.create(
        program=program,
        person=person,
        role="maintenance",
        is_active=True,
    )
    resp = _post_payload(
        api_client,
        recipient=f"ticket+{open_ticket.id}@reply.mail.test",
        body="Checking it now.",
        sender="maint@camp.test",
    )
    assert resp.status_code == 200
    assert OrderActivityEvent.all_objects.filter(content_id=open_ticket.id).exists()


@override_settings(ANYMAIL={"MAILGUN_API_KEY": API_KEY})
def test_closed_ticket_rejected(api_client, org, program):
    with organization_context(org):
        closed = MaintenanceTicket.objects.create(
            organization=org,
            program=program,
            location="X",
            category="other",
            description="done",
            urgency="normal",
            status=MaintenanceTicket.Status.FULFILLED,
        )
    resp = _post_payload(
        api_client,
        recipient=f"ticket+{closed.id}@reply.mail.test",
        body="reopen?",
        sender="facilities@camp.test",
    )
    assert resp.status_code == 400

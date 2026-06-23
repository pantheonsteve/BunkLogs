"""Mailgun inbound webhook — email replies become maintenance ticket notes."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import uuid
from email.utils import getaddresses
from email.utils import parseaddr

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from email_reply_parser import EmailReplyParser
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.maintenance.settings import is_configured_recipient
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import Person

logger = logging.getLogger(__name__)

STATUS_CLOSED = (
    MaintenanceTicket.Status.FULFILLED,
    MaintenanceTicket.Status.UNABLE_TO_FULFILL,
)
TICKET_UUID_RE = re.compile(
    r"ticket\+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)
HTML_TAG_RE = re.compile(r"<[^>]+>")


def verify_mailgun_signature(timestamp: str, token: str, signature: str) -> bool:
    api_key = ""
    anymail = getattr(settings, "ANYMAIL", None)
    if isinstance(anymail, dict):
        api_key = anymail.get("MAILGUN_API_KEY", "")
    if not api_key:
        api_key = getattr(settings, "MAILGUN_API_KEY", "")
    if not api_key or not timestamp or not token or not signature:
        return False
    digest = hmac.new(
        key=api_key.encode(),
        msg=f"{timestamp}{token}".encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


def parse_ticket_id_from_recipient(recipient: str) -> uuid.UUID | None:
    """Extract ticket UUID from a single address or header value."""
    _, addr = parseaddr((recipient or "").strip())
    candidate = (addr or recipient or "").strip().lower()
    match = TICKET_UUID_RE.search(candidate)
    if not match:
        return None
    try:
        return uuid.UUID(match.group(1))
    except ValueError:
        return None


def _iter_inbound_addresses(post_data: dict) -> list[str]:
    """Collect candidate recipient addresses from Mailgun inbound fields."""
    addresses: list[str] = []
    for key in ("recipient", "To", "to"):
        raw = _field_value(post_data, key)
        if raw:
            addresses.extend(addr for _, addr in getaddresses([raw]) if addr)
            addresses.append(raw)
    headers_raw = _field_value(post_data, "message-headers")
    if headers_raw:
        try:
            headers = json.loads(headers_raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            headers = []
        for item in headers:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                continue
            name, value = item
            if str(name).lower() in {
                "to", "recipient", "delivered-to", "x-original-to", "x-envelope-to",
            }:
                addresses.extend(addr for _, addr in getaddresses([str(value)]) if addr)
                addresses.append(str(value))
    return addresses


def extract_ticket_id_from_inbound(post_data: dict) -> uuid.UUID | None:
    """Resolve ticket id from any Mailgun recipient/header field."""
    for address in _iter_inbound_addresses(post_data):
        ticket_id = parse_ticket_id_from_recipient(address)
        if ticket_id is not None:
            return ticket_id
    return None


def extract_sender_email(raw_from: str) -> str:
    _, addr = parseaddr(raw_from or "")
    return addr.strip().lower()


def _field_value(data: dict, key: str) -> str:
    raw = data.get(key, "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    return str(raw).strip()


def _strip_html(value: str) -> str:
    text = HTML_TAG_RE.sub(" ", value or "")
    return re.sub(r"\s+", " ", text).strip()


def parse_reply_body(post_data: dict) -> str:
    for key in ("stripped-text", "body-plain", "stripped-html", "body-html"):
        raw = _field_value(post_data, key)
        if not raw:
            continue
        if key.endswith("html"):
            raw = _strip_html(raw)
        parsed = EmailReplyParser.parse_reply(raw).strip()
        if parsed:
            return parsed
    return ""


def authorize_sender(
    org,
    sender_email: str,
    *,
    ticket: MaintenanceTicket | None = None,
) -> Membership | None:
    if is_configured_recipient(org, sender_email):
        person = Person.all_objects.filter(
            organization=org, email__iexact=sender_email,
        ).first()
        if person:
            return (
                Membership.all_objects.filter(
                    person=person,
                    program__organization=org,
                    is_active=True,
                )
                .order_by("-created_at")
                .first()
            )
        return None

    person = Person.all_objects.filter(
        organization=org, email__iexact=sender_email,
    ).first()
    if person is None:
        return None
    membership = (
        Membership.all_objects.filter(
            person=person,
            program__organization=org,
            role__in=("maintenance", "admin"),
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )
    if membership is not None:
        return membership

    if ticket and ticket.submitted_by_id:
        submitter = ticket.submitted_by
        submitter_person = getattr(submitter, "person", None) if submitter else None
        if (
            submitter_person
            and submitter_person.email
            and submitter_person.email.strip().lower() == sender_email
        ):
            return submitter
    return None


@method_decorator(csrf_exempt, name="dispatch")
class MailgunInboundWebhookView(APIView):
    """``POST /api/v1/webhooks/mailgun/inbound/`` — inbound email replies."""

    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request, *args, **kwargs):
        data = request.POST
        timestamp = _field_value(dict(data), "timestamp")
        token = _field_value(dict(data), "token")
        signature = _field_value(dict(data), "signature")

        if not verify_mailgun_signature(timestamp, token, signature):
            logger.warning("mailgun inbound: invalid signature")
            return Response({"detail": "Invalid signature."}, status=status.HTTP_403_FORBIDDEN)

        post_data = dict(data)
        ticket_id = extract_ticket_id_from_inbound(post_data)
        if ticket_id is None:
            recipient = _field_value(post_data, "recipient")
            logger.info(
                "mailgun inbound: unrecognized recipient fields (recipient=%r)",
                recipient,
            )
            return HttpResponse(status=406)

        ticket = (
            MaintenanceTicket.all_objects.filter(pk=ticket_id)
            .select_related("organization", "program", "submitted_by__person")
            .first()
        )
        if ticket is None:
            return Response({"detail": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)

        sender_email = extract_sender_email(
            _field_value(post_data, "from") or _field_value(post_data, "sender"),
        )
        if not sender_email:
            return Response({"detail": "Missing sender."}, status=status.HTTP_400_BAD_REQUEST)

        membership = authorize_sender(ticket.organization, sender_email, ticket=ticket)
        if membership is None and not is_configured_recipient(ticket.organization, sender_email):
            # The ticket+uuid address is only distributed to notification recipients;
            # accept the reply but log when the From address is unexpected.
            logger.info(
                "mailgun inbound: reply from unlisted sender %s on ticket %s",
                sender_email,
                ticket_id,
            )

        if ticket.status in STATUS_CLOSED:
            return Response(
                {"detail": "Cannot add notes to a closed ticket."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        body = parse_reply_body(post_data)
        if not body:
            logger.info(
                "mailgun inbound: empty reply body for ticket %s from %s",
                ticket_id,
                sender_email,
            )
            return Response({"detail": "Empty reply body."}, status=status.HTTP_400_BAD_REQUEST)

        with organization_context(ticket.organization):
            OrderActivityEvent.all_objects.create(
                organization=ticket.organization,
                program=ticket.program,
                actor_membership=membership,
                event_type=OrderActivityEvent.EventType.NOTE,
                content_type="maintenance_ticket",
                content_id=ticket.id,
                note=body,
                metadata={
                    "visibility": "team_only",
                    "source": "email",
                    "sender_email": sender_email,
                },
            )

        logger.info(
            "mailgun inbound: note created on ticket %s from %s", ticket_id, sender_email,
        )
        return HttpResponse(status=200)

"""Mailgun inbound webhook — email replies become maintenance ticket notes."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import uuid
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
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import Person

logger = logging.getLogger(__name__)

STATUS_CLOSED = (
    MaintenanceTicket.Status.FULFILLED,
    MaintenanceTicket.Status.UNABLE_TO_FULFILL,
)


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
    local = recipient.strip().lower().split("@", 1)[0]
    match = re.match(r"^ticket\+([0-9a-f-]{36})$", local, re.IGNORECASE)
    if not match:
        return None
    try:
        return uuid.UUID(match.group(1))
    except ValueError:
        return None


def extract_sender_email(raw_from: str) -> str:
    _, addr = parseaddr(raw_from or "")
    return addr.strip().lower()


def _field_value(data: dict, key: str) -> str:
    raw = data.get(key, "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    return str(raw).strip()


def parse_reply_body(post_data: dict) -> str:
    stripped = _field_value(post_data, "stripped-text")
    if stripped:
        return EmailReplyParser.parse_reply(stripped).strip()
    plain = _field_value(post_data, "body-plain")
    if plain:
        return EmailReplyParser.parse_reply(plain).strip()
    return ""


def authorize_sender(org, sender_email: str) -> Membership | None:
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
    return (
        Membership.all_objects.filter(
            person=person,
            program__organization=org,
            role="maintenance",
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )


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
        recipient = _field_value(post_data, "recipient")
        ticket_id = parse_ticket_id_from_recipient(recipient)
        if ticket_id is None:
            logger.info("mailgun inbound: unrecognized recipient %s", recipient)
            return HttpResponse(status=406)

        ticket = (
            MaintenanceTicket.all_objects.filter(pk=ticket_id)
            .select_related("organization", "program")
            .first()
        )
        if ticket is None:
            return Response({"detail": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)

        sender_email = extract_sender_email(
            _field_value(post_data, "from") or _field_value(post_data, "sender"),
        )
        if not sender_email:
            return Response({"detail": "Missing sender."}, status=status.HTTP_400_BAD_REQUEST)

        membership = authorize_sender(ticket.organization, sender_email)
        if membership is None and not is_configured_recipient(ticket.organization, sender_email):
            logger.warning(
                "mailgun inbound: unauthorized sender %s for ticket %s",
                sender_email,
                ticket_id,
            )
            return Response({"detail": "Sender not authorized."}, status=status.HTTP_403_FORBIDDEN)

        if ticket.status in STATUS_CLOSED:
            return Response(
                {"detail": "Cannot add notes to a closed ticket."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        body = parse_reply_body(post_data)
        if not body:
            return Response({"detail": "Empty reply body."}, status=status.HTTP_400_BAD_REQUEST)

        OrderActivityEvent.objects.create(
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

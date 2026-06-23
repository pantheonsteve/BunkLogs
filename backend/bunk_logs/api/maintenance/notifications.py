"""Instant maintenance ticket email alerts."""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from bunk_logs.api.maintenance.settings import get_instant_recipients
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import TicketPhoto

logger = logging.getLogger(__name__)

MAX_EMBEDDED_PHOTOS = 3


def ticket_reply_to_address(ticket_id) -> str | None:
    domain = getattr(settings, "MAILGUN_INBOUND_DOMAIN", "") or ""
    if not domain:
        return None
    return f"ticket+{ticket_id}@{domain}"


def _absolute_image_url(photo: TicketPhoto) -> str | None:
    if not photo.image:
        return None
    url = photo.image.url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    site_url = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    return urljoin(f"{site_url}/", url.lstrip("/"))


def _build_ticket_created_context(ticket: MaintenanceTicket) -> dict:
    submitter = ticket.submitted_by
    person = getattr(submitter, "person", None) if submitter else None
    submitter_name = (
        f"{person.first_name} {person.last_name}".strip() if person else "Unknown"
    )

    photos = list(
        TicketPhoto.all_objects.filter(ticket=ticket, is_followup=False)
        .order_by("created_at"),
    )
    embedded = [_absolute_image_url(p) for p in photos[:MAX_EMBEDDED_PHOTOS]]
    embedded = [u for u in embedded if u]
    extra_photo_count = max(0, len(photos) - MAX_EMBEDDED_PHOTOS)

    base_url = getattr(settings, "FRONTEND_BASE_URL", "https://clc.bunklogs.net").rstrip("/")
    deep_link = f"{base_url}/maintenance/tickets/{ticket.id}/"

    return {
        "ticket": ticket,
        "submitter_name": submitter_name,
        "category_display": ticket.get_category_display(),
        "urgency_display": ticket.get_urgency_display(),
        "deep_link": deep_link,
        "embedded_photo_urls": embedded,
        "extra_photo_count": extra_photo_count,
        "org_name": ticket.organization.name if ticket.organization_id else "",
    }


@shared_task(name="maintenance.send_ticket_created_email")
def send_ticket_created_email(ticket_id: str) -> None:
    """Send instant alert email when a new maintenance ticket is created."""
    try:
        ticket = (
            MaintenanceTicket.all_objects.select_related(
                "organization", "submitted_by__person",
            )
            .prefetch_related("photos")
            .get(pk=ticket_id)
        )
    except MaintenanceTicket.DoesNotExist:
        logger.warning("ticket created email: ticket %s not found", ticket_id)
        return

    recipients = get_instant_recipients(ticket.organization)
    if not recipients:
        return

    ctx = _build_ticket_created_context(ticket)
    urgency_label = ticket.urgency.upper() if ticket.urgency == "urgent" else ticket.urgency
    subject = f"New Maintenance Ticket — {ticket.location} ({urgency_label})"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@bunklogs.net")

    text_body = render_to_string("maintenance/ticket_created.txt", ctx)
    html_body = render_to_string("maintenance/ticket_created.html", ctx)

    reply_to = ticket_reply_to_address(ticket.id)
    headers = {}
    if reply_to:
        headers["Reply-To"] = reply_to

    for recipient in recipients:
        try:
            msg = EmailMultiAlternatives(
                subject, text_body, from_email, [recipient], headers=headers,
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()
            logger.info(
                "ticket created email sent to %s for ticket %s", recipient, ticket_id,
            )
        except Exception:
            logger.exception(
                "ticket created email failure — ticket %s recipient %s",
                ticket_id,
                recipient,
            )


def send_maintenance_notifications_test_email(recipient: str) -> dict:
    """Send a one-off test message using the same mail backend as ticket alerts."""
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@bunklogs.net")
    inbound_domain = getattr(settings, "MAILGUN_INBOUND_DOMAIN", "") or ""
    example_ticket_id = "00000000-0000-0000-0000-000000000000"
    reply_to = (
        f"ticket+{example_ticket_id}@{inbound_domain}" if inbound_domain else None
    )

    subject = "BunkLogs maintenance email test"
    text_body = (
        "This is a test email from BunkLogs maintenance notifications.\n\n"
        "If you received this, outbound email (Mailgun) is configured correctly.\n"
    )
    if reply_to:
        text_body += f"\nReply-To example: {reply_to}\n"
    html_body = (
        "<p>This is a test email from <strong>BunkLogs</strong> maintenance notifications.</p>"
        "<p>If you received this, outbound email is configured correctly.</p>"
    )
    if reply_to:
        html_body += f"<p>Reply-To example: <code>{reply_to}</code></p>"

    headers = {"Reply-To": reply_to} if reply_to else {}
    msg = EmailMultiAlternatives(
        subject, text_body, from_email, [recipient], headers=headers,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    return {
        "detail": f"Test email sent to {recipient}.",
        "from_email": from_email,
        "inbound_domain_configured": bool(inbound_domain),
        "reply_to_example": reply_to,
    }

"""Daily maintenance digest email (Step 7_10, Story 36).

Scheduling
----------
A single Celery Beat task ``maintenance.dispatch_daily_digests`` runs at
``05:00`` server time and fans out one ``send_maintenance_digest`` task per
active org/program pair that has a ``maintenance_digest_email`` configured
in ``Organization.settings``.

Per-org send time is honoured by checking whether ``now`` in the org's
timezone is within the configured send window (``maintenance_digest_time``,
default ``"06:00"``).  Because the dispatcher itself runs at 05:00 UTC and
most US camp orgs are UTC-4/UTC-5, default 06:00 local hits the window.

Failure tracking
----------------
Consecutive failures are counted in
``Organization.settings["maintenance_digest_consecutive_failures"]``.
Three consecutive failures emit a ``logger.error`` with enough context for
Datadog to trigger an alert (the project-wide DD agent reads Python loggers
at ERROR level).
"""

from __future__ import annotations

import logging
from datetime import datetime
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program
from bunk_logs.core.time_utils import get_org_timezone

logger = logging.getLogger(__name__)

CONSECUTIVE_FAILURE_ALERT_THRESHOLD = 3
DEFAULT_DIGEST_TIME = "06:00"
SEND_WINDOW_MINUTES = 59  # task runs every hour; accept if within 59 min of target


# ---------------------------------------------------------------------------
# Dispatcher (hourly fan-out)
# ---------------------------------------------------------------------------


@shared_task(name="maintenance.dispatch_daily_digests")
def dispatch_daily_digests() -> None:
    """Fan-out one digest task per eligible org/program pair."""
    for org in Organization.objects.filter(is_active=True):
        digest_email = (org.settings or {}).get("maintenance_digest_email")
        if not digest_email:
            continue

        target_time_str: str = (org.settings or {}).get("maintenance_digest_time", DEFAULT_DIGEST_TIME)
        if not _is_send_window(org, target_time_str):
            continue

        for program in Program.all_objects.filter(
            organization=org, is_active=True,
        ):
            send_maintenance_digest.delay(str(org.id), str(program.id))


def _is_send_window(org: Organization, target_time_str: str) -> bool:
    """Return True when ``now`` in the org's timezone is within the send window."""
    try:
        hour, minute = (int(p) for p in target_time_str.split(":"))
    except (ValueError, AttributeError):
        hour, minute = 6, 0

    tz = get_org_timezone(org)
    now_local = timezone.now().astimezone(tz)
    target = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    diff = abs((now_local - target).total_seconds())
    return diff <= SEND_WINDOW_MINUTES * 60


# ---------------------------------------------------------------------------
# Per-org digest sender
# ---------------------------------------------------------------------------


@shared_task(
    name="maintenance.send_maintenance_digest",
    bind=True,
    max_retries=0,
)
def send_maintenance_digest(self, org_id: str, program_id: str) -> None:
    """Build and send the daily maintenance digest for one org/program pair."""
    try:
        org = Organization.objects.get(pk=org_id)
        program = Program.all_objects.get(pk=program_id, organization=org)
    except (Organization.DoesNotExist, Program.DoesNotExist):
        logger.warning("maintenance digest: org %s / program %s not found", org_id, program_id)
        return

    recipient = (org.settings or {}).get("maintenance_digest_email")
    if not recipient:
        return

    tz = get_org_timezone(org)
    now = timezone.now().astimezone(tz)
    window_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = window_end - timedelta(days=1)

    ctx = _build_digest_context(org, program, window_start, window_end)

    subject = f"Maintenance Digest — {window_end.strftime('%B %-d, %Y')}"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@bunklogs.net")

    text_body = render_to_string("maintenance/digest.txt", ctx)
    html_body = render_to_string("maintenance/digest.html", ctx)

    try:
        msg = EmailMultiAlternatives(subject, text_body, from_email, [recipient])
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        _reset_failure_count(org)
        logger.info("maintenance digest sent to %s for program %s", recipient, program_id)
    except Exception:
        _increment_failure_count(org)
        logger.exception(
            "maintenance digest send failure — org %s program %s recipient %s",
            org_id,
            program_id,
            recipient,
        )


# ---------------------------------------------------------------------------
# Digest content builder
# ---------------------------------------------------------------------------


def _build_digest_context(
    org: Organization,
    program: Program,
    window_start: datetime,
    window_end: datetime,
) -> dict:
    all_qs = MaintenanceTicket.objects.filter(program=program)

    urgent_open = list(
        all_qs.filter(
            status__in=("new", "in_progress"),
            urgency="urgent",
        ).select_related("submitted_by__person").order_by("created_at"),
    )

    new_in_window = list(
        all_qs.filter(
            created_at__gte=window_start,
            created_at__lt=window_end,
        ).select_related("submitted_by__person").order_by("created_at"),
    )

    closed_in_window = list(
        all_qs.filter(
            status__in=("fulfilled", "unable_to_fulfill"),
            updated_at__gte=window_start,
            updated_at__lt=window_end,
        ).select_related("submitted_by__person").order_by("updated_at"),
    )

    reopened_in_window = list(
        OrderActivityEvent.objects.filter(
            content_type="maintenance_ticket",
            from_state__in=("fulfilled", "unable_to_fulfill"),
            to_state="in_progress",
            created_at__gte=window_start,
            created_at__lt=window_end,
        ).select_related("actor_membership__person"),
    )
    reopened_ticket_ids = [str(e.content_id) for e in reopened_in_window]
    reopened_tickets = {
        str(t.id): t
        for t in all_qs.filter(id__in=reopened_ticket_ids).select_related("submitted_by__person")
    }

    still_open = list(
        all_qs.filter(status__in=("new", "in_progress"))
        .select_related("submitted_by__person")
        .order_by("created_at"),
    )

    def _closing_note(ticket):
        ev = (
            OrderActivityEvent.objects.filter(
                content_type="maintenance_ticket",
                content_id=ticket.id,
                to_state__in=("fulfilled", "unable_to_fulfill"),
            )
            .order_by("-created_at")
            .first()
        )
        return (ev.note or "")[:120] if ev else ""

    def _reopen_reason(event):
        ev = (
            OrderActivityEvent.objects.filter(
                content_type="maintenance_ticket",
                content_id=event.content_id,
                from_state__in=("fulfilled", "unable_to_fulfill"),
                to_state="in_progress",
                created_at=event.created_at,
            ).first()
        )
        return (ev.note or "") if ev else ""

    base_url = getattr(settings, "FRONTEND_BASE_URL", "https://clc.bunklogs.net")

    return {
        "org": org,
        "program": program,
        "window_start": window_start,
        "window_end": window_end,
        "base_url": base_url,
        "summary": {
            "new_in_window": len(new_in_window),
            "closed_in_window": len(closed_in_window),
            "still_open": len(still_open),
            "urgent_open": len(urgent_open),
        },
        "urgent_open": [_ticket_brief(t, base_url) for t in urgent_open],
        "new_in_window": [_ticket_brief(t, base_url) for t in new_in_window],
        "closed_in_window": [
            {**_ticket_brief(t, base_url), "closing_note": _closing_note(t)}
            for t in closed_in_window
        ],
        "reopened_in_window": [
            {
                "ticket": _ticket_brief(reopened_tickets[str(e.content_id)], base_url),
                "reopen_reason": (e.note or "")[:120],
            }
            for e in reopened_in_window
            if str(e.content_id) in reopened_tickets
        ],
        "still_open": [_ticket_brief(t, base_url) for t in still_open],
    }


def _ticket_brief(ticket: MaintenanceTicket, base_url: str) -> dict:
    submitter = getattr(ticket, "submitted_by", None)
    person = getattr(submitter, "person", None) if submitter else None
    return {
        "id": str(ticket.id),
        "location": ticket.location,
        "category": ticket.get_category_display(),
        "urgency": ticket.urgency,
        "description": (ticket.description or "")[:100],
        "submitter_name": f"{person.first_name} {person.last_name}".strip() if person else "",
        "status": ticket.status,
        "deep_link": f"{base_url}/maintenance/tickets/{ticket.id}/",
        "age_days": (timezone.now() - ticket.created_at).days if ticket.created_at else None,
    }


# ---------------------------------------------------------------------------
# Failure tracking
# ---------------------------------------------------------------------------


def _reset_failure_count(org: Organization) -> None:
    settings_copy = dict(org.settings or {})
    if settings_copy.get("maintenance_digest_consecutive_failures", 0) != 0:
        settings_copy["maintenance_digest_consecutive_failures"] = 0
        Organization.objects.filter(pk=org.pk).update(settings=settings_copy)


def _increment_failure_count(org: Organization) -> None:
    settings_copy = dict(org.settings or {})
    count = settings_copy.get("maintenance_digest_consecutive_failures", 0) + 1
    settings_copy["maintenance_digest_consecutive_failures"] = count
    Organization.objects.filter(pk=org.pk).update(settings=settings_copy)

    if count >= CONSECUTIVE_FAILURE_ALERT_THRESHOLD:
        logger.error(
            "maintenance digest ALERT: %d consecutive failures for org %s — "
            "manual intervention required",
            count,
            org.slug,
            extra={"org_id": str(org.id), "consecutive_failures": count},
        )

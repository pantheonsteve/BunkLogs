"""Celery tasks for reflection reminder emails."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ("en", "es")

# Maps the schedule string prefix to cadence names used in ReflectionTemplate
SCHEDULE_PREFIX_TO_CADENCE = {
    "daily": "daily",
    "weekly": "weekly",
    "biweekly": "biweekly",
}

DAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _parse_reminder_schedule(schedule_str: str) -> dict:
    """Parse a schedule string like 'daily_18:00' or 'weekly_friday_15:00'.

    Returns a dict with keys: cadence, day_of_week (int or None), hour (int), minute (int).
    Returns None if the string is unparseable.
    """
    parts = schedule_str.lower().split("_")
    if not parts:
        return {}

    cadence = parts[0]
    if cadence not in SCHEDULE_PREFIX_TO_CADENCE:
        return {}

    try:
        if cadence == "daily":
            # daily_HH:MM
            h, m = parts[1].split(":")
            return {"cadence": cadence, "day_of_week": None, "hour": int(h), "minute": int(m)}
        elif cadence in ("weekly", "biweekly"):
            # weekly_DOW_HH:MM or biweekly_DOW_HH:MM
            dow_name = parts[1]
            h, m = parts[2].split(":")
            return {
                "cadence": cadence,
                "day_of_week": DAY_NAMES.get(dow_name),
                "hour": int(h),
                "minute": int(m),
            }
    except (IndexError, ValueError):
        pass
    return {}


def _schedule_is_due(schedule_str: str, now: date, current_hour: int) -> bool:
    """Return True if the given schedule_str fires at the current datetime.

    `now` is the current date; `current_hour` is the current hour (0–23).
    Matching is on day-of-week + hour (minutes are ignored for hourly dispatch).
    """
    parsed = _parse_reminder_schedule(schedule_str)
    if not parsed:
        return False

    cadence = parsed["cadence"]
    scheduled_hour = parsed.get("hour", 0)

    if current_hour != scheduled_hour:
        return False

    if cadence == "daily":
        return True

    scheduled_dow = parsed.get("day_of_week")
    if scheduled_dow is None:
        return False

    if cadence == "weekly":
        return now.weekday() == scheduled_dow

    if cadence == "biweekly":
        # Fire on the scheduled day-of-week every two weeks.
        # Use ISO week number parity as the biweekly signal.
        iso_week = now.isocalendar()[1]
        return now.weekday() == scheduled_dow and iso_week % 2 == 1

    return False


def _get_email_for_person(person) -> str:
    """Return the best email address for a person."""
    if person.email:
        return person.email
    if person.user_id and hasattr(person, "user") and person.user:
        return person.user.email
    return ""


@shared_task(bind=True, name="bunk_logs.core.tasks.send_reflection_reminders")
def send_reflection_reminders(self, program_id: int, role: str | None = None) -> dict:
    """Send reminder emails to staff missing a reflection for the current period.

    Finds all active Memberships in the given program (optionally filtered by role)
    that have not submitted a reflection covering today, then sends each person
    an email in their preferred language.
    """
    from bunk_logs.core.models import Membership, Program, Reflection, ReflectionTemplate

    today = date.today()

    try:
        program = Program.all_objects.select_related("organization").get(pk=program_id)
    except Program.DoesNotExist:
        logger.error("send_reflection_reminders: program %s not found", program_id)
        return {"error": f"Program {program_id} not found"}

    template_qs = ReflectionTemplate.all_objects.filter(
        is_active=True,
        program_type=program.program_type,
    ).filter(
        Q(organization=program.organization) | Q(organization__isnull=True)
    )
    if role:
        template_qs = template_qs.filter(Q(role=role) | Q(role__isnull=True))

    membership_qs = (
        Membership.all_objects.filter(program=program, is_active=True)
        .exclude(role="camper")
        .select_related("person", "person__user")
    )
    if role:
        membership_qs = membership_qs.filter(role=role)

    results: dict = {"sent": 0, "skipped": 0, "errors": 0}

    for template in template_qs:
        target = membership_qs.filter(role=template.role) if template.role else membership_qs

        already_submitted = Reflection.all_objects.filter(
            program=program,
            template=template,
            is_complete=True,
            period_start__lte=today,
            period_end__gte=today,
        ).values_list("person_id", flat=True)

        missing = target.exclude(person_id__in=already_submitted)

        for membership in missing:
            person = membership.person
            email = _get_email_for_person(person)
            if not email:
                results["skipped"] += 1
                continue

            lang = person.preferred_language if person.preferred_language in SUPPORTED_LANGUAGES else "en"

            try:
                _send_reminder_email(person, program, template, lang)
                results["sent"] += 1
            except Exception:
                logger.exception(
                    "Failed to send reminder to person %s (program %s, template %s)",
                    person.pk,
                    program_id,
                    template.pk,
                )
                results["errors"] += 1

    logger.info(
        "send_reflection_reminders program=%s role=%s: %s",
        program_id,
        role,
        results,
    )
    return results


def _send_reminder_email(person, program, template, lang: str) -> None:
    """Render and send a single reminder email."""
    context = {
        "person": person,
        "program": program,
        "template": template,
        "site_name": getattr(settings, "SITE_NAME", "BunkLogs"),
        "site_url": getattr(settings, "SITE_URL", "https://bunklogs.com"),
    }

    subject_map = {
        "en": f"Reminder: Submit your {template.name} reflection",
        "es": f"Recordatorio: Envía tu reflexión de {template.name}",
    }
    subject = subject_map.get(lang, subject_map["en"])

    text_body = render_to_string(f"emails/reflection_reminder_{lang}.txt", context)
    html_body = render_to_string(f"emails/reflection_reminder_{lang}.html", context)

    from_email = getattr(settings, "MAILGUN_FROM_EMAIL", None) or getattr(
        settings, "DEFAULT_FROM_EMAIL", "noreply@bunklogs.com"
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[_get_email_for_person(person)],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()


@shared_task(name="bunk_logs.core.tasks.dispatch_reflection_reminders")
def dispatch_reflection_reminders() -> dict:
    """Hourly dispatcher: check Program.settings reminder_schedules and fire reminders.

    Each active program may define:
        program.settings["reminder_schedules"] = {
            "counselor": "daily_18:00",
            "kitchen_staff": "weekly_friday_15:00",
            "leadership_team": "biweekly_monday_09:00",
        }
    This task runs every hour and dispatches send_reflection_reminders for any
    role whose schedule fires at the current hour.
    """
    from bunk_logs.core.models import Program

    now_local = timezone.localtime(timezone.now())
    today = now_local.date()
    current_hour = now_local.hour

    dispatched = []
    programs = Program.all_objects.filter(is_active=True).select_related("organization")

    for program in programs:
        schedules: dict = (program.settings or {}).get("reminder_schedules", {})
        if not schedules:
            continue

        for role, schedule_str in schedules.items():
            if _schedule_is_due(schedule_str, today, current_hour):
                send_reflection_reminders.delay(program.pk, role)
                dispatched.append({"program_id": program.pk, "role": role})
                logger.info(
                    "dispatch_reflection_reminders: queued program=%s role=%s",
                    program.pk,
                    role,
                )

    return {"dispatched": dispatched}

"""Celery Beat schedule registration for the translation pipeline (Step 7_5).

``CELERY_BEAT_SCHEDULER`` is ``django_celery_beat``'s DatabaseScheduler, so
periodic tasks live as ``PeriodicTask`` rows rather than in
``CELERY_BEAT_SCHEDULE`` settings dict. This module centralises the
registration helpers so a single data migration (or a manual ``shell_plus``
call) can install / remove the nightly ``purge_expired_translations`` row.

Both helpers take ``apps`` (the ``state apps`` Django passes to
``RunPython``) so they can be called from a frozen-state migration replay
without importing the real model classes at module load.
"""
from __future__ import annotations

import json

PERIODIC_TASK_NAME = "translation.purge_expired_translations.nightly"
PERIODIC_TASK_PATH = "bunk_logs.core.translation.purge_expired_translations"

# 03:15 server time -- after the day's reflection submissions have settled
# but well before any morning admin activity. ``CELERY_TIMEZONE`` controls
# the interpretation (defaults to Django's ``TIME_ZONE`` per settings).
SCHEDULE_HOUR = 3
SCHEDULE_MINUTE = 15


def register_periodic_tasks(apps) -> None:
    """Idempotently create/update the nightly GC ``PeriodicTask`` row.

    Designed for ``RunPython`` data migrations. Uses ``apps.get_model`` so
    it survives a frozen-state migration replay even after the
    ``django_celery_beat`` models evolve.

    Safe to call multiple times: re-runs (e.g. PR-preview redeploys)
    update the existing row in place rather than creating duplicates.
    """
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute=str(SCHEDULE_MINUTE),
        hour=str(SCHEDULE_HOUR),
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
    )
    PeriodicTask.objects.update_or_create(
        name=PERIODIC_TASK_NAME,
        defaults={
            "crontab": schedule,
            "interval": None,
            "task": PERIODIC_TASK_PATH,
            "args": json.dumps([]),
            "kwargs": json.dumps({}),
            "enabled": True,
            "description": (
                "Nightly garbage collection of TranslationRecord rows "
                "older than TRANSLATION_RETENTION_DAYS (Step 7_5)."
            ),
        },
    )


def unregister_periodic_tasks(apps) -> None:
    """Reverse of :func:`register_periodic_tasks`.

    Drops the ``PeriodicTask`` row but intentionally leaves the
    ``CrontabSchedule`` alone -- other tasks (existing or future) may
    share the same crontab and django-celery-beat does not orphan-clean
    schedules automatically.
    """
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=PERIODIC_TASK_NAME).delete()

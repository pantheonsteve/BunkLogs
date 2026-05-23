"""Register the hourly reflection-reminder dispatcher PeriodicTask (Step 7_14).

The dispatcher (``bunk_logs.core.tasks.dispatch_reflection_reminders``)
inspects each active Program's ``settings['reminder_schedules']`` map and
queues a per-role reminder if the schedule fires at the current hour.
Step 3_10 shipped the task itself; this migration finally wires it up to
Celery Beat so the day-of-week + time configurations (per Step 7_14 MA2
the TBE program uses ``"madrich": "weekly_wednesday_18:00"``) actually
dispatch in production.

Runs every hour at minute 0 so weekly Wednesday-evening / biweekly
Monday-morning / daily 18:00 schedules all hit their target hour. Each
program's per-role schedule controls which roles actually send mail on a
given firing — the dispatcher is intentionally cheap to run every hour.

Idempotent: uses ``update_or_create`` keyed on the well-known PeriodicTask
name so re-runs simply refresh the row in place.
"""
from __future__ import annotations

import json

from django.db import migrations

PERIODIC_TASK_NAME = "reflection_reminders.dispatch.hourly"
PERIODIC_TASK_PATH = "bunk_logs.core.tasks.dispatch_reflection_reminders"


def _register(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="*",
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
                "Hourly dispatcher for per-role reflection reminders "
                "(Step 7_14 MA2). Each Program's "
                "settings['reminder_schedules'] map drives the actual "
                "send schedule; the dispatcher is a no-op for hours that "
                "do not match any configured schedule."
            ),
        },
    )


def _unregister(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=PERIODIC_TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0037_seed_tbe_madrich_template"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_register, reverse_code=_unregister),
    ]

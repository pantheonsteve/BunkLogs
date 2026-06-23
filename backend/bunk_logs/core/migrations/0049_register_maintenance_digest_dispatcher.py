"""Register the hourly maintenance digest dispatcher PeriodicTask."""

from __future__ import annotations

import json

from django.db import migrations

PERIODIC_TASK_NAME = "maintenance.dispatch_daily_digests.hourly"
PERIODIC_TASK_PATH = "maintenance.dispatch_daily_digests"


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
                "Hourly dispatcher for per-org maintenance digest emails. "
                "Each org's maintenance_digest_time setting controls the "
                "actual send window."
            ),
        },
    )


def _unregister(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=PERIODIC_TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0048_assignmentgroup_add_team_group_type"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_register, reverse_code=_unregister),
    ]

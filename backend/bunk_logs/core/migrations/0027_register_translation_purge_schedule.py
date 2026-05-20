"""Register the nightly translation-record GC schedule (Step 7_5).

``CELERY_BEAT_SCHEDULER`` is ``DatabaseScheduler`` so periodic tasks must
live as ``django_celery_beat.PeriodicTask`` rows. The actual ORM bits are
in :mod:`bunk_logs.core.translation.beat` -- this migration is a thin
``RunPython`` wrapper so the schedule registration ships alongside the
GC task code rather than as an out-of-band ops step.

Idempotent on both forward and reverse: re-running the migration (e.g.
in a PR-preview redeploy) updates the existing row in place. Reversing
drops only the ``PeriodicTask`` row -- the shared ``CrontabSchedule`` is
left in place since other future tasks may reuse the same 03:15 slot.
"""
from django.db import migrations


def _forward(apps, schema_editor):
    from bunk_logs.core.translation.beat import register_periodic_tasks
    register_periodic_tasks(apps)


def _reverse(apps, schema_editor):
    from bunk_logs.core.translation.beat import unregister_periodic_tasks
    unregister_periodic_tasks(apps)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_person_translation_preference_alter_note_language_and_more"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_forward, reverse_code=_reverse),
    ]

"""Add observed_at for back-dated observations."""

from django.db import migrations
from django.db import models


def backfill_observed_at(apps, schema_editor):
    Observation = apps.get_model("notes", "Observation")
    for obs in Observation.objects.all().iterator():
        obs.observed_at = obs.created_at
        obs.save(update_fields=["observed_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0003_remove_noteaudiencecapture_note_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="observation",
            name="observed_at",
            field=models.DateTimeField(
                help_text="When the observation occurred; defaults to submission time but may be back-dated.",
                null=True,
            ),
        ),
        migrations.RunPython(backfill_observed_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="observation",
            name="observed_at",
            field=models.DateTimeField(
                help_text="When the observation occurred; defaults to submission time but may be back-dated.",
            ),
        ),
    ]

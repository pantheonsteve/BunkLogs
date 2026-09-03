"""Admin redesign enablers: group sort order and person invite timestamps.

Both columns are additive with safe defaults, so the previous code version
keeps running against the new schema while a deploy rolls: ``display_order``
defaults to 0, which makes the new ordering tuple collapse back to
``(group_type, name)`` until someone sets a value, and ``invited_at`` is
nullable. Backfill of ``invited_at`` from the audit log lives in 0065.
"""

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0063_tbe_madrich_template_terminology"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="assignmentgroup",
            options={"ordering": ["group_type", "display_order", "name"]},
        ),
        migrations.AddField(
            model_name="assignmentgroup",
            name="display_order",
            field=models.PositiveIntegerField(default=0, help_text="Lower sorts first within a group type. Ties fall back to name."),
        ),
        migrations.AddField(
            model_name="person",
            name="invited_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

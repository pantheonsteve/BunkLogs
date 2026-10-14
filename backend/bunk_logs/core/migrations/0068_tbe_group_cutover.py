"""Cut Temple Beth-El over to the class and cohort seats.

Slug ``tbe`` only. Reverse is a no-op: the previous seat mix is not restored.
"""
from django.db import migrations


def _apply(apps, schema_editor):
    from bunk_logs.core.tbe_group_cutover import cut_over_tbe

    cut_over_tbe()


def _noop(apps, schema_editor):
    return


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0067_program_display_alias"),
    ]

    operations = [
        migrations.RunPython(_apply, reverse_code=_noop),
    ]

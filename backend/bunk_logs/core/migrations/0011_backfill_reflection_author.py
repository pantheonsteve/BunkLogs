"""Data migration: populate Reflection.author from Reflection.subject for all existing rows.

Existing reflections are all self-reflections (subject == author).
"""
from django.db import migrations


def _backfill_author(apps, schema_editor):
    Reflection = apps.get_model("core", "Reflection")
    for ref in Reflection.objects.filter(author__isnull=True, subject__isnull=False):
        ref.author_id = ref.subject_id
        ref.save(update_fields=["author_id"])


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_assignmentgroup_assignmentgroupmembership_and_more"),
    ]

    operations = [
        migrations.RunPython(_backfill_author, reverse_code=_noop),
    ]

"""Turn on the reflection completion roster for Temple Beth-El.

Slug ``tbe`` only. Reverse is a no-op: the flag is left as it was set.
"""
from django.db import migrations


def enable_reflection_completion(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    org = Organization.objects.filter(slug="tbe").first()
    if org is None:
        return
    settings = dict(org.settings or {})
    if settings.get("reflection_completion") is True:
        return
    settings["reflection_completion"] = True
    org.settings = settings
    org.save(update_fields=["settings"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0068_tbe_group_cutover"),
    ]

    operations = [
        migrations.RunPython(enable_reflection_completion, reverse_code=migrations.RunPython.noop),
    ]

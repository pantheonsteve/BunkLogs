"""Recalibrate Camper Care memberships from domain_specialist to supervisor.

Step 3.21: Camper Care is treated as a unit-scoped supervisor whose visibility
flows through ``Membership.metadata.assigned_unit_slugs`` (the same convention
already used by leadership_team / faculty), instead of the wellness-template
shortcut intended for cross-unit specialists.

Forward-only: every existing row with ``role='camper_care'`` is bumped to
``capability='supervisor'``. The reverse direction is intentionally a no-op so
production rollbacks of *code* don't silently re-broaden visibility -- if the
mapping needs to be reverted we want a new explicit migration.

The mapping is duplicated here on purpose; historical migrations must not
import from live code (see ``0016_backfill_membership_capability.py`` for the
rationale).
"""

from django.db import migrations


def _recalibrate_camper_care(apps, schema_editor):
    Membership = apps.get_model("core", "Membership")
    Membership.objects.filter(role="camper_care").exclude(
        capability="supervisor",
    ).update(capability="supervisor")


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_alter_membership_capability_nonnull"),
    ]

    operations = [
        migrations.RunPython(_recalibrate_camper_care, reverse_code=_noop),
    ]

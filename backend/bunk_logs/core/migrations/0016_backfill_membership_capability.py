"""Data migration: backfill Membership.capability from role.

Idempotent — only writes rows where capability is null. Fails loudly with the
offending PK if a role has no mapping, so deploys surface the problem rather
than leaving NULLs that 0017 would then reject.

The mapping is duplicated from ``ROLE_TO_CAPABILITY`` in ``core/models.py`` on
purpose: historical migrations must not import from live code, since live code
can drift after the migration is recorded.
"""

from django.db import migrations

ROLE_TO_CAPABILITY = {
    "camper": "participant",
    "counselor": "participant",
    "junior_counselor": "participant",
    "specialist": "participant",
    "general_counselor": "participant",
    "kitchen_staff": "participant",
    "maintenance": "participant",
    "housekeeping": "participant",
    "madrich": "participant",
    "unit_head": "supervisor",
    "faculty": "supervisor",
    "leadership_team": "program_lead",
    "camper_care": "domain_specialist",
    "health_center": "domain_specialist",
    "special_diets": "domain_specialist",
    "admin": "admin",
}


def _backfill_capability(apps, schema_editor):
    Membership = apps.get_model("core", "Membership")
    for m in Membership.objects.filter(capability__isnull=True).only("id", "role"):
        try:
            m.capability = ROLE_TO_CAPABILITY[m.role]
        except KeyError as exc:
            msg = (
                f"Membership pk={m.pk} has role {m.role!r}, which is not in "
                "ROLE_TO_CAPABILITY. Add a mapping before re-running the migration."
            )
            raise RuntimeError(msg) from exc
        m.save(update_fields=["capability"])


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_membership_capability"),
    ]

    operations = [
        migrations.RunPython(_backfill_capability, reverse_code=_noop),
    ]

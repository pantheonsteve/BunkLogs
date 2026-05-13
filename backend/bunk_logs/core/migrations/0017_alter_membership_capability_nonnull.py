# Hand-written: tightens Membership.capability to NOT NULL after the backfill
# in 0016. Final state matches models.py so future `makemigrations` runs see no
# drift on this field.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_backfill_membership_capability"),
    ]

    operations = [
        migrations.AlterField(
            model_name="membership",
            name="capability",
            field=models.CharField(
                choices=[
                    ("participant", "Participant"),
                    ("supervisor", "Supervisor"),
                    ("program_lead", "Program Lead"),
                    ("domain_specialist", "Domain Specialist"),
                    ("admin", "Admin"),
                ],
                db_index=True,
                help_text="RBAC layer derived from role via ROLE_TO_CAPABILITY.",
                max_length=32,
            ),
        ),
    ]

# Generated manually for EOD submission reliability.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0005_alter_observation_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="observation",
            name="client_submission_id",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                help_text=(
                    "Client-supplied idempotency key for network-tolerant POST retries. "
                    "Unique per program when set."
                ),
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="observation",
            constraint=models.UniqueConstraint(
                condition=models.Q(("client_submission_id__isnull", False)),
                fields=("program", "client_submission_id"),
                name="obs_client_submission_unique",
            ),
        ),
    ]

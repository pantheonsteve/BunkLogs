import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0045_assignmentdashboardgrant"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="submitted_from_bunk",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Bunk the submitter was authoring when the request was filed. "
                    "Persisted at creation so Camper Care can route the ticket even "
                    "when the subject camper is unknown or off-roster."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cc_orders_submitted_from",
                to="core.assignmentgroup",
            ),
        ),
    ]

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0066_seed_faculty_self_reflection_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="program",
            name="display_alias",
            field=models.CharField(blank=True, db_default="", default="", max_length=100),
        ),
    ]

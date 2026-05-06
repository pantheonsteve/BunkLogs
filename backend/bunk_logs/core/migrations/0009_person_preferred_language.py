from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_fieldkey_core_fieldkey_global_key_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="preferred_language",
            field=models.CharField(
                choices=[("en", "English"), ("es", "Spanish")],
                default="en",
                help_text="Language for email communications",
                max_length=10,
            ),
        ),
    ]

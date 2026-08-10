# Generated manually for org branding image uploads.

import bunk_logs.core.models
import bunk_logs.core.storages
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0055_alter_person_user_person_uniq_person_org_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="logo",
            field=models.ImageField(
                blank=True,
                help_text="Sign-in page and app shell logo. Served from public media storage.",
                max_length=512,
                null=True,
                storage=bunk_logs.core.storages.select_public_media_storage,
                upload_to=bunk_logs.core.models.organization_branding_logo_upload_path,
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="login_hero",
            field=models.ImageField(
                blank=True,
                help_text="Right-side hero image on sign-in / sign-up / password-reset pages.",
                max_length=512,
                null=True,
                storage=bunk_logs.core.storages.select_public_media_storage,
                upload_to=bunk_logs.core.models.organization_branding_hero_upload_path,
            ),
        ),
    ]

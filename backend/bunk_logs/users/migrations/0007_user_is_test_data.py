# Generated by Django 5.0.13 on 2025-06-17 20:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_user_profile_complete_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_test_data',
            field=models.BooleanField(default=False, help_text='Mark this record as test/dummy data. Test data can be easily identified and deleted in bulk.', verbose_name='Is Test Data'),
        ),
    ]

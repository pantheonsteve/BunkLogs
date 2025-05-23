# Generated by Django 5.0.13 on 2025-04-18 19:24

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bunks', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='bunk',
            name='counselors',
            field=models.ManyToManyField(limit_choices_to={'role': 'Counselor'}, related_name='assigned_bunks', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='unit',
            name='unit_head',
            field=models.ForeignKey(limit_choices_to={'role': 'Unit Head'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_units', to=settings.AUTH_USER_MODEL),
        ),
    ]

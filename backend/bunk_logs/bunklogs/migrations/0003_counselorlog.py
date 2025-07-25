# Generated by Django 5.0.13 on 2025-06-23 19:16

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bunklogs', '0002_bunklog_is_test_data'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CounselorLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_test_data', models.BooleanField(default=False, help_text='Mark this record as test/dummy data. Test data can be easily identified and deleted in bulk.', verbose_name='Is Test Data')),
                ('date', models.DateField()),
                ('day_quality_score', models.PositiveSmallIntegerField(help_text='How was your day? (1 = terrible, 5 = best day ever)', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('support_level_score', models.PositiveSmallIntegerField(help_text='How supported did you feel today? (1 = unsupported, 5 = fully supported)', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('elaboration', models.TextField(help_text='Elaborate on why - positive or negative (providing more information about questions 1 and 2)')),
                ('day_off', models.BooleanField(default=False, help_text='Check if you are on a day off today')),
                ('staff_care_support_needed', models.BooleanField(default=False, help_text='Check if you would like staff care/engagement support')),
                ('values_reflection', models.TextField(help_text='How did the bunk exemplify our values today?')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('counselor', models.ForeignKey(limit_choices_to={'role': 'Counselor'}, on_delete=django.db.models.deletion.CASCADE, related_name='counselor_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'counselor log',
                'verbose_name_plural': 'counselor logs',
                'ordering': ['-date'],
                'unique_together': {('counselor', 'date')},
            },
        ),
    ]

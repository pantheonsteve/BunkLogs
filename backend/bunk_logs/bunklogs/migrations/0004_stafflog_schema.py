import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create the StaffLog concrete model table.

    StaffLog replaces the per-role CounselorLog concrete table with a single
    table shared by all staff reflection types. The existing CounselorLog rows
    are preserved in the next migration (0005_stafflog_data) before the old
    table is dropped in migration 0006_stafflog_proxy.
    """

    dependencies = [
        ("bunklogs", "0003_counselorlog"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_test_data", models.BooleanField(
                    default=False,
                    help_text="Mark this record as test/dummy data. Test data can be easily identified and deleted in bulk.",
                    verbose_name="Is Test Data",
                )),
                ("date", models.DateField()),
                ("day_quality_score", models.PositiveSmallIntegerField(
                    help_text="How was your day? (1 = terrible, 5 = best day ever)",
                    validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)],
                )),
                ("support_level_score", models.PositiveSmallIntegerField(
                    help_text="How supported did you feel today? (1 = unsupported, 5 = fully supported)",
                    validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)],
                )),
                ("elaboration", models.TextField(
                    help_text="Elaborate on why - positive or negative (providing more information about questions 1 and 2)",
                )),
                ("day_off", models.BooleanField(default=False, help_text="Check if you are on a day off today")),
                ("staff_care_support_needed", models.BooleanField(
                    default=False,
                    help_text="Check if you would like staff care/engagement support",
                )),
                ("values_reflection", models.TextField(
                    help_text="How did you/your team exemplify our values today?",
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("staff_member", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="staff_logs",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "staff log",
                "verbose_name_plural": "staff logs",
                "ordering": ["-date"],
                "unique_together": {("staff_member", "date")},
                "app_label": "bunklogs",
            },
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0047_alter_membership_role"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assignmentgroup",
            name="group_type",
            field=models.CharField(
                choices=[
                    ("bunk", "Bunk"),
                    ("classroom", "Classroom"),
                    ("caseload", "Caseload"),
                    ("unit", "Unit"),
                    ("division", "Division"),
                    ("cohort", "Cohort"),
                    ("team", "Team"),
                    ("specialty", "Specialty/Activity Group"),
                    ("custom", "Custom Group"),
                ],
                max_length=32,
            ),
        ),
    ]

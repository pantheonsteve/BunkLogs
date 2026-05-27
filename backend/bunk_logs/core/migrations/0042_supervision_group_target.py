"""Add target_group FK and ASSIGNMENT_GROUP target type to Supervision.

Allows supervisors (e.g. Camper Care) to be assigned to any AssignmentGroup
level (unit, division, …). The caseload resolver expands the group to all
active descendant bunks so the dashboard tree populates automatically.
"""

import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0041_subjectnote"),
    ]

    operations = [
        migrations.AddField(
            model_name="supervision",
            name="target_group",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Any AssignmentGroup when target_type=ASSIGNMENT_GROUP. "
                    "Caseload resolvers expand this to all active descendant bunks."
                ),
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="group_supervisions",
                to="core.assignmentgroup",
            ),
        ),
        migrations.AddIndex(
            model_name="supervision",
            index=models.Index(
                fields=["target_group"], name="core_superv_target__group_idx"
            ),
        ),
        migrations.AlterField(
            model_name="supervision",
            name="target_type",
            field=models.CharField(
                choices=[
                    ("membership", "Membership (direct supervisee)"),
                    ("role_in_program", "Role in program (team-by-role)"),
                    ("bunk", "Bunk (caseload entry)"),
                    ("assignment_group", "Assignment Group (hierarchy)"),
                ],
                db_index=True,
                max_length=24,
            ),
        ),
    ]

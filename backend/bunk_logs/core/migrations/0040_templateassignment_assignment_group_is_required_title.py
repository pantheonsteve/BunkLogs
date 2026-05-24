"""Step 7_20: Extend TemplateAssignment with assignment_group FK, is_required, and title.

All three fields are additive and nullable/defaulted, so existing rows remain valid.
No data migration is needed; FA-S (Step 7_22) handles seeding rows.
"""
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0039_refresh_tbe_madrich_template_category_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="templateassignment",
            name="assignment_group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="template_assignments",
                to="core.assignmentgroup",
                help_text=(
                    "When target_type='assignment_group', the group this assignment "
                    "targets. Memberships resolve to those whose role matches the "
                    "template's author_role_filter AND who hold an active "
                    "AssignmentGroupMembership in this group with role_in_group='author'."
                ),
            ),
        ),
        migrations.AddField(
            model_name="templateassignment",
            name="is_required",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "When True, the assignment produces tasks in the per-role dashboards. "
                    "When False, it appears in the role's optional forms library and does "
                    "NOT affect the 'all set' state (decision FA5)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="templateassignment",
            name="title",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                help_text=(
                    "Per-assignment display title for dashboard widgets. "
                    "Falls back to template.name when blank."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="templateassignment",
            name="target_type",
            field=models.CharField(
                max_length=16,
                choices=[
                    ("role", "Role (dynamic)"),
                    ("individuals", "Individual memberships (static)"),
                    ("tag_group", "Tag group (dynamic)"),
                    ("assignment_group", "Assignment group (dynamic)"),
                ],
            ),
        ),
        migrations.AddIndex(
            model_name="templateassignment",
            index=models.Index(
                fields=["assignment_group", "status"],
                name="core_templa_assignm_8ec6ca_idx",
            ),
        ),
    ]

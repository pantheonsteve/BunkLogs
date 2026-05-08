import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_person_preferred_language"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── AssignmentGroup ──────────────────────────────────────────────────
        migrations.CreateModel(
            name="AssignmentGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "name",
                    models.CharField(max_length=255),
                ),
                (
                    "slug",
                    models.SlugField(max_length=100),
                ),
                (
                    "group_type",
                    models.CharField(
                        choices=[
                            ("bunk", "Bunk"),
                            ("classroom", "Classroom"),
                            ("caseload", "Caseload"),
                            ("unit", "Unit"),
                            ("division", "Division"),
                            ("cohort", "Cohort"),
                            ("specialty", "Specialty/Activity Group"),
                            ("custom", "Custom Group"),
                        ],
                        max_length=32,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_groups",
                        to="core.organization",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        help_text="For nesting: bunk -> unit -> division",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="core.assignmentgroup",
                    ),
                ),
                (
                    "program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_groups",
                        to="core.program",
                    ),
                ),
            ],
            options={
                "ordering": ["group_type", "name"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="assignmentgroup",
            unique_together={("program", "slug")},
        ),
        migrations.AddIndex(
            model_name="assignmentgroup",
            index=models.Index(fields=["program", "group_type", "is_active"], name="core_assign_program_1_idx"),
        ),
        migrations.AddIndex(
            model_name="assignmentgroup",
            index=models.Index(fields=["parent"], name="core_assign_parent_idx"),
        ),

        # ── AssignmentGroupMembership ────────────────────────────────────────
        migrations.CreateModel(
            name="AssignmentGroupMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role_in_group",
                    models.CharField(
                        choices=[("subject", "Subject"), ("author", "Author")],
                        max_length=16,
                    ),
                ),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Role-specific data, e.g. {'is_lead_counselor': true}",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="core.assignmentgroup",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_group_memberships",
                        to="core.person",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="assignmentgroupmembership",
            index=models.Index(
                fields=["group", "role_in_group", "is_active"],
                name="core_agm_group_role_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="assignmentgroupmembership",
            index=models.Index(
                fields=["person", "role_in_group", "is_active"],
                name="core_agm_person_role_idx",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="assignmentgroupmembership",
            unique_together={("group", "person", "role_in_group")},
        ),

        # ── ReflectionTemplate new fields ────────────────────────────────────
        migrations.AddField(
            model_name="reflectiontemplate",
            name="subject_mode",
            field=models.CharField(
                choices=[
                    ("self", "Self-reflection (author == subject)"),
                    ("single_subject", "About one other person"),
                    ("multi_subject", "About multiple people in one submission"),
                    ("group", "About a group/unit, no individual subject"),
                ],
                default="self",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="reflectiontemplate",
            name="assignment_scope",
            field=models.CharField(
                choices=[
                    ("none", "No group context"),
                    ("per_subject_in_group", "One reflection per subject in the assignment group"),
                    ("per_group", "One reflection per group as a whole"),
                ],
                default="none",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="reflectiontemplate",
            name="assignment_group_types",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Which group types this template applies to, e.g. ['bunk']",
            ),
        ),
        migrations.AddField(
            model_name="reflectiontemplate",
            name="author_role_filter",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Membership roles eligible to author this template, e.g. ['counselor', 'unit_head']",
            ),
        ),
        migrations.AddField(
            model_name="reflectiontemplate",
            name="subject_role_filter",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Membership roles eligible to be subjects, e.g. ['camper']. Empty = any role.",
            ),
        ),
        migrations.AddField(
            model_name="reflectiontemplate",
            name="required_per_subject_per_period",
            field=models.IntegerField(
                default=1,
                help_text="How many reflections per subject per cadence period for completion",
            ),
        ),
        migrations.AddField(
            model_name="reflectiontemplate",
            name="subject_visible",
            field=models.BooleanField(
                default=False,
                help_text="Whether the subject can see reflections about themselves",
            ),
        ),

        # ── Reflection: rename person→subject, add new fields ────────────────
        migrations.RenameField(
            model_name="reflection",
            old_name="person",
            new_name="subject",
        ),
        migrations.AlterField(
            model_name="reflection",
            name="subject",
            field=models.ForeignKey(
                blank=True,
                help_text="Who this reflection is ABOUT. Null when subject_mode='group'.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reflections_about",
                to="core.person",
            ),
        ),
        migrations.AddField(
            model_name="reflection",
            name="subject_group",
            field=models.ForeignKey(
                blank=True,
                help_text="Set when subject_mode='group'",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reflections_as_subject",
                to="core.assignmentgroup",
            ),
        ),
        migrations.AddField(
            model_name="reflection",
            name="author",
            field=models.ForeignKey(
                blank=True,
                help_text="Who FILLED OUT this reflection (may equal subject for self-reflection)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reflections_authored",
                to="core.person",
            ),
        ),
        migrations.AddField(
            model_name="reflection",
            name="assignment_group",
            field=models.ForeignKey(
                blank=True,
                help_text="Which group context this was authored in (e.g. which bunk)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reflections",
                to="core.assignmentgroup",
            ),
        ),
        migrations.AddField(
            model_name="reflection",
            name="submission_id",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                help_text="Groups multi-subject submissions together",
            ),
        ),

        # ── Reflection: update indexes ────────────────────────────────────────
        migrations.RemoveIndex(
            model_name="reflection",
            name="core_reflec_person__71d77a_idx",
        ),
        migrations.AddIndex(
            model_name="reflection",
            index=models.Index(fields=["subject", "period_end"], name="core_reflec_subject_idx"),
        ),
        migrations.AddIndex(
            model_name="reflection",
            index=models.Index(fields=["subject_group", "period_end"], name="core_reflec_subj_grp_idx"),
        ),
        migrations.AddIndex(
            model_name="reflection",
            index=models.Index(fields=["assignment_group", "period_end"], name="core_reflec_asg_grp_idx"),
        ),
        migrations.AddIndex(
            model_name="reflection",
            index=models.Index(fields=["author", "period_end"], name="core_reflec_author_idx"),
        ),
        migrations.AddIndex(
            model_name="reflection",
            index=models.Index(fields=["submission_id"], name="core_reflec_sub_id_idx"),
        ),
    ]

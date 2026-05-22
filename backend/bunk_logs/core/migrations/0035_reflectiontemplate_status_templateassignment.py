"""Step 7_12 PR B — add ReflectionTemplate.status + TemplateAssignment.

Schema migration safety (per CLAUDE.md "full mode" criteria):

1. ``status`` default is ``"published"`` so any row inserted by old code
   (which only writes ``is_active``) keeps its expected lifecycle. Old
   readers that only inspect ``is_active`` continue to work; the new
   field is additive, not a replacement.
2. The ``RunPython`` backfill walks all existing rows and translates
   ``is_active`` -> ``status``. Idempotent: re-running yields the same
   final state. ``reverse_code=RunPython.noop`` because we never want to
   strip ``status`` data on rollback (the column drop in
   ``AddField.reverse`` handles that).
3. ``TemplateAssignment`` is a wholly new table with no prior data.
4. No indexes are created on a non-empty table for ``status`` directly;
   the per-org filter remains efficient through the existing
   ``(organization, slug)`` composite. If hot paths emerge we can add
   the index in a follow-up.

Tested on a ``make sync-prod-db`` snapshot before merge.
"""

import django.db.models.deletion
from django.db import migrations
from django.db import models


def backfill_status_from_is_active(apps, schema_editor):
    """Translate the boolean ``is_active`` to the lifecycle ``status`` enum.

    * ``is_active=True``  -> ``status="published"`` (default; no-op for
      most rows)
    * ``is_active=False`` -> ``status="archived"``

    Idempotent: subsequent runs leave already-archived rows untouched
    and never overwrite a non-default ``status`` value.
    """
    ReflectionTemplate = apps.get_model("core", "ReflectionTemplate")
    ReflectionTemplate.objects.filter(is_active=False, status="published").update(
        status="archived",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0034_seed_leadership_team_self_reflection_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="reflectiontemplate",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("published", "Published"),
                    ("archived", "Archived"),
                ],
                default="published",
                help_text=(
                    "Lifecycle state. 'published' templates can collect "
                    "responses, 'draft' are LT-builder work-in-progress, "
                    "'archived' are preserved read-only for historical "
                    "reflections. Old code that only inspects ``is_active`` "
                    "keeps working because the default is 'published' "
                    "(matches is_active=True)."
                ),
                max_length=16,
            ),
        ),
        migrations.RunPython(
            backfill_status_from_is_active,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.CreateModel(
            name="TemplateAssignment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "target_type",
                    models.CharField(
                        choices=[
                            ("role", "Role (dynamic)"),
                            ("individuals", "Individual memberships (static)"),
                            ("tag_group", "Tag group (dynamic)"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "target_payload",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text=(
                            "Shape depends on target_type. role: "
                            "{'role': 'kitchen_staff'}. individuals: "
                            "{'membership_ids': [<int>...]}. tag_group: "
                            "{'tag': 'kitchen-lead'}."
                        ),
                    ),
                ),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                (
                    "cadence_override",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("daily", "Daily"),
                            ("weekly", "Weekly"),
                            ("biweekly", "Biweekly"),
                            ("monthly", "Monthly"),
                            ("on_demand", "On Demand"),
                        ],
                        help_text="If set, overrides template.cadence for this assignment.",
                        max_length=32,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("scheduled", "Scheduled"),
                            ("active", "Active"),
                            ("ended", "Ended"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="scheduled",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="template_assignments_created",
                        to="core.membership",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="template_assignments",
                        to="core.organization",
                    ),
                ),
                (
                    "program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="template_assignments",
                        to="core.program",
                    ),
                ),
                (
                    "replaces",
                    models.ForeignKey(
                        blank=True,
                        help_text=(
                            "Set when this assignment ended a prior one "
                            "(conflict_resolution='replace')."
                        ),
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="replaced_by",
                        to="core.templateassignment",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="core.reflectiontemplate",
                    ),
                ),
            ],
            options={
                "ordering": ["-start_date", "-created_at"],
                "indexes": [
                    models.Index(
                        fields=["organization", "template", "status"],
                        name="core_templa_organiz_445ab3_idx",
                    ),
                    models.Index(
                        fields=["program", "start_date", "end_date"],
                        name="core_templa_program_2b2470_idx",
                    ),
                ],
            },
        ),
    ]

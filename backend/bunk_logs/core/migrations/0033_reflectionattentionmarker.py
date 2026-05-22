"""Add ReflectionAttentionMarker model (Step 7_12 PR A — Story 46 c5).

Net-new table. Markers are placed by supervisor Memberships against
Reflection rows and are visible to the placing supervisor plus any
co-supervisors. The reflection itself is not mutated.
"""

import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0032_seed_camper_care_self_reflection_template"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReflectionAttentionMarker",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "marker_membership",
                    models.ForeignKey(
                        help_text="Supervisor Membership that placed the marker.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attention_markers_placed",
                        to="core.membership",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reflection_attention_markers",
                        to="core.organization",
                    ),
                ),
                (
                    "reflection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attention_markers",
                        to="core.reflection",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["reflection", "created_at"],
                        name="core_reflec_reflect_82d2c2_idx",
                    ),
                    models.Index(
                        fields=["marker_membership", "created_at"],
                        name="core_reflec_marker__a7c2e0_idx",
                    ),
                ],
                "unique_together": {("reflection", "marker_membership")},
            },
        ),
    ]

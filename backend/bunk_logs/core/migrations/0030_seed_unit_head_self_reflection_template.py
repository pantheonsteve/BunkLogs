"""Seed the global Unit Head self-reflection ReflectionTemplate (Step 7_7).

Mirrors the counselor seed (migration 0029) in shape: a single
``organization IS NULL`` template that any tenant can override with an
org-scoped row via the resolver in ``api/unit_head/common.py``. Targets
the ``unit_head`` Membership role.

Schema design (Story 16):
1. ``day_off`` (yes_no) — same shortcut counselors get; UH self-reflections
   are daily by default.
2. ``overall_day`` (single_rating) — primary score surfaced in the
   dashboard "My reflection" section.
3. ``wins`` / ``improvements`` (text_list) — open-ended reflection.
4. ``concern`` (textarea) — generic supervisor flag for the UH's own LT.
5. ``bunk_concerns_bunks`` (multiple_choice, ``option_source="supervised_bunks"``)
    — optional Story 16 criterion 7 / UH2 field. Options are resolved at
    render time from the viewer's active counselor supervisions; the
    write API validates submitted IDs against that set. When populated,
    the Bunk Dashboard (Story 11) surfaces this UH self-reflection in the
    "Bunk concerns" section for each referenced bunk.
6. ``bunk_concerns_note`` (textarea) — narrative paired with the bunk
    selection above.

All scored / list fields are ``required: false`` so the ``day_off``
shortcut payload ``{"day_off": true}`` validates without other fields.
English + Spanish prompts are seeded.
"""

from django.db import migrations

SLUG = "unit-head-self-reflection"
NAME = "Unit Head Self-Reflection"
LANGUAGES = ["en", "es"]


def _schema() -> dict:
    return {
        "fields": [
            {
                "key": "day_off",
                "type": "yes_no",
                "required": False,
                "prompts": {
                    "en": "Are you taking a day off today?",
                    "es": "¿Estás tomando un día libre hoy?",
                },
            },
            {
                "key": "overall_day",
                "type": "single_rating",
                "required": False,
                "scale": [1, 5],
                "scale_labels": {
                    "en": ["Difficult", "Tough", "OK", "Good", "Great"],
                    "es": ["Difícil", "Duro", "Regular", "Bueno", "Excelente"],
                },
                "dashboard_role": "primary_rating",
            },
            {
                "key": "wins",
                "type": "text_list",
                "required": False,
                "prompts": {
                    "en": "What went well across your unit today?",
                    "es": "¿Qué salió bien en tu unidad hoy?",
                },
                "dashboard_role": "wins",
            },
            {
                "key": "improvements",
                "type": "text_list",
                "required": False,
                "prompts": {
                    "en": "What could go differently tomorrow?",
                    "es": "¿Qué podría ser diferente mañana?",
                },
                "dashboard_role": "improvements",
            },
            {
                "key": "concern",
                "type": "textarea",
                "required": False,
                "prompts": {
                    "en": "Anything you want to flag for your team?",
                    "es": "¿Algo que quieras compartir con tu equipo?",
                },
                "dashboard_role": "open_concern",
            },
            {
                "key": "bunk_concerns_bunks",
                "type": "multiple_choice",
                "required": False,
                "option_source": "supervised_bunks",
                "prompts": {
                    "en": "Which bunks (if any) have something to flag?",
                    "es": "¿Qué cabañas (si las hay) tienen algo que destacar?",
                },
            },
            {
                "key": "bunk_concerns_note",
                "type": "textarea",
                "required": False,
                "prompts": {
                    "en": "What should the bunk team know?",
                    "es": "¿Qué debe saber el equipo de la cabaña?",
                },
            },
        ],
    }


def _seed_template(apps, schema_editor):
    ReflectionTemplate = apps.get_model("core", "ReflectionTemplate")
    ReflectionTemplate.objects.update_or_create(
        organization=None,
        slug=SLUG,
        version=1,
        defaults={
            "name": NAME,
            "description": (
                "Daily self-reflection for Unit Heads. Includes a 'day off' "
                "shortcut and an optional bunk-concerns flag whose options are "
                "populated server-side from the viewer's supervised bunks."
            ),
            "cadence": "daily",
            "schema": _schema(),
            "languages": LANGUAGES,
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["unit_head"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": False,
            "role": "unit_head",
            "program_type": None,
        },
    )


def _remove_template(apps, schema_editor):
    ReflectionTemplate = apps.get_model("core", "ReflectionTemplate")
    ReflectionTemplate.objects.filter(
        organization__isnull=True, slug=SLUG, version=1,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0029_seed_counselor_self_reflection_template"),
    ]

    operations = [
        migrations.RunPython(_seed_template, reverse_code=_remove_template),
    ]

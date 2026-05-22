"""Seed the global Leadership Team self-reflection ReflectionTemplate (Step 7_12 PR A).

Targets the ``leadership_team`` Membership role. Differs from the other
role flows in two ways:

* ``cadence='biweekly'`` per Story 50 c2 (default biweekly, configurable per program).
* ``supports_privacy=True`` per Story 50 c11 — the private toggle restricts
  the reflection to author + Admin only (sensitive variant of the
  ``leadership_team_self_reflection`` content type).

English + Spanish prompts are seeded so the form renders in either
language out of the box.
"""

from django.db import migrations

SLUG = "leadership-team-self-reflection"
NAME = "Leadership Team Self-Reflection"
LANGUAGES = ["en", "es"]


def _schema() -> dict:
    return {
        "fields": [
            {
                "key": "overall_period",
                "type": "single_rating",
                "required": False,
                "scale": [1, 5],
                "scale_labels": {
                    "en": ["Difficult", "Tough", "OK", "Good", "Great"],
                    "es": ["Difícil", "Duro", "Regular", "Bueno", "Excelente"],
                },
                "dashboard_role": "primary_rating",
                "prompts": {
                    "en": "How did the last two weeks feel overall?",
                    "es": "¿Cómo se sintieron las últimas dos semanas en general?",
                },
            },
            {
                "key": "wins",
                "type": "text_list",
                "required": False,
                "prompts": {
                    "en": "What went well across the teams you supervise?",
                    "es": "¿Qué salió bien en los equipos que supervisas?",
                },
                "dashboard_role": "wins",
            },
            {
                "key": "improvements",
                "type": "text_list",
                "required": False,
                "prompts": {
                    "en": "What needs more attention next period?",
                    "es": "¿Qué necesita más atención el próximo período?",
                },
                "dashboard_role": "improvements",
            },
            {
                "key": "concern",
                "type": "textarea",
                "required": False,
                "prompts": {
                    "en": "Anything to flag for your leadership peers or admin?",
                    "es": "¿Algo que quieras compartir con tus pares de liderazgo o administración?",
                },
                "dashboard_role": "open_concern",
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
                "Biweekly self-reflection for Leadership Team members. "
                "Supports the per-submission private toggle (Story 50 c11) "
                "which restricts visibility to the author plus org Admin."
            ),
            "cadence": "biweekly",
            "schema": _schema(),
            "languages": LANGUAGES,
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["leadership_team"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": True,
            "role": "leadership_team",
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
        ("core", "0033_reflectionattentionmarker"),
    ]

    operations = [
        migrations.RunPython(_seed_template, reverse_code=_remove_template),
    ]

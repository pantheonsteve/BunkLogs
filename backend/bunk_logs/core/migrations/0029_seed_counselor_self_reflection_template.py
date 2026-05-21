"""Seed the global counselor self-reflection ReflectionTemplate (Step 7_6c).

A single ``organization IS NULL`` template that applies to both ``counselor``
and ``junior_counselor`` Memberships. Org-scoped templates may shadow it via
the resolution helper in ``api/counselor/common.py``; this seed only lights
up tenants that haven't authored their own.

Schema design (Story 5):
1. ``day_off`` (yes_no) — the shortcut described in Story 5 criterion 3.
2. ``overall_day`` (single_rating) — the primary dashboard score.
3. ``wins`` (text_list) — what went well.
4. ``improvements`` (text_list) — what could be different.
5. ``concern`` (textarea) — open-ended flag to supervisors.

All fields are ``required: false`` so the ``day_off`` shortcut payload
``{"day_off": true}`` validates without the other fields needing values.
English + Spanish are seeded; additional languages can be backfilled by a
later migration without touching this row's ``version``.

The migration is idempotent: re-applying ``get_or_create`` keyed on
``(organization=None, slug, version)`` does not create a duplicate row,
and ``reverse_code`` only removes the row we created.
"""

from django.db import migrations

SLUG = "counselor-self-reflection"
NAME = "Counselor Self-Reflection"
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
                    "en": "What went well today?",
                    "es": "¿Qué salió bien hoy?",
                },
                "dashboard_role": "wins",
            },
            {
                "key": "improvements",
                "type": "text_list",
                "required": False,
                "prompts": {
                    "en": "What could you do differently tomorrow?",
                    "es": "¿Qué podrías hacer diferente mañana?",
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
                "Daily self-reflection for counselors. Includes a 'day off' "
                "shortcut that records a complete-but-empty submission."
            ),
            "cadence": "daily",
            "schema": _schema(),
            "languages": LANGUAGES,
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["counselor", "junior_counselor"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": False,
            "role": "counselor",
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
        ("core", "0028_camperdaystate_orderitemsuggestion_ticketphoto_and_more"),
    ]

    operations = [
        migrations.RunPython(_seed_template, reverse_code=_remove_template),
    ]

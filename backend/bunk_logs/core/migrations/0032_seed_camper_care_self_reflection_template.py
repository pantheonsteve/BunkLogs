"""Seed the global Camper Care self-reflection ReflectionTemplate (Step 7_8d).

Parallels the Unit Head seed (0030) in shape: a single
``organization IS NULL`` row that any tenant can override with an
org-scoped version via the resolver in ``api/camper_care/common.py``.
Targets the ``camper_care`` Membership role.

The schema mirrors UH's with one rename: ``bunk_concerns_bunks`` uses
``option_source="caseload_bunks"`` so the frontend knows to populate
options from CC's caseload rather than UH's supervised counselors.
The write API resolves both sources to the same shape (a list of bunk
IDs) so the validation is uniform.

The seed is reversible — used by tests to spin up the template and
torn down with ``migrate core 0031``.
"""

from django.db import migrations

SLUG = "camper-care-self-reflection"
NAME = "Camper Care Self-Reflection"
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
                    "en": "What went well across your caseload today?",
                    "es": "¿Qué salió bien en tu carga hoy?",
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
                    "en": "Anything to flag for your supervisor / Leadership Team?",
                    "es": "¿Algo que quieras compartir con tu supervisor o equipo de liderazgo?",
                },
                "dashboard_role": "open_concern",
            },
            {
                "key": "bunk_concerns_bunks",
                "type": "multiple_choice",
                "required": False,
                "option_source": "caseload_bunks",
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
                "Daily self-reflection for Camper Care role. Includes a 'day "
                "off' shortcut and an optional bunk-concerns flag whose "
                "options are populated server-side from the viewer's "
                "caseload."
            ),
            "cadence": "daily",
            "schema": _schema(),
            "languages": LANGUAGES,
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["camper_care"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": False,
            "role": "camper_care",
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
        ("core", "0031_note_category_flag"),
    ]

    operations = [
        migrations.RunPython(_seed_template, reverse_code=_remove_template),
    ]

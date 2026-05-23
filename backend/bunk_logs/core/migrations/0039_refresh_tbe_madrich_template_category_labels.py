"""Refresh TBE Madrich rating-group categories to use ``labels`` (plural).

The original seed in 0037 mistakenly used ``label`` (singular) for each
rating-group category, but the frontend ``ReflectionField`` renderer
reads ``cat.labels[lang]`` and falls back to ``cat.key``, so categories
rendered as ``reliability_punctuality`` etc. instead of their human
labels. Re-run the seed (idempotent via ``update_or_create``) so any
environment that already applied 0037 picks up the corrected schema
without manual intervention.
"""
from django.db import migrations

SLUG = "tbe-madrich-3-2-1-weekly"
NAME = "TBE Madrich Weekly 3-2-1"
LANGUAGES = ["en"]


def _schema() -> dict:
    return {
        "fields": [
            {
                "key": "wins",
                "type": "text_list",
                "required": True,
                "min_items": 3,
                "max_items": 3,
                "prompts": {"en": "Three wins from this week"},
                "dashboard_role": "wins",
            },
            {
                "key": "improvements",
                "type": "text_list",
                "required": True,
                "min_items": 2,
                "max_items": 2,
                "prompts": {"en": "Two things to improve next week"},
                "dashboard_role": "improvements",
            },
            {
                "key": "question_or_concern",
                "type": "text",
                "required": True,
                "prompts": {"en": "One question or concern for your Director"},
                "dashboard_role": "open_concern",
            },
            {
                "key": "ratings",
                "type": "rating_group",
                "required": True,
                "scale": [1, 4],
                "scale_labels": {
                    "en": [
                        "Unsatisfactory",
                        "Needs Improvement",
                        "Meets Expectations",
                        "Exceeds Expectations",
                    ],
                },
                "categories": [
                    {
                        "key": "reliability_punctuality",
                        "labels": {"en": "Reliability & Punctuality"},
                    },
                    {"key": "initiative", "labels": {"en": "Initiative"}},
                    {"key": "communication", "labels": {"en": "Communication"}},
                    {"key": "problem_solving", "labels": {"en": "Problem Solving"}},
                    {"key": "interpersonal", "labels": {"en": "Interpersonal"}},
                ],
                "prompts": {"en": "Rate yourself in each area for the week"},
                "dashboard_role": "primary_rating",
            },
        ],
    }


def _refresh(apps, schema_editor):
    ReflectionTemplate = apps.get_model("core", "ReflectionTemplate")
    ReflectionTemplate.objects.update_or_create(
        organization=None,
        slug=SLUG,
        version=1,
        defaults={
            "name": NAME,
            "description": (
                "Weekly self-reflection for TBE Madrichim using Rachel's "
                "3-2-1 format. Standard visibility (Director + TBE Admin); "
                "no sensitive-note variant at Tier 1."
            ),
            "cadence": "weekly",
            "schema": _schema(),
            "languages": LANGUAGES,
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["madrich"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": False,
            "role": "madrich",
            "program_type": "religious_school",
        },
    )


def _noop(apps, schema_editor):
    return


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0038_register_reflection_reminder_dispatcher"),
    ]

    operations = [
        migrations.RunPython(_refresh, reverse_code=_noop),
    ]

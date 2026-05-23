"""Seed the global TBE 3-2-1 Madrich weekly reflection template (Step 7_14).

Targets the ``madrich`` Membership role with weekly cadence per MA1
(Monday-Sunday). Schema follows Story 62 c1:

* 3 wins (``text_list``, exactly 3 items, required)
* 2 improvements (``text_list``, exactly 2 items, required)
* 1 open question or concern (``text``, required)
* 5 ratings (``rating_group``, 5 categories from Rachel's proposal on a
  1-4 scale: Unsatisfactory / Needs Improvement / Meets Expectations /
  Exceeds Expectations)

English-only prompts at Tier 1 per the TBE scope statement; the schema
nevertheless uses the ``prompts`` / ``scale_labels`` localized-key shape
so Hebrew can be added later without a data migration.

Idempotent via ``update_or_create`` keyed on (organization=NULL, slug,
version) so re-running on a preview redeploy refreshes the row in place.
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
                "prompts": {
                    "en": "Three wins from this week",
                },
                "dashboard_role": "wins",
            },
            {
                "key": "improvements",
                "type": "text_list",
                "required": True,
                "min_items": 2,
                "max_items": 2,
                "prompts": {
                    "en": "Two things to improve next week",
                },
                "dashboard_role": "improvements",
            },
            {
                "key": "question_or_concern",
                "type": "text",
                "required": True,
                "prompts": {
                    "en": "One question or concern for your Director",
                },
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
                        "label": {"en": "Reliability & Punctuality"},
                    },
                    {
                        "key": "initiative",
                        "label": {"en": "Initiative"},
                    },
                    {
                        "key": "communication",
                        "label": {"en": "Communication"},
                    },
                    {
                        "key": "problem_solving",
                        "label": {"en": "Problem Solving"},
                    },
                    {
                        "key": "interpersonal",
                        "label": {"en": "Interpersonal"},
                    },
                ],
                "prompts": {
                    "en": "Rate yourself in each area for the week",
                },
                "dashboard_role": "primary_rating",
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


def _remove_template(apps, schema_editor):
    ReflectionTemplate = apps.get_model("core", "ReflectionTemplate")
    ReflectionTemplate.objects.filter(
        organization__isnull=True, slug=SLUG, version=1,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0036_admin_templates_review_metadata"),
    ]

    operations = [
        migrations.RunPython(_seed_template, reverse_code=_remove_template),
    ]

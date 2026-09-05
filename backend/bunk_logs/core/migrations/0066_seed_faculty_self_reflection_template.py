"""Seed the global Faculty weekly self-reflection template.

Faculty home already reviews Madrich 3-2-1s; this is the form faculty
fill about their own week so /tasks can show a Submit reflection CTA.
Also binds the template to existing TBE programs that already have a
faculty membership, so local/prod tenants pick it up on migrate.
"""

from datetime import date
from datetime import timedelta

from django.db import migrations

SLUG = "faculty-self-reflection"
NAME = "Faculty Weekly Reflection"
LANGUAGES = ["en"]


def _schema() -> dict:
    return {
        "fields": [
            {
                "key": "overall_week",
                "type": "single_rating",
                "required": False,
                "scale": [1, 5],
                "scale_labels": {
                    "en": ["Difficult", "Tough", "OK", "Good", "Great"],
                },
                "dashboard_role": "primary_rating",
                "prompts": {
                    "en": "How did this week feel in your classroom?",
                },
            },
            {
                "key": "wins",
                "type": "text_list",
                "required": False,
                "prompts": {
                    "en": "What went well with your Madrichim or students?",
                },
                "dashboard_role": "wins",
            },
            {
                "key": "improvements",
                "type": "text_list",
                "required": False,
                "prompts": {
                    "en": "What would you change next week?",
                },
                "dashboard_role": "improvements",
            },
            {
                "key": "support_needed",
                "type": "textarea",
                "required": False,
                "prompts": {
                    "en": "Anything the Director should know or help with?",
                },
                "dashboard_role": "open_concern",
            },
        ],
    }


def _seed_template(apps, schema_editor):
    ReflectionTemplate = apps.get_model("core", "ReflectionTemplate")
    Organization = apps.get_model("core", "Organization")
    Program = apps.get_model("core", "Program")
    Membership = apps.get_model("core", "Membership")
    TemplateAssignment = apps.get_model("core", "TemplateAssignment")

    template, _ = ReflectionTemplate.objects.update_or_create(
        organization=None,
        slug=SLUG,
        version=1,
        defaults={
            "name": NAME,
            "description": (
                "Weekly self-reflection for faculty. Surfaces on My tasks "
                "so teachers can submit without a dedicated faculty form route."
            ),
            "cadence": "weekly",
            "schema": _schema(),
            "languages": LANGUAGES,
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["faculty"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": False,
            "role": "faculty",
            "program_type": "religious_school",
        },
    )

    today = date.today()
    for org in Organization.objects.filter(slug="tbe"):
        program_ids = (
            Membership.objects.filter(
                role="faculty",
                is_active=True,
                program__organization=org,
            )
            .values_list("program_id", flat=True)
            .distinct()
        )
        for program in Program.objects.filter(pk__in=program_ids):
            start = min(program.start_date, today) - timedelta(days=365)
            TemplateAssignment.objects.get_or_create(
                organization_id=org.pk,
                program=program,
                template=template,
                target_type="role",
                target_payload={"role": "faculty"},
                defaults={
                    "start_date": start,
                    "status": "active",
                    "is_required": True,
                },
            )


def _remove_template(apps, schema_editor):
    ReflectionTemplate = apps.get_model("core", "ReflectionTemplate")
    TemplateAssignment = apps.get_model("core", "TemplateAssignment")
    TemplateAssignment.objects.filter(
        template__organization__isnull=True,
        template__slug=SLUG,
        template__version=1,
        target_type="role",
        target_payload={"role": "faculty"},
    ).delete()
    ReflectionTemplate.objects.filter(
        organization__isnull=True, slug=SLUG, version=1,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0065_backfill_person_invited_at"),
    ]

    operations = [
        migrations.RunPython(_seed_template, reverse_code=_remove_template),
    ]

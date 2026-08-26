"""Point the TBE Madrich 3-2-1 prompts at TBE's own vocabulary.

``Organization.settings["terminology"]`` renames app chrome, but these two
prompts are authored content inside ``ReflectionTemplate.schema`` and so
still read "your Director" / "your cohort" where the rest of the TBE app
now says "the Ed Team" / "your Teaching Team".

Only rewrites a prompt that still matches the string 0037/0060 seeded, so
an admin who has already reworded the field keeps their wording and a
re-run is a no-op.

The template is global (``organization`` is null) but TBE-specific by slug
and by its ``madrich`` role, which no camp org uses. A second religious
school would get its own template rather than inherit this wording.
"""
from django.db import migrations

SLUG = "tbe-madrich-3-2-1-weekly"

# field key -> (language, prompt seeded before this migration, replacement)
PROMPT_REWRITES = {
    "question_or_concern": (
        "en",
        "One question or concern for your Director",
        "One question or concern for the Ed Team",
    ),
    "shared_idea": (
        "en",
        "Anything you'd like to share with the rest of your cohort? (optional)",
        "Anything you'd like to share with the rest of your Teaching Team? (optional)",
    ),
}


def _patch_schema(schema: dict) -> bool:
    """Rewrite untouched prompts in place; return whether anything changed."""
    fields = schema.get("fields")
    if not isinstance(fields, list):
        return False

    changed = False
    for field in fields:
        if not isinstance(field, dict):
            continue
        rewrite = PROMPT_REWRITES.get(field.get("key"))
        if rewrite is None:
            continue
        language, previous, replacement = rewrite
        prompts = field.get("prompts")
        if not isinstance(prompts, dict) or prompts.get(language) != previous:
            continue
        prompts[language] = replacement
        changed = True
    return changed


def _apply(apps, schema_editor):
    ReflectionTemplate = apps.get_model("core", "ReflectionTemplate")
    for template in ReflectionTemplate.objects.filter(slug=SLUG):
        schema = template.schema
        if isinstance(schema, dict) and _patch_schema(schema):
            template.schema = schema
            template.save(update_fields=["schema"])


def _noop(apps, schema_editor):
    return


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0062_alter_membership_role"),
    ]

    operations = [
        migrations.RunPython(_apply, reverse_code=_noop),
    ]

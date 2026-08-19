"""Turn the TBE Madrich 3-2-1 answers into threaded surfaces (Step 4_9).

Adds the thread/routing/cohort flags to the weekly template so the role
homepages have something to render: wins and improvements thread per
list item, the question routes to the Director's queue, and a new
optional ``shared_idea`` field publishes to the cohort feed.

Patches the existing schema field-by-field rather than rewriting it, so
an environment where an admin has edited prompts keeps those edits, and
re-running the migration is a no-op.
"""
from django.db import migrations

SLUG = "tbe-madrich-3-2-1-weekly"

# key -> keys to merge onto that field
#
# ``ratings`` also gets a dashboard_role correction. 0037 seeded it as
# ``primary_rating``, which the validator only allows on ``single_rating``,
# so the template has never passed its own ``clean()``. Nothing read it
# usefully either: ``api/dashboards/trends.py`` would have treated the
# category dict as a scalar. ``category_ratings`` is what the FieldKey
# registry already expects for these keys.
FIELD_FLAGS = {
    "wins": {"thread_enabled": True, "thread_scope": "item"},
    "improvements": {"thread_enabled": True, "thread_scope": "item"},
    "question_or_concern": {"thread_enabled": True, "routes_to": "director"},
    "ratings": {"dashboard_role": "category_ratings"},
}

SHARED_IDEA_FIELD = {
    "key": "shared_idea",
    "type": "textarea",
    "required": False,
    "prompts": {
        "en": "Anything you'd like to share with the rest of your cohort? (optional)",
    },
    "thread_enabled": True,
    "share_with_cohort": True,
}

# The ratings matrix stays last in the form, so a new prose field goes
# immediately before it rather than at the end of the list.
_ANCHOR_KEY = "ratings"


def _patch_schema(schema: dict) -> tuple[dict, bool]:
    """Return ``(schema, changed)`` with thread flags and ``shared_idea`` applied."""
    fields = schema.get("fields")
    if not isinstance(fields, list):
        return schema, False

    changed = False
    for field in fields:
        if not isinstance(field, dict):
            continue
        flags = FIELD_FLAGS.get(field.get("key"))
        if not flags:
            continue
        for flag, value in flags.items():
            if field.get(flag) != value:
                field[flag] = value
                changed = True

    keys = {f.get("key") for f in fields if isinstance(f, dict)}
    if "shared_idea" not in keys:
        anchor = next(
            (
                i
                for i, f in enumerate(fields)
                if isinstance(f, dict) and f.get("key") == _ANCHOR_KEY
            ),
            len(fields),
        )
        fields.insert(anchor, dict(SHARED_IDEA_FIELD))
        changed = True

    return schema, changed


def _apply(apps, schema_editor):
    ReflectionTemplate = apps.get_model("core", "ReflectionTemplate")
    for template in ReflectionTemplate.objects.filter(slug=SLUG):
        schema = template.schema
        if not isinstance(schema, dict):
            continue
        schema, changed = _patch_schema(schema)
        if changed:
            template.schema = schema
            template.save(update_fields=["schema"])


def _noop(apps, schema_editor):
    return


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0059_reflection_theme_tagging"),
    ]

    operations = [
        migrations.RunPython(_apply, reverse_code=_noop),
    ]

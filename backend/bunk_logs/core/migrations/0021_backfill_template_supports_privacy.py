"""Backfill ReflectionTemplate.supports_privacy=True for non-self templates.

Step 3.23 introduces ``supports_privacy`` as a template-level gate for the
3.22 per-reflection privacy toggle. The new column ships with a default of
``False`` (the safe option) so any third-party / scripted template create
flow is opt-in. Existing templates that already host peer-authored
reflections need to be flipped on so their authors don't lose the toggle
they had access to before this deploy.

Heuristic: ``subject_mode in {single_subject, multi_subject, group}`` is the
peer-authored case where the toggle is meaningful. ``subject_mode='self'``
stays opt-out -- there's no peer to hide from.

Idempotent: ``.update(supports_privacy=True)`` only flips rows that need it,
so re-running (e.g. via ``--fake`` then real apply) is safe. ``reverse_code``
is a no-op since reverting wouldn't restore the previous state cleanly.
"""

from django.db import migrations


NON_SELF_SUBJECT_MODES = ("single_subject", "multi_subject", "group")


def _backfill_supports_privacy(apps, schema_editor):
    ReflectionTemplate = apps.get_model("core", "ReflectionTemplate")
    ReflectionTemplate.objects.filter(
        subject_mode__in=NON_SELF_SUBJECT_MODES,
    ).exclude(supports_privacy=True).update(supports_privacy=True)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0020_reflectiontemplate_supports_privacy"),
    ]

    operations = [
        migrations.RunPython(
            _backfill_supports_privacy,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

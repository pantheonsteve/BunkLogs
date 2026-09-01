"""Seed ``Person.invited_at`` from invitations already recorded in the audit log.

Until 0064 the only trace of an invitation was an ``AuditEvent`` with
``content_type="person_invitation"``. Without this backfill every person who
was invited before the deploy would read as "never invited", which is exactly
the question the new People screen exists to answer.

Idempotent: only fills rows where ``invited_at`` is still null, so a re-run
(or a re-apply after a rollback) never overwrites a newer real invitation.
"""

from django.db import migrations


def backfill_invited_at(apps, schema_editor):
    Person = apps.get_model("core", "Person")
    AuditEvent = apps.get_model("core", "AuditEvent")

    events = (
        AuditEvent.objects.filter(content_type="person_invitation")
        .order_by("content_id", "-created_at")
        .values_list("content_id", "created_at")
    )
    # Most recent invitation wins; the ordering above puts it first per person.
    latest: dict[str, object] = {}
    for content_id, created_at in events:
        if content_id not in latest:
            latest[content_id] = created_at

    for content_id, created_at in latest.items():
        try:
            person_id = int(content_id)
        except (TypeError, ValueError):
            continue
        Person.objects.filter(pk=person_id, invited_at__isnull=True).update(
            invited_at=created_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0064_alter_assignmentgroup_options_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_invited_at, migrations.RunPython.noop),
    ]

from django.db import migrations

BATCH_SIZE = 500


def copy_counselor_logs_to_staff_logs(apps, schema_editor):
    """Copy all existing CounselorLog rows into the new StaffLog table.

    Preserves PKs so that any external references survive. Skips rows already
    present in bunklogs_stafflog (makes the migration idempotent).

    Rows are inserted in batches of BATCH_SIZE. Because the Migration sets
    atomic = False, each batch is committed immediately rather than being
    held in a single long-lived transaction. This prevents the Postgres
    connection from being dropped on managed-DB environments (e.g. Render)
    when the total copy takes longer than the server's idle-in-transaction
    timeout. A mid-run failure can be retried safely: the existing-ID check
    and bulk_create(ignore_conflicts=True) together ensure idempotency.
    """
    CounselorLog = apps.get_model("bunklogs", "CounselorLog")
    StaffLog = apps.get_model("bunklogs", "StaffLog")

    existing_ids = set(StaffLog.objects.values_list("id", flat=True))

    batch = []
    for cl in CounselorLog.objects.select_related("counselor").iterator():
        if cl.pk in existing_ids:
            continue
        # Note: created_at / updated_at are auto fields; we accept that they
        # will be set to now() rather than the original timestamps because
        # Django does not allow overriding auto_now_add in bulk_create without
        # raw SQL. Historical accuracy of these fields is not required.
        batch.append(
            StaffLog(
                id=cl.pk,
                staff_member_id=cl.counselor_id,
                date=cl.date,
                day_quality_score=cl.day_quality_score,
                support_level_score=cl.support_level_score,
                elaboration=cl.elaboration,
                day_off=cl.day_off,
                staff_care_support_needed=cl.staff_care_support_needed,
                values_reflection=cl.values_reflection,
                is_test_data=cl.is_test_data,
            )
        )
        if len(batch) >= BATCH_SIZE:
            StaffLog.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []

    if batch:
        StaffLog.objects.bulk_create(batch, ignore_conflicts=True)

    # After inserting rows with explicit PKs the Postgres sequence is behind.
    # Advance it so subsequent auto-increment inserts start after the current max.
    schema_editor.execute(
        "SELECT setval("
        "pg_get_serial_sequence('bunklogs_stafflog', 'id'),"
        "COALESCE((SELECT MAX(id) FROM bunklogs_stafflog), 0) + 1,"
        "false"
        ")"
    )


class Migration(migrations.Migration):
    """Copy CounselorLog rows into StaffLog before the old table is dropped.

    atomic = False so Django does not wrap the entire data copy in one
    long-lived transaction. Each batch of BATCH_SIZE rows commits immediately,
    which avoids losing the connection on Render's managed Postgres when the
    operation holds a transaction open longer than the server's
    idle-in-transaction timeout. The migration function is idempotent, so a
    mid-run failure can be retried without data loss or duplication.
    """

    atomic = False

    dependencies = [
        ("bunklogs", "0004_stafflog_schema"),
    ]

    operations = [
        migrations.RunPython(
            copy_counselor_logs_to_staff_logs,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

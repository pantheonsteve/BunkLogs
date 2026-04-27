from django.db import migrations


def copy_counselor_logs_to_staff_logs(apps, schema_editor):
    """Copy all existing CounselorLog rows into the new StaffLog table.

    Uses a single INSERT INTO ... SELECT ... ON CONFLICT DO NOTHING statement
    executed via schema_editor so it runs in autocommit mode (the Migration
    class sets atomic = False). This avoids Django's bulk_create(), which
    internally calls transaction.atomic() and toggles set_autocommit(True/False)
    on the connection — the call that was failing on Render's managed Postgres
    when the server entered recovery mode mid-migration.

    In autocommit mode each schema_editor.execute() call is committed by the
    database engine immediately without any client-side transaction toggling.
    If the connection drops the statement rolls back cleanly, and the retry
    can re-run the whole INSERT safely because ON CONFLICT DO NOTHING is
    idempotent.
    """
    schema_editor.execute("""
        INSERT INTO bunklogs_stafflog (
            id,
            staff_member_id,
            date,
            day_quality_score,
            support_level_score,
            elaboration,
            day_off,
            staff_care_support_needed,
            values_reflection,
            is_test_data,
            created_at,
            updated_at
        )
        SELECT
            id,
            counselor_id,
            date,
            day_quality_score,
            support_level_score,
            elaboration,
            day_off,
            staff_care_support_needed,
            values_reflection,
            is_test_data,
            NOW(),
            NOW()
        FROM bunklogs_counselorlog
        ON CONFLICT DO NOTHING
    """)

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

    atomic = False so Django does not wrap anything in a transaction.
    The data copy runs as a single server-side INSERT...SELECT statement via
    schema_editor.execute(), which commits immediately in autocommit mode
    without any client-side set_autocommit() toggling. This is robust to
    the Render managed-Postgres entering recovery mode mid-build.
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

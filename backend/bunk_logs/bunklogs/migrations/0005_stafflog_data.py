from django.db import migrations


def copy_counselor_logs_to_staff_logs(apps, schema_editor):
    """Copy all existing CounselorLog rows into the new StaffLog table.

    Preserves PKs so that any external references survive. Skips rows already
    present in bunklogs_stafflog (makes the migration idempotent).
    """
    CounselorLog = apps.get_model("bunklogs", "CounselorLog")
    StaffLog = apps.get_model("bunklogs", "StaffLog")

    existing_ids = set(StaffLog.objects.values_list("id", flat=True))

    staff_logs = []
    for cl in CounselorLog.objects.select_related("counselor").iterator():
        if cl.pk in existing_ids:
            continue
        staff_logs.append(StaffLog(
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
            # Note: created_at / updated_at are auto fields; we accept that they
            # will be set to now() rather than the original timestamps because
            # Django does not allow overriding auto_now_add in bulk_create without
            # raw SQL. Historical accuracy of these fields is not required.
        ))

    StaffLog.objects.bulk_create(staff_logs, ignore_conflicts=True)


class Migration(migrations.Migration):
    """Copy CounselorLog rows into StaffLog before the old table is dropped."""

    dependencies = [
        ("bunklogs", "0004_stafflog_schema"),
    ]

    operations = [
        migrations.RunPython(
            copy_counselor_logs_to_staff_logs,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

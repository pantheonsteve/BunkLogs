from django.db import migrations


class Migration(migrations.Migration):
    """Convert CounselorLog to a proxy of StaffLog; register new proxy models.

    After the data migration (0005) all CounselorLog rows live in bunklogs_stafflog.
    This migration:
      1. Deletes the now-empty concrete CounselorLog model (drops its DB table).
      2. Recreates CounselorLog as a proxy of StaffLog (no new DB table).
      3. Adds LeadershipLog and KitchenStaffLog as proxies of StaffLog.
    """

    dependencies = [
        ("bunklogs", "0005_stafflog_data"),
    ]

    operations = [
        # 1. Drop the old concrete CounselorLog table
        migrations.DeleteModel(
            name="CounselorLog",
        ),

        # 2. Recreate CounselorLog as a proxy (no DB table created)
        migrations.CreateModel(
            name="CounselorLog",
            fields=[],
            options={
                "proxy": True,
                "verbose_name": "counselor log",
                "verbose_name_plural": "counselor logs",
                "indexes": [],
                "constraints": [],
            },
            bases=("bunklogs.stafflog",),
        ),

        # 3. New proxy models — zero DB table changes
        migrations.CreateModel(
            name="LeadershipLog",
            fields=[],
            options={
                "proxy": True,
                "verbose_name": "leadership log",
                "verbose_name_plural": "leadership logs",
                "indexes": [],
                "constraints": [],
            },
            bases=("bunklogs.stafflog",),
        ),
        migrations.CreateModel(
            name="KitchenStaffLog",
            fields=[],
            options={
                "proxy": True,
                "verbose_name": "kitchen staff log",
                "verbose_name_plural": "kitchen staff logs",
                "indexes": [],
                "constraints": [],
            },
            bases=("bunklogs.stafflog",),
        ),
    ]

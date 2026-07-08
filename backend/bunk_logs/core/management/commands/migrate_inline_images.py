"""Migrate legacy base64 inline images out of rich-text fields into S3.

The Quill editor used to embed pasted images as ``data:image/...;base64,...``
inside stored HTML, bloating the DB (a handful of rows reached 9-11 MB) and
breaking ``pg_dump``. This one-off command extracts each blob, uploads it as a
:class:`RichTextImage`, and rewrites the ``<img src>`` to the hosted URL.

Scans: StaffLog.elaboration/values_reflection, BunkLog.description,
Reflection.answers (string values).

Safe to run repeatedly: dry-run by default (pass ``--commit`` to write), one
transaction per row, and idempotent (rewritten rows no longer contain
``data:image`` so a second pass is a no-op). Malformed data URIs are skipped,
not deleted. Run as a Render one-off job after a DB backup.
"""

from __future__ import annotations

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.db.models import TextField
from django.db.models.functions import Cast

from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.bunklogs.models import StaffLog
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import RichTextImage
from bunk_logs.core.rich_text import contains_inline_base64_image
from bunk_logs.core.rich_text import replace_inline_images


class Command(BaseCommand):
    help = "Extract base64 inline images from rich-text fields and upload to S3."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Persist changes. Without this flag the command only reports.",
        )

    def handle(self, *args, **options):
        commit = options["commit"]
        self.commit = commit
        mode = "COMMIT" if commit else "DRY-RUN"
        self.stdout.write(f"[migrate_inline_images] mode={mode}")

        totals = {"rows": 0, "images": 0}

        self._process_stafflogs(totals)
        self._process_bunklogs(totals)
        self._process_reflections(totals)

        self.stdout.write(
            self.style.SUCCESS(
                f"[migrate_inline_images] {mode}: {totals['images']} image(s) "
                f"across {totals['rows']} row(s)"
                + ("" if commit else " -- re-run with --commit to apply."),
            ),
        )

    # -- per-image upload -------------------------------------------------

    def _make_uploader(self):
        """Build an ``upload(image) -> url`` callback that persists a RichTextImage."""

        def upload(image) -> str:
            data = image.decode()
            if not self.commit:
                # Dry-run: don't write to storage; a placeholder URL is enough
                # for replace_inline_images to count the replacement.
                return "DRYRUN"
            obj = RichTextImage()
            obj.image.save(f"{obj.id}{image.extension}", ContentFile(data), save=True)
            return obj.image.url

        return upload

    # -- scanners ---------------------------------------------------------

    def _process_stafflogs(self, totals):
        qs = StaffLog.objects.filter(
            Q(elaboration__contains="data:image/")
            | Q(values_reflection__contains="data:image/"),
        )
        for row in qs.iterator():
            changed = 0
            with transaction.atomic():
                for field in ("elaboration", "values_reflection"):
                    value = getattr(row, field) or ""
                    if not contains_inline_base64_image(value):
                        continue
                    new_value, n = replace_inline_images(value, self._make_uploader())
                    if n:
                        setattr(row, field, new_value)
                        changed += n
                if changed and self.commit:
                    # .update() bypasses StaffLog.save()'s full_clean(), which
                    # would reject these legacy rows via the "no logs older than
                    # 30 days" rule. This backfill only swaps base64 for URLs.
                    StaffLog.objects.filter(pk=row.pk).update(
                        elaboration=row.elaboration,
                        values_reflection=row.values_reflection,
                    )
            if changed:
                totals["rows"] += 1
                totals["images"] += changed
                self.stdout.write(f"  StaffLog {row.pk}: {changed} image(s)")

    def _process_bunklogs(self, totals):
        qs = BunkLog.objects.filter(description__contains="data:image/")
        for row in qs.iterator():
            value = row.description or ""
            if not contains_inline_base64_image(value):
                continue
            with transaction.atomic():
                new_value, n = replace_inline_images(value, self._make_uploader())
                if n and self.commit:
                    # .update() bypasses model validation/signals; backfill only.
                    BunkLog.objects.filter(pk=row.pk).update(description=new_value)
            if n:
                totals["rows"] += 1
                totals["images"] += n
                self.stdout.write(f"  BunkLog {row.pk}: {n} image(s)")

    def _process_reflections(self, totals):
        # answers is a JSONField; cast to text so a substring match works
        # reliably across the whole JSON blob.
        qs = (
            Reflection.all_objects.annotate(
                _answers_text=Cast("answers", TextField()),
            )
            .filter(_answers_text__icontains="data:image/")
        )
        for row in qs.iterator():
            answers = row.answers
            if not isinstance(answers, dict):
                continue
            changed = 0
            with transaction.atomic():
                for key, value in list(answers.items()):
                    if not contains_inline_base64_image(value):
                        continue
                    new_value, n = replace_inline_images(value, self._make_uploader())
                    if n:
                        answers[key] = new_value
                        changed += n
                if changed and self.commit:
                    # .update() bypasses model validation/signals; backfill only.
                    Reflection.all_objects.filter(pk=row.pk).update(answers=answers)
            if changed:
                totals["rows"] += 1
                totals["images"] += changed
                self.stdout.write(f"  Reflection {row.pk}: {changed} image(s)")

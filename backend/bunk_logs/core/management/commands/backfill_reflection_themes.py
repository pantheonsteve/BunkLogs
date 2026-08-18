"""Tag existing reflections against the theme taxonomy.

Feeds the admin growth-by-grade dashboard, which is only meaningful once
historical reflections carry theme tags. Re-runs are cheap: reflections that
already have a ``completed`` tagging at the current ``TAXONOMY_VERSION`` are
skipped unless ``--retag`` is passed.

Usage::

    # Dry run: prints how many reflections would be tagged and a token estimate
    python manage.py backfill_reflection_themes --org-slug tbe

    # Enqueue Celery tasks for real
    python manage.py backfill_reflection_themes --org-slug tbe --apply

    # Tag inline instead of via Celery (small batches / no worker running)
    python manage.py backfill_reflection_themes --org-slug tbe --apply --sync

    # Re-tag everything after bumping the taxonomy or fixing a roster grade
    python manage.py backfill_reflection_themes --org-slug tbe --apply --retag

Defaults to a dry run because each reflection costs an LLM call.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionThemeTagging
from bunk_logs.core.theme_tagging.client import estimate_tokens
from bunk_logs.core.theme_tagging.tasks import extract_taggable_items
from bunk_logs.core.theme_tagging.tasks import is_taggable_reflection
from bunk_logs.core.theme_tagging.tasks import tag_reflection_themes
from bunk_logs.core.theme_tagging.taxonomy import TAXONOMY_VERSION

CHUNK_SIZE = 200


def _parse_iso_date(value: str | None) -> date_type | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        msg = f"Invalid date '{value}'. Expected YYYY-MM-DD."
        raise CommandError(msg) from exc


class Command(BaseCommand):
    help = "Tag existing reflections with growth-dashboard themes via Anthropic."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-slug",
            required=True,
            help="Organization slug to backfill (e.g. 'tbe').",
        )
        parser.add_argument(
            "--program-id",
            type=int,
            default=None,
            help="Restrict to a single program.",
        )
        parser.add_argument(
            "--since",
            default=None,
            help="Only reflections with period_start on/after this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after this many reflections.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually tag. Without this flag the command is a dry run.",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run tagging inline instead of enqueueing Celery tasks.",
        )
        parser.add_argument(
            "--retag",
            action="store_true",
            help="Re-tag reflections that already have completed tags.",
        )

    def handle(self, *args, **options):
        org_slug = options["org_slug"]
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist as exc:
            msg = f"No organization with slug '{org_slug}'."
            raise CommandError(msg) from exc

        since = _parse_iso_date(options.get("since"))
        limit = options.get("limit")
        apply_changes = options["apply"]
        run_sync = options["sync"]
        retag = options["retag"]

        with organization_context(org):
            candidates = self._candidates(org, options.get("program_id"), since)
            already_tagged = self._completed_reflection_ids(org)

            selected: list[Reflection] = []
            estimated_tokens = 0
            skipped_untaggable = 0
            skipped_already = 0

            for reflection in candidates.iterator(chunk_size=CHUNK_SIZE):
                if not is_taggable_reflection(reflection):
                    skipped_untaggable += 1
                    continue
                if not retag and reflection.pk in already_tagged:
                    skipped_already += 1
                    continue
                items = extract_taggable_items(reflection)
                if not items:
                    skipped_untaggable += 1
                    continue
                selected.append(reflection)
                estimated_tokens += estimate_tokens(items)
                if limit and len(selected) >= limit:
                    break

            self._report(
                org_slug=org_slug,
                selected=len(selected),
                skipped_untaggable=skipped_untaggable,
                skipped_already=skipped_already,
                estimated_tokens=estimated_tokens,
                retag=retag,
            )

            if not apply_changes:
                self.stdout.write(
                    self.style.WARNING(
                        "Dry run -- nothing tagged. Re-run with --apply to proceed.",
                    ),
                )
                return

            if retag:
                # Drop the old rows so the tagger writes a clean set rather
                # than short-circuiting on the existing completed status.
                ReflectionThemeTagging.all_objects.filter(
                    organization=org,
                    reflection__in=[r.pk for r in selected],
                    taxonomy_version=TAXONOMY_VERSION,
                ).delete()

            self._dispatch(selected, run_sync=run_sync)

    def _candidates(self, org, program_id: int | None, since: date_type | None):
        qs = (
            Reflection.all_objects.filter(organization=org, is_complete=True)
            .select_related("template", "program", "organization")
            .order_by("period_start", "pk")
        )
        if program_id:
            qs = qs.filter(program_id=program_id)
        if since:
            qs = qs.filter(period_start__gte=since)
        return qs

    def _completed_reflection_ids(self, org) -> set[int]:
        return set(
            ReflectionThemeTagging.all_objects.filter(
                organization=org,
                taxonomy_version=TAXONOMY_VERSION,
                status=ReflectionThemeTagging.Status.COMPLETED,
            ).values_list("reflection_id", flat=True),
        )

    def _report(
        self,
        *,
        org_slug: str,
        selected: int,
        skipped_untaggable: int,
        skipped_already: int,
        estimated_tokens: int,
        retag: bool,
    ) -> None:
        self.stdout.write(f"Organization:        {org_slug}")
        self.stdout.write(f"Taxonomy version:    {TAXONOMY_VERSION}")
        self.stdout.write(f"To tag:              {selected}")
        self.stdout.write(f"Skipped (no text):   {skipped_untaggable}")
        if not retag:
            self.stdout.write(f"Skipped (tagged):    {skipped_already}")
        self.stdout.write(
            f"Estimated tokens:    ~{estimated_tokens:,} "
            f"({selected} Anthropic call{'s' if selected != 1 else ''})",
        )

    def _dispatch(self, selected: list[Reflection], *, run_sync: bool) -> None:
        failures = 0
        for reflection in selected:
            if run_sync:
                try:
                    tag_reflection_themes.run(reflection.pk)
                except Exception as exc:
                    # One bad reflection shouldn't abandon the rest of the batch.
                    failures += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"Reflection {reflection.pk} failed: {exc}",
                        ),
                    )
            else:
                tag_reflection_themes.delay(reflection.pk)

        verb = "tagged" if run_sync else "enqueued"
        self.stdout.write(
            self.style.SUCCESS(f"{len(selected) - failures} reflections {verb}."),
        )
        if failures:
            self.stdout.write(self.style.ERROR(f"{failures} failed."))

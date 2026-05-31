"""Converge the three legacy note systems into ``notes.Observation`` (Step 7_23).

Absorbs (one Observation per source row):
  * ``core.SubjectNote``                       — all rows
  * ``core.Note`` (camper_care / specialist)   — subject-anchored typed notes
  * ``notes.Note`` WITH ``camper_reference``   — threaded platform notes about a person

Retires (exported to JSON, NOT migrated):
  * ``notes.Note`` WITHOUT ``camper_reference`` — pure peer-to-peer notes

Leaves alone: ``core.Note`` (maintenance), Orders, MaintenanceTickets, Reflections.

The command is **idempotent** — each source row maps to exactly one Observation
via the ``legacy_source`` provenance key ('<app>.<model>:<pk>'), enforced by a
partial unique constraint, so replays never double-create. It defaults to a
**dry run**; ``--apply`` performs the writes. Runs with ``all_objects`` (no org
context) and prints a per-source reconciliation report + sensitivity histogram.

Usage::

    python manage.py migrate_observations            # dry run, prints plan
    python manage.py migrate_observations --apply     # perform the migration
    python manage.py migrate_observations --apply --export-path /tmp/peer.json
"""

from __future__ import annotations

import json
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from bunk_logs.core.models import Note as CoreNote
from bunk_logs.core.models import SubjectNote
from bunk_logs.notes.models import Note as PlatformNote
from bunk_logs.notes.models import Observation
from bunk_logs.notes.models import ObservationArchive
from bunk_logs.notes.models import ObservationReadReceipt
from bunk_logs.notes.models import ObservationRecipient
from bunk_logs.notes.models import ObservationReply
from bunk_logs.notes.models import ObservationSubject

# SubjectNote.visibility -> Observation.sensitivity (1:1, ordered low->high).
VISIBILITY_TO_SENSITIVITY = {
    "team": Observation.Sensitivity.NORMAL,
    "supervisors_only": Observation.Sensitivity.SENSITIVE,
    "domain_only": Observation.Sensitivity.DOMAIN,
    "admin_only": Observation.Sensitivity.CONFIDENTIAL,
}

_SENSITIVITY_RANK = {
    Observation.Sensitivity.NORMAL: 0,
    Observation.Sensitivity.SENSITIVE: 1,
    Observation.Sensitivity.DOMAIN: 2,
    Observation.Sensitivity.CONFIDENTIAL: 3,
}

DEFAULT_EXPORT_PATH = "observations_retired_peer_notes.json"


def _clamp_at_least(tier: str, floor: str) -> str:
    """Return the higher of two sensitivity tiers."""
    return tier if _SENSITIVITY_RANK[tier] >= _SENSITIVITY_RANK[floor] else floor


def _core_note_sensitivity(note: CoreNote) -> str:
    """camper_care medical/family -> domain; else sensitive if is_sensitive else normal."""
    if note.note_type == CoreNote.NoteType.CAMPER_CARE and note.category in (
        CoreNote.Category.MEDICAL,
        CoreNote.Category.FAMILY,
    ):
        return Observation.Sensitivity.DOMAIN
    if note.is_sensitive:
        return Observation.Sensitivity.SENSITIVE
    return Observation.Sensitivity.NORMAL


def _preserve_timestamps(obs: Observation, created_at, updated_at=None) -> None:
    """Set created_at/updated_at past the auto_now(_add) fields via a raw update."""
    Observation.all_objects.filter(pk=obs.pk).update(
        created_at=created_at,
        updated_at=updated_at or created_at,
    )


class Command(BaseCommand):
    help = "Converge SubjectNote + core.Note(cc/specialist) + notes.Note into Observations (Step 7_23)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist the writes. Without this flag the command is a dry run.",
        )
        parser.add_argument(
            "--export-path",
            default=DEFAULT_EXPORT_PATH,
            help="Where to write the retired peer-note JSON archive (on --apply).",
        )

    def handle(self, *args, **options):
        self.apply = options["apply"]
        self.export_path = options["export_path"]
        self.report: dict[str, dict[str, int]] = {}
        self.sensitivity_hist: Counter = Counter()

        mode = "APPLY" if self.apply else "DRY RUN"
        self.stdout.write(self.style.MIGRATE_HEADING(f"migrate_observations [{mode}]"))

        self._migrate_subject_notes()
        self._migrate_core_notes()
        self._migrate_platform_notes()
        self._export_peer_notes()

        self._print_report()

    # ------------------------------------------------------------------
    # core.SubjectNote
    # ------------------------------------------------------------------
    def _migrate_subject_notes(self) -> None:
        rows = list(SubjectNote.all_objects.all().order_by("pk"))
        created = skipped = 0
        # sn.pk -> Observation (existing or freshly created) for amendment wiring.
        obs_by_sn: dict[int, Observation] = {}

        for sn in rows:
            key = f"core.subjectnote:{sn.pk}"
            existing = Observation.all_objects.filter(legacy_source=key).first()
            if existing is not None:
                obs_by_sn[sn.pk] = existing
                skipped += 1
                continue

            sensitivity = VISIBILITY_TO_SENSITIVITY.get(sn.visibility, Observation.Sensitivity.NORMAL)
            if sn.is_sensitive:
                sensitivity = _clamp_at_least(sensitivity, Observation.Sensitivity.SENSITIVE)
            self.sensitivity_hist[sensitivity] += 1

            if not self.apply:
                created += 1
                continue

            with transaction.atomic():
                obs = Observation.all_objects.create(
                    organization=sn.organization,
                    program=sn.program,
                    author=sn.author_person,
                    author_role_at_write="",
                    body=sn.body,
                    context=sn.context,
                    sensitivity=sensitivity,
                    subject_visible=sn.subject_visible,
                    language="en",
                    legacy_source=key,
                )
                _preserve_timestamps(obs, sn.created_at, sn.updated_at)
                ObservationSubject.objects.create(observation=obs, subject=sn.subject)
            obs_by_sn[sn.pk] = obs
            created += 1

        # Second pass: wire amendment_of chains using the sn->obs map.
        if self.apply:
            for sn in rows:
                if sn.amendment_of_id and sn.pk in obs_by_sn and sn.amendment_of_id in obs_by_sn:
                    child = obs_by_sn[sn.pk]
                    parent = obs_by_sn[sn.amendment_of_id]
                    if child.amendment_of_id != parent.pk:
                        child.amendment_of = parent
                        child.save(update_fields=["amendment_of"])

        self.report["core.SubjectNote"] = {"source": len(rows), "created": created, "skipped": skipped}

    # ------------------------------------------------------------------
    # core.Note (camper_care / specialist)
    # ------------------------------------------------------------------
    def _migrate_core_notes(self) -> None:
        rows = list(
            CoreNote.all_objects.filter(
                note_type__in=[CoreNote.NoteType.CAMPER_CARE, CoreNote.NoteType.SPECIALIST],
            ).order_by("pk"),
        )
        created = skipped = 0

        for note in rows:
            key = f"core.note:{note.pk}"
            if Observation.all_objects.filter(legacy_source=key).exists():
                skipped += 1
                continue

            sensitivity = _core_note_sensitivity(note)
            self.sensitivity_hist[sensitivity] += 1

            if not self.apply:
                created += 1
                continue

            with transaction.atomic():
                obs = Observation.all_objects.create(
                    organization=note.organization,
                    program=note.program,
                    author=note.author,
                    author_role_at_write="",
                    body=note.body,
                    context=note.note_type,
                    sensitivity=sensitivity,
                    subject_visible=False,
                    language=note.language or "en",
                    legacy_source=key,
                )
                _preserve_timestamps(obs, note.created_at, note.updated_at)
                ObservationSubject.objects.create(observation=obs, subject=note.subject)
            created += 1

        self.report["core.Note (cc/specialist)"] = {
            "source": len(rows),
            "created": created,
            "skipped": skipped,
        }

    # ------------------------------------------------------------------
    # notes.Note WITH camper_reference
    # ------------------------------------------------------------------
    def _migrate_platform_notes(self) -> None:
        rows = list(
            PlatformNote.all_objects.filter(camper_reference__isnull=False).order_by("pk"),
        )
        created = skipped = 0

        for note in rows:
            key = f"notes.note:{note.pk}"
            if Observation.all_objects.filter(legacy_source=key).exists():
                skipped += 1
                continue

            self.sensitivity_hist[Observation.Sensitivity.NORMAL] += 1
            # Fold the thread title into the body (decision: prepend, not drop).
            body = f"{note.subject}\n\n{note.body}" if note.subject else note.body

            if not self.apply:
                created += 1
                continue

            with transaction.atomic():
                obs = Observation.all_objects.create(
                    organization=note.organization,
                    program=note.program,
                    author=note.author,
                    author_role_at_write=note.author_role_at_write,
                    body=body,
                    context="",
                    sensitivity=Observation.Sensitivity.NORMAL,
                    subject_visible=False,
                    language="en",
                    source_content_type=note.source_content_type,
                    source_object_id=note.source_object_id,
                    legacy_source=key,
                )
                _preserve_timestamps(obs, note.created_at)
                ObservationSubject.objects.create(observation=obs, subject=note.camper_reference)

                for cap in note.audience_captures.all():
                    ObservationRecipient.objects.get_or_create(
                        observation=obs,
                        person=cap.person,
                        defaults={
                            "option_key": cap.option_key,
                            "bunk_id_at_capture_id": cap.bunk_id_at_capture_id,
                        },
                    )
                for reply in note.replies.all().order_by("created_at"):
                    r = ObservationReply.objects.create(
                        observation=obs,
                        author=reply.author,
                        author_role_at_write=reply.author_role_at_write,
                        body=reply.body,
                    )
                    ObservationReply.objects.filter(pk=r.pk).update(created_at=reply.created_at)
                for receipt in note.read_receipts.all():
                    ObservationReadReceipt.objects.get_or_create(
                        observation=obs,
                        person=receipt.person,
                        defaults={
                            "last_read_at": receipt.last_read_at,
                            "last_read_entry_id": receipt.last_read_entry_id,
                        },
                    )
                for arch in note.archive_entries.all():
                    a, was_created = ObservationArchive.objects.get_or_create(
                        observation=obs,
                        person=arch.person,
                    )
                    if was_created:
                        ObservationArchive.objects.filter(pk=a.pk).update(archived_at=arch.archived_at)
            created += 1

        self.report["notes.Note (w/ subject)"] = {
            "source": len(rows),
            "created": created,
            "skipped": skipped,
        }

    # ------------------------------------------------------------------
    # notes.Note WITHOUT camper_reference -> export, do not migrate
    # ------------------------------------------------------------------
    def _export_peer_notes(self) -> None:
        rows = list(PlatformNote.all_objects.filter(camper_reference__isnull=True).order_by("pk"))
        payload = [
            {
                "id": note.pk,
                "organization_id": note.organization_id,
                "program_id": note.program_id,
                "author_id": note.author_id,
                "author_role_at_write": note.author_role_at_write,
                "subject": note.subject,
                "body": note.body,
                "source_content_type": note.source_content_type,
                "source_object_id": note.source_object_id,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "audience": [
                    {"person_id": c.person_id, "option_key": c.option_key}
                    for c in note.audience_captures.all()
                ],
                "replies": [
                    {
                        "id": rep.pk,
                        "author_id": rep.author_id,
                        "body": rep.body,
                        "created_at": rep.created_at.isoformat() if rep.created_at else None,
                    }
                    for rep in note.replies.all().order_by("created_at")
                ],
            }
            for note in rows
        ]

        if self.apply:
            with open(self.export_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            self.stdout.write(f"  exported {len(payload)} peer notes -> {self.export_path}")

        self.report["notes.Note (peer, RETIRED)"] = {
            "source": len(rows),
            "created": 0,
            "skipped": 0,
            "exported": len(payload),
        }

    # ------------------------------------------------------------------
    def _print_report(self) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("\nReconciliation"))
        for source, counts in self.report.items():
            detail = ", ".join(f"{k}={v}" for k, v in counts.items())
            self.stdout.write(f"  {source}: {detail}")

        self.stdout.write(self.style.MIGRATE_HEADING("\nSensitivity histogram (rows processed)"))
        for tier in Observation.Sensitivity.values:
            self.stdout.write(f"  {tier}: {self.sensitivity_hist.get(tier, 0)}")

        total_obs = Observation.all_objects.exclude(legacy_source="").count()
        self.stdout.write(f"\nObservations with provenance now in DB: {total_obs}")
        if not self.apply:
            self.stdout.write(self.style.WARNING("\nDRY RUN — no changes written. Re-run with --apply."))
        else:
            self.stdout.write(self.style.SUCCESS("\nDone."))

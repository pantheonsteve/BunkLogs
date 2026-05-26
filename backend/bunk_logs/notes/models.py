"""Notes platform models (Step 7_19, Stories 66-70).

Five models form the notes data layer:

  Note              — the root message (author, audience, body, optional camper/source refs)
  NoteAudienceCapture — audit-captured resolved audience, one row per Person per Note
  NoteReply         — threaded replies; no edit, per decision N8
  NoteReadReceipt   — per-person last-read watermark, drives the unread badge
  NoteArchive       — through model for Note.archived_by M2M (per-user archive, decision N9)

Invariants:
  * Every Note belongs to an organization (org-scoped via OrgScopedManager).
  * Audience is captured at write-time (NoteAudienceCapture rows); membership
    changes after submission do NOT affect who can read the note.
  * Archive is per-user; archived notes are never deleted from the system.
"""

from __future__ import annotations

from django.db import models

from bunk_logs.core.managers import OrgScopedManager
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program


class Note(models.Model):
    """A standalone threaded note composed by one Person and addressed to an explicit audience."""

    SOURCE_TYPES = [
        ("reflection_concern", "Reflection concern"),
        ("specialist_note", "Specialist note"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="platform_notes",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="platform_notes",
    )
    author = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="authored_platform_notes",
    )
    # The Membership role the author held at submission — for audit and display.
    author_role_at_write = models.CharField(max_length=32)
    subject = models.CharField(max_length=200)
    body = models.TextField(max_length=10000)
    camper_reference = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referenced_in_platform_notes",
    )
    # Source cross-reference (Stories 69, 70). Uses CharField so we can hold
    # both integer Reflection PKs and any future UUID-keyed source types.
    source_content_type = models.CharField(
        max_length=32,
        choices=SOURCE_TYPES,
        blank=True,
        default="",
    )
    source_object_id = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.ManyToManyField(
        Person,
        through="NoteArchive",
        related_name="archived_platform_notes",
        blank=True,
    )

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["author", "created_at"], name="notes_note_author_created_idx"),
            models.Index(
                fields=["source_content_type", "source_object_id"],
                name="notes_note_source_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Note({self.id}): {self.subject[:40]}"


class NoteAudienceCapture(models.Model):
    """Audit-captured audience — one row per resolved Person per Note.

    Written at submission time; never modified. The inbox visibility query
    joins through this table (person, note).
    """

    note = models.ForeignKey(
        Note,
        on_delete=models.CASCADE,
        related_name="audience_captures",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="note_audience_captures",
    )
    option_key = models.CharField(max_length=64)
    # Populated for bunk-scoped options so we know which bunk context this resolved from.
    bunk_id_at_capture = models.ForeignKey(
        "core.AssignmentGroup",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        indexes = [
            models.Index(fields=["person", "note"], name="notes_audience_person_note_idx"),
        ]

    def __str__(self) -> str:
        return f"NoteAudienceCapture(note={self.note_id}, person={self.person_id})"


class NoteReply(models.Model):
    """A reply to a Note thread. No edit after creation (decision N8)."""

    note = models.ForeignKey(
        Note,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    author = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="note_replies",
    )
    author_role_at_write = models.CharField(max_length=32)
    body = models.TextField(max_length=10000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["note", "created_at"], name="notes_reply_note_created_idx"),
        ]

    def __str__(self) -> str:
        return f"NoteReply({self.id}) on note {self.note_id}"


class NoteReadReceipt(models.Model):
    """Tracks the last time a Person read a note thread."""

    note = models.ForeignKey(
        Note,
        on_delete=models.CASCADE,
        related_name="read_receipts",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="note_read_receipts",
    )
    last_read_at = models.DateTimeField()
    # ID of the most recent Note or NoteReply the person had visibility to at
    # last_read_at. UUID to accommodate both integer Note PKs and any future
    # UUID-keyed entries (stored as string for flexibility).
    last_read_entry_id = models.CharField(max_length=50)

    class Meta:
        unique_together = [("note", "person")]
        indexes = [
            models.Index(fields=["person", "note"], name="notes_receipt_person_note_idx"),
        ]

    def __str__(self) -> str:
        return f"NoteReadReceipt(note={self.note_id}, person={self.person_id})"


class NoteArchive(models.Model):
    """Through model for Note.archived_by (per-user archive, decision N9)."""

    note = models.ForeignKey(
        Note,
        on_delete=models.CASCADE,
        related_name="archive_entries",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="note_archive_entries",
    )
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("note", "person")]

    def __str__(self) -> str:
        return f"NoteArchive(note={self.note_id}, person={self.person_id})"

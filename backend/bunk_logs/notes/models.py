"""Observations models (Step 7_23).

Legacy note families (notes.Note, core.Note camper-care/specialist,
core.SubjectNote) were removed in Step 7_24; this app holds the converged
Observation entity and satellites.
"""

from __future__ import annotations

from django.db import models

from bunk_logs.core.managers import OrgScopedManager
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program


class Observation(models.Model):
    """A subject-anchored, threaded, sensitivity-gated observation."""

    class Sensitivity(models.TextChoices):
        # Ordered tiers (low → high). Mapped 1:1 from the legacy SubjectNote
        # visibility enum: team→normal, supervisors_only→sensitive,
        # domain_only→domain, admin_only→confidential.
        NORMAL = "normal", "Normal"
        SENSITIVE = "sensitive", "Sensitive"
        DOMAIN = "domain", "Domain"
        CONFIDENTIAL = "confidential", "Confidential"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="observations",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="observations",
    )
    author = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_observations",
        help_text="Writer. Nullable to preserve the immutable record if the Person is removed.",
    )
    # Membership role the author held at submission — for audit and display.
    author_role_at_write = models.CharField(max_length=32, blank=True, default="")
    subjects = models.ManyToManyField(
        Person,
        through="ObservationSubject",
        related_name="observations_about",
        blank=True,
    )
    body = models.TextField(max_length=10000)
    context = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Org-configurable context tag carried from SubjectNote (e.g. 'camper_care', 'swim_instruction').",
    )
    sensitivity = models.CharField(
        max_length=32,
        choices=Sensitivity.choices,
        default=Sensitivity.NORMAL,
    )
    subject_visible = models.BooleanField(
        default=False,
        help_text="When True, a tagged subject can see this observation on their own Profile.",
    )
    language = models.CharField(
        max_length=10,
        choices=Person.LANGUAGE_CHOICES,
        default="en",
    )
    amendment_of = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="amendments",
        help_text="Set when this observation amends an earlier one. Original is immutable.",
    )
    # Cross-reference to the originating content (reflection concern, specialist
    # note, …) — carried from notes.Note.
    source_content_type = models.CharField(max_length=32, blank=True, default="")
    source_object_id = models.CharField(max_length=50, blank=True, default="")
    # Provenance key '<app_label>.<model>:<pk>' for rows created by the
    # migrate_observations command. Blank for API-created observations. The
    # partial unique constraint below makes the migration idempotent.
    legacy_source = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_by = models.ManyToManyField(
        Person,
        through="ObservationArchive",
        related_name="archived_observations",
        blank=True,
    )

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["legacy_source"],
                condition=~models.Q(legacy_source=""),
                name="obs_unique_legacy_source",
            ),
        ]
        indexes = [
            models.Index(fields=["author", "created_at"], name="obs_author_created_idx"),
            models.Index(
                fields=["source_content_type", "source_object_id"],
                name="obs_source_idx",
            ),
            models.Index(
                fields=["organization", "sensitivity", "created_at"],
                name="obs_org_sens_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Observation({self.id})" if self.pk else "Observation (unsaved)"

    def _audit_content_type_label(self) -> str:
        return "observation"


class ObservationSubject(models.Model):
    """Through table for Observation.subjects (the Persons an observation is about)."""

    observation = models.ForeignKey(
        Observation,
        on_delete=models.CASCADE,
        related_name="subject_links",
    )
    subject = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="observation_subject_links",
    )

    class Meta:
        unique_together = [("observation", "subject")]
        indexes = [
            models.Index(fields=["subject", "observation"], name="obs_subject_subj_obs_idx"),
        ]

    def __str__(self) -> str:
        return f"ObservationSubject(obs={self.observation_id}, subject={self.subject_id})"


class ObservationRecipient(models.Model):
    """Write-time captured recipient — one row per tagged Person per observation.

    Write-time captured recipients (keeps ``option_key``) so the audit story and
    any future role-matrix tagging carry over. Drives the inbox + the
    tagged-recipient read leg.
    """

    observation = models.ForeignKey(
        Observation,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="observation_recipiencies",
    )
    option_key = models.CharField(max_length=64, blank=True, default="")
    bunk_id_at_capture = models.ForeignKey(
        "core.AssignmentGroup",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        unique_together = [("observation", "person")]
        indexes = [
            models.Index(fields=["person", "observation"], name="obs_recip_person_obs_idx"),
        ]

    def __str__(self) -> str:
        return f"ObservationRecipient(obs={self.observation_id}, person={self.person_id})"


class ObservationReply(models.Model):
    """A reply to an observation thread. No edit after creation."""

    observation = models.ForeignKey(
        Observation,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    author = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="observation_replies",
    )
    author_role_at_write = models.CharField(max_length=32)
    body = models.TextField(max_length=10000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["observation", "created_at"], name="obs_reply_obs_created_idx"),
        ]

    def __str__(self) -> str:
        return f"ObservationReply({self.id}) on observation {self.observation_id}"


class ObservationReadReceipt(models.Model):
    """Tracks the last time a Person read an observation thread."""

    observation = models.ForeignKey(
        Observation,
        on_delete=models.CASCADE,
        related_name="read_receipts",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="observation_read_receipts",
    )
    last_read_at = models.DateTimeField()
    last_read_entry_id = models.CharField(max_length=50)

    class Meta:
        unique_together = [("observation", "person")]
        indexes = [
            models.Index(fields=["person", "observation"], name="obs_receipt_person_obs_idx"),
        ]

    def __str__(self) -> str:
        return f"ObservationReadReceipt(obs={self.observation_id}, person={self.person_id})"


class ObservationArchive(models.Model):
    """Through model for Observation.archived_by (per-user archive)."""

    observation = models.ForeignKey(
        Observation,
        on_delete=models.CASCADE,
        related_name="archive_entries",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="observation_archive_entries",
    )
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("observation", "person")]

    def __str__(self) -> str:
        return f"ObservationArchive(obs={self.observation_id}, person={self.person_id})"

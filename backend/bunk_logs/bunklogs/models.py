from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from bunk_logs.utils.models import TestDataMixin


class BunkLog(TestDataMixin):
    """Daily report for each camper."""

    bunk_assignment = models.ForeignKey(
        "campers.CamperBunkAssignment",
        on_delete=models.PROTECT,  # Don't allow deleting assignment if logs exist
        related_name="bunk_logs",
    )
    date = models.DateField()
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_logs",
    )

    not_on_camp = models.BooleanField(default=False)

    # Scores (1-5 scale)
    social_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    behavior_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    participation_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )

    # Status flags
    request_camper_care_help = models.BooleanField(default=False)
    request_unit_head_help = models.BooleanField(default=False)

    # Details
    description = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("bunk log")
        verbose_name_plural = _("bunk logs")
        unique_together = ("bunk_assignment", "date")
        ordering = ["-date"]
        app_label = "bunklogs"

    def __str__(self):
        return f"Log for {self.bunk_assignment.camper} on {self.date}"

    @property
    def camper(self):
        """Property to maintain compatibility with existing code."""
        return self.bunk_assignment.camper

    def save(self, *args, **kwargs):
        """Override save method to set date for new records only."""
        # For new records, set date based on local timezone at creation time
        # For existing records, preserve any manually set dates
        if not self.pk:
            # Get the current local time for new records
            local_now = timezone.localtime()
            self.date = local_now.date()
        
        # Call parent save - allow manual date changes for existing records
        super().save(*args, **kwargs)


class CounselorLog(TestDataMixin):
    """Daily personal reflection log for counselors."""

    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="counselor_logs",
        limit_choices_to={"role": "Counselor"},
    )
    date = models.DateField()

    # Day quality (1-5 scale)
    day_quality_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="How was your day? (1 = terrible, 5 = best day ever)",
    )

    # Support level (1-5 scale)
    support_level_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="How supported did you feel today? (1 = unsupported, 5 = fully supported)",
    )

    # Elaboration on scores
    elaboration = models.TextField(
        help_text="Elaborate on why - positive or negative (providing more information about questions 1 and 2)"
    )

    # Day off status
    day_off = models.BooleanField(
        default=False,
        help_text="Check if you are on a day off today"
    )

    # Staff care/engagement support request
    staff_care_support_needed = models.BooleanField(
        default=False,
        help_text="Check if you would like staff care/engagement support"
    )

    # Values reflection
    values_reflection = models.TextField(
        help_text="How did the bunk exemplify our values today?"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("counselor log")
        verbose_name_plural = _("counselor logs")
        unique_together = ("counselor", "date")
        ordering = ["-date"]
        app_label = "bunklogs"

    def __str__(self):
        return f"Counselor log for {self.counselor.get_full_name()} on {self.date}"

    def save(self, *args, **kwargs):
        """Override save method to set date for new records only."""
        # For new records, set date based on local timezone at creation time
        # For existing records, preserve any manually set dates
        if not self.pk:
            # Get the current local time for new records
            local_now = timezone.localtime()
            self.date = local_now.date()
        
        # Call parent save - allow manual date changes for existing records
        super().save(*args, **kwargs)

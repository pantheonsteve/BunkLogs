from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

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

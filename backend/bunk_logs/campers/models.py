from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from bunk_logs.bunks.models import Bunk
from bunk_logs.utils.models import TestDataMixin


class Camper(TestDataMixin):
    """Camper information."""

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    camper_notes = models.TextField(blank=True)
    parent_notes = models.TextField(blank=True)

    # Current status
    status_note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("camper")
        verbose_name_plural = _("campers")
        ordering = ["last_name", "first_name"]
        app_label = "campers"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        if not self.date_of_birth:
            return 0
        today = datetime.now(tz=timezone.get_current_timezone()).date()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )


class CamperBunkAssignment(TestDataMixin):
    """Assignment of campers to bunks for a specific session."""

    # Add error message constant
    BUNK_LOGS_DELETE_ERROR = "Cannot delete bunk assignment with associated bunk logs."
    OVERLAPPING_ASSIGNMENT_ERROR = "Camper already has an active bunk assignment during this period."

    camper = models.ForeignKey(
        Camper,
        on_delete=models.CASCADE,
        related_name="bunk_assignments",
    )
    bunk = models.ForeignKey(
        Bunk,
        on_delete=models.CASCADE,
        related_name="camper_assignments",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("camper bunk assignment")
        verbose_name_plural = _("camper bunk assignments")
        # Removed unique_together constraint to allow multiple assignments with different dates
        app_label = "campers"

    def __str__(self):
        return f"{self.camper} in {self.bunk.name}"

    def clean(self):
        # Validate that dates are logical
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("End date cannot be before start date.")
            
        # Check for overlapping assignments
        if self.is_active or (self.start_date and self.end_date):
            overlapping_assignments = CamperBunkAssignment.objects.filter(
                camper=self.camper,
                is_active=True,
            )
            
            # Exclude current instance if it exists (for updates)
            if self.pk:
                overlapping_assignments = overlapping_assignments.exclude(pk=self.pk)
                
            # Check date-based overlaps if dates are provided
            if self.start_date and self.end_date:
                date_overlaps = CamperBunkAssignment.objects.filter(
                    camper=self.camper,
                    start_date__lte=self.end_date,
                    end_date__gte=self.start_date
                )
                
                if self.pk:
                    date_overlaps = date_overlaps.exclude(pk=self.pk)
                    
                if date_overlaps.exists():
                    raise ValidationError(self.OVERLAPPING_ASSIGNMENT_ERROR)
                    
            # If we're setting this as active, ensure no other active assignments exist
            if self.is_active and overlapping_assignments.exists():
                raise ValidationError("Camper already has an active bunk assignment.")

    def save(self, *args, **kwargs):
        # Automatically set start and end dates based on the session of the bunk
        if not self.start_date and self.bunk and self.bunk.session:
            self.start_date = self.bunk.session.start_date
        if not self.end_date and self.bunk and self.bunk.session:
            self.end_date = self.bunk.session.end_date
            
        # Run validation
        self.clean()
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Check for associated bunk logs before deletion
        from bunk_logs.bunklogs.models import BunkLog  # Changed to match the import used in admin.py
        if BunkLog.objects.filter(bunk_assignment=self).exists():
            raise ValidationError(self.BUNK_LOGS_DELETE_ERROR)
        super().delete(*args, **kwargs)

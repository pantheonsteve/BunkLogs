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

    @property
    def overall_score(self):
        """Calculate average score, excluding null values."""
        scores = [s for s in [self.social_score, self.behavior_score, self.participation_score] if s is not None]
        return round(sum(scores) / len(scores), 1) if scores else None

    @property
    def needs_attention(self):
        """Returns True if any score is 2 or below, or help is requested."""
        if self.not_on_camp:
            return False
        
        low_scores = any(score and score <= 2 for score in [self.social_score, self.behavior_score, self.participation_score])
        return low_scores or self.request_camper_care_help or self.request_unit_head_help

    @property
    def is_complete(self):
        """Returns True if the log has all required information."""
        if self.not_on_camp:
            return True  # No scores needed if not on camp
        
        # At least one score should be provided
        has_scores = any(score is not None for score in [self.social_score, self.behavior_score, self.participation_score])
        return has_scores

    def can_edit(self, user):
        """Business rule: who can edit this log."""
        # Original counselor can edit
        if self.counselor == user:
            return True
        
        # Users with change permission can edit (admins, managers)
        if user.has_perm('bunklogs.change_bunklog'):
            return True
        
        return False

    def get_score_summary(self):
        """Get a human-readable summary of scores."""
        if self.not_on_camp:
            return "Not on camp"
        
        scores = []
        if self.social_score:
            scores.append(f"Social: {self.social_score}")
        if self.behavior_score:
            scores.append(f"Behavior: {self.behavior_score}")
        if self.participation_score:
            scores.append(f"Participation: {self.participation_score}")
        
        if scores:
            avg = self.overall_score
            return f"{', '.join(scores)} (Avg: {avg})" if avg else ', '.join(scores)
        
        return "No scores recorded"

    def clean(self):
        """Validate the log data."""
        from django.core.exceptions import ValidationError
        from datetime import timedelta
        
        super().clean()
        
        if self.date:
            today = timezone.localtime().date()
            
            # Prevent future dates (unless admin override)
            if self.date > today:
                raise ValidationError({
                    'date': 'Cannot create logs for future dates.'
                })
            
            # Prevent very old dates (business rule - adjust as needed)
            max_days_back = 30
            if self.date < (today - timedelta(days=max_days_back)):
                raise ValidationError({
                    'date': f'Cannot create logs older than {max_days_back} days.'
                })
        
        # Validate bunk assignment is active for the log date
        if self.bunk_assignment_id and self.date:
            # Note: This assumes your CamperBunkAssignment has start_date/end_date fields
            # Adjust field names based on your actual model
            if hasattr(self.bunk_assignment, 'start_date') and self.bunk_assignment.start_date:
                if self.date < self.bunk_assignment.start_date:
                    raise ValidationError({
                        'date': f'Cannot create log before camper assignment start date ({self.bunk_assignment.start_date}).'
                    })
            
            if hasattr(self.bunk_assignment, 'end_date') and self.bunk_assignment.end_date:
                if self.date > self.bunk_assignment.end_date:
                    raise ValidationError({
                        'date': f'Cannot create log after camper assignment end date ({self.bunk_assignment.end_date}).'
                    })
        
        # If camper is marked as "not on camp", scores should not be provided
        if self.not_on_camp:
            score_errors = {}
            if self.social_score is not None:
                score_errors['social_score'] = 'Cannot score a camper who was not on camp.'
            if self.behavior_score is not None:
                score_errors['behavior_score'] = 'Cannot score a camper who was not on camp.'
            if self.participation_score is not None:
                score_errors['participation_score'] = 'Cannot score a camper who was not on camp.'
            
            if score_errors:
                raise ValidationError(score_errors)
        
        # If camper was on camp, at least one score should be provided (business rule)
        else:
            if (self.social_score is None and 
                self.behavior_score is None and 
                self.participation_score is None):
                raise ValidationError({
                    '__all__': 'At least one score must be provided for campers who were on camp.'
                })
        
        # If requesting help, description should be provided
        if (self.request_camper_care_help or self.request_unit_head_help) and not self.description.strip():
            raise ValidationError({
                'description': 'Description is required when requesting help from camper care or unit head.'
            })

    def save(self, *args, **kwargs):
        """Override save method to set default date for new records."""
        # For new records without a date, use today's date
        if not self.pk and not self.date:
            self.date = timezone.localtime().date()
        
        # Run validation
        self.full_clean()
        
        # Call parent save - let unique constraint handle duplicates
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

    @property
    def overall_wellbeing_score(self):
        """Calculate average of day quality and support level."""
        return round((self.day_quality_score + self.support_level_score) / 2, 1)

    @property
    def needs_support(self):
        """Returns True if counselor seems to need support based on scores or explicit request."""
        low_scores = self.day_quality_score <= 2 or self.support_level_score <= 2
        return low_scores or self.staff_care_support_needed

    @property
    def current_bunk_assignments(self):
        """Get the counselor's current bunk assignments for the log date."""
        from bunk_logs.bunks.models import CounselorBunkAssignment
        
        # Get all bunk assignments that were active on the log date
        assignments = CounselorBunkAssignment.objects.filter(
            counselor=self.counselor,
            start_date__lte=self.date,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=self.date)
        ).select_related('bunk', 'bunk__unit', 'bunk__cabin', 'bunk__session').order_by('-is_primary', '-start_date')
        
        return assignments

    @property
    def bunk_names(self):
        """Get comma-separated string of bunk names for this counselor on the log date."""
        assignments = self.current_bunk_assignments
        if not assignments:
            return "No bunk assignment"
        
        bunk_names = []
        for assignment in assignments:
            name = assignment.bunk.name
            if assignment.is_primary:
                name += " (Primary)"
            bunk_names.append(name)
        
        return ", ".join(bunk_names)

    def can_edit(self, user):
        """Business rule: who can edit this counselor log."""
        # Original counselor can edit their own log
        if self.counselor == user:
            return True
        
        # Users with change permission can edit (admins, camp directors)
        if user.has_perm('bunklogs.change_counselorlog'):
            return True
        
        return False

    def get_wellbeing_summary(self):
        """Get a human-readable summary of wellbeing."""
        day_labels = {1: "Terrible", 2: "Poor", 3: "Okay", 4: "Good", 5: "Excellent"}
        support_labels = {1: "Unsupported", 2: "Poorly supported", 3: "Adequately supported", 4: "Well supported", 5: "Fully supported"}
        
        day_desc = day_labels.get(self.day_quality_score, "Unknown")
        support_desc = support_labels.get(self.support_level_score, "Unknown")
        
        if self.day_off:
            return f"Day off - Day: {day_desc}, Support: {support_desc}"
        
        return f"Day: {day_desc}, Support: {support_desc} (Avg: {self.overall_wellbeing_score})"

    def clean(self):
        """Validate the counselor log data."""
        from django.core.exceptions import ValidationError
        from datetime import timedelta
        
        super().clean()
        
        if self.date:
            today = timezone.localtime().date()
            
            # Prevent future dates (unless admin override)
            if self.date > today:
                raise ValidationError({
                    'date': 'Cannot create logs for future dates.'
                })
            
            # Prevent very old dates (business rule - adjust as needed)
            max_days_back = 30
            if self.date < (today - timedelta(days=max_days_back)):
                raise ValidationError({
                    'date': f'Cannot create logs older than {max_days_back} days.'
                })
        
        # If on day off, certain fields should be handled differently
        if self.day_off:
            # Day off logs might have different validation rules
            # For example, values_reflection might not be required on day off
            pass
        else:
            # If not on day off, ensure all reflection fields are filled
            if not self.elaboration.strip():
                raise ValidationError({
                    'elaboration': 'Elaboration is required for work days.'
                })
            
            if not self.values_reflection.strip():
                raise ValidationError({
                    'values_reflection': 'Values reflection is required for work days.'
                })
        
        # If requesting staff care support, elaboration should explain why
        if self.staff_care_support_needed and not self.elaboration.strip():
            raise ValidationError({
                'elaboration': 'Please explain why you need staff care support in the elaboration field.'
            })

    def save(self, *args, **kwargs):
        """Override save method to set default date for new records."""
        # For new records without a date, use today's date
        if not self.pk and not self.date:
            self.date = timezone.localtime().date()
        
        # Run validation
        self.full_clean()
        
        # Call parent save - let unique constraint handle duplicates
        super().save(*args, **kwargs)

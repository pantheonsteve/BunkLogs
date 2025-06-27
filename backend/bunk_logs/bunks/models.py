from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from bunk_logs.utils.models import TestDataMixin


class Cabin(TestDataMixin):
    """Physical location for a bunk."""

    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = _("cabin")
        verbose_name_plural = _("cabins")
        app_label = "bunks"

    def __str__(self):
        return self.name


class Session(TestDataMixin):
    """Camp session period."""

    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("session")
        verbose_name_plural = _("sessions")
        app_label = "bunks"

    def __str__(self):
        return f"{self.name}"


class UnitStaffAssignment(models.Model):
    """Staff assignment to units with specific roles."""

    ROLE_CHOICES = [
        ("unit_head", "Unit Head"),
        ("camper_care", "Camper Care"),
    ]

    unit = models.ForeignKey(
        "Unit", on_delete=models.CASCADE, related_name="staff_assignments"
    )
    staff_member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unit_assignments"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_primary = models.BooleanField(default=False)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("unit staff assignment")
        verbose_name_plural = _("unit staff assignments")
        unique_together = [("unit", "staff_member", "role")]
        app_label = "bunks"

    def __str__(self):
        return f"{self.unit.name} - {self.staff_member.get_full_name()} ({self.get_role_display()})"


class CounselorBunkAssignment(TestDataMixin):
    """Assignment of counselors to bunks with date tracking."""

    # Add error message constants
    OVERLAPPING_ASSIGNMENT_ERROR = "Counselor already has an active bunk assignment during this period."

    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bunk_assignments",
        limit_choices_to={"role": "Counselor"},
    )
    bunk = models.ForeignKey(
        "Bunk",
        on_delete=models.CASCADE,
        related_name="counselor_assignments",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(
        default=False,
        help_text="Is this counselor the primary counselor for this bunk?"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("counselor bunk assignment")
        verbose_name_plural = _("counselor bunk assignments")
        ordering = ["-start_date", "-is_primary"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F("start_date")),
                name="valid_date_range_counselor_bunk"
            )
        ]
        app_label = "bunks"

    def __str__(self):
        end_str = f" - {self.end_date}" if self.end_date else " - Present"
        primary_str = " (Primary)" if self.is_primary else ""
        return f"{self.counselor.get_full_name()} -> {self.bunk.name} ({self.start_date}{end_str}){primary_str}"

    @property
    def is_active(self):
        """Check if this assignment is currently active"""
        today = timezone.now().date()
        return self.start_date <= today and (self.end_date is None or self.end_date >= today)

    def clean(self):
        """Validate the assignment"""
        # Validate that dates are logical
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("End date cannot be before start date.")

        # Check for overlapping assignments if we're setting this as primary
        if self.is_primary:
            overlapping_primary = CounselorBunkAssignment.objects.filter(
                bunk=self.bunk,
                is_primary=True,
            )

            # Exclude current instance if it exists (for updates)
            if self.pk:
                overlapping_primary = overlapping_primary.exclude(pk=self.pk)

            # Check for active overlaps
            for assignment in overlapping_primary:
                if assignment.is_active:
                    # Check if our date range overlaps with this active assignment
                    their_end = assignment.end_date or timezone.now().date()
                    our_end = self.end_date or timezone.now().date()
                    
                    if (self.start_date <= their_end and our_end >= assignment.start_date):
                        raise ValidationError("Another counselor is already the primary for this bunk during this period.")

    def save(self, *args, **kwargs):
        # Run validation
        self.clean()
        super().save(*args, **kwargs)


class Unit(TestDataMixin):
    """Group of bunks managed by unit heads."""

    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("unit")
        verbose_name_plural = _("units")
        app_label = "bunks"

    def __str__(self):
        return f"{self.name}"

    @property
    def primary_unit_head(self):
        """Get the primary unit head from staff assignments."""
        assignment = self.staff_assignments.filter(
            role="unit_head",
            is_primary=True,
            start_date__lte=timezone.now().date(),
            end_date__isnull=True,
        ).first()
        return assignment.staff_member if assignment else None

    @property
    def primary_camper_care(self):
        """Get the primary camper care from staff assignments."""
        assignment = self.staff_assignments.filter(
            role="camper_care",
            is_primary=True,
            start_date__lte=timezone.now().date(),
            end_date__isnull=True,
        ).first()
        return assignment.staff_member if assignment else None

    @property
    def all_unit_heads(self):
        """Get all active unit heads."""
        assignments = self.staff_assignments.filter(
            role="unit_head",
            start_date__lte=timezone.now().date(),
            end_date__isnull=True,
        ).select_related("staff_member")
        return [a.staff_member for a in assignments]

    @property
    def all_camper_care(self):
        """Get all active camper care staff."""
        assignments = self.staff_assignments.filter(
            role="camper_care",
            start_date__lte=timezone.now().date(),
            end_date__isnull=True,
        ).select_related("staff_member")
        return [a.staff_member for a in assignments]

    @property
    def unit_heads(self):
        """Alias for all_unit_heads for API compatibility."""
        return self.all_unit_heads

    @property
    def camper_care_staff(self):
        """Alias for all_camper_care for API compatibility."""
        return self.all_camper_care


class Bunk(TestDataMixin):
    """Group of campers assigned to counselors for a session."""

    cabin = models.ForeignKey(
        Cabin,
        on_delete=models.SET_NULL,
        null=True,
        related_name="bunks",
    )
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="bunks")
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        related_name="bunks",
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("bunk")
        verbose_name_plural = _("bunks")
        unique_together = ("cabin", "session")
        app_label = "bunks"

    def __str__(self):
        return self.name

    @property
    def name(self):
        if self.cabin and self.session:
            return f"{self.cabin.name} - {self.session.name}"
        if self.cabin:
            return f"{self.cabin.name} - (No Session)"
        if self.session:
            return f"(No Cabin) - {self.session.name}"
        return "(Undefined Bunk)"

    def get_current_counselors(self):
        """Get all currently assigned counselors"""
        today = timezone.now().date()
        return [
            assignment.counselor 
            for assignment in self.counselor_assignments.filter(
                start_date__lte=today
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
            ).order_by("-is_primary", "-start_date")
        ]
    
    def get_primary_counselor(self):
        """Get the primary counselor for this bunk"""
        today = timezone.now().date()
        primary_assignment = self.counselor_assignments.filter(
            start_date__lte=today,
            is_primary=True
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
        ).first()
        
        return primary_assignment.counselor if primary_assignment else None
    
    def assign_counselor(self, counselor, start_date=None, end_date=None, is_primary=False):
        """Assign a counselor to this bunk"""
        if start_date is None:
            start_date = timezone.now().date()
        
        return CounselorBunkAssignment.objects.create(
            counselor=counselor,
            bunk=self,
            start_date=start_date,
            end_date=end_date,
            is_primary=is_primary
        )
    
    @property
    def counselor(self):
        """Backward compatibility property - returns primary counselor"""
        return self.get_primary_counselor()

    @property  
    def current_counselors(self):
        """Property for current counselors list"""
        return self.get_current_counselors()

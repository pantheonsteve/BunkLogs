from django.conf import settings
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
    counselors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        limit_choices_to={"role": "Counselor"},
        related_name="assigned_bunks",
    )
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

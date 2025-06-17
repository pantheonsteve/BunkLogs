from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Cabin(models.Model):
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


class Session(models.Model):
    """Camp session period."""

    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("session")
        verbose_name_plural = _("sessions")

    def __str__(self):
        return f"{self.name}"


class Unit(models.Model):
    """Group of bunks managed by a unit head."""

    name = models.CharField(max_length=100)
    unit_head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        limit_choices_to={"role": "Unit Head"},
        on_delete=models.SET_NULL,
        null=True,
        related_name="managed_units",
    )
    camper_care = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        limit_choices_to={"role": "Camper Care"},
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="camper_care_units",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("unit")
        verbose_name_plural = _("units")

    def __str__(self):
        return f"{self.name}"


class Bunk(models.Model):
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

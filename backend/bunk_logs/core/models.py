from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.db.models import Q


class Organization(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Program(models.Model):
    PROGRAM_TYPES = [
        ("summer_camp", "Summer Camp"),
        ("religious_school", "Religious School"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="programs",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    program_type = models.CharField(max_length=32, choices=PROGRAM_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("organization", "slug")]
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                check=Q(end_date__gte=F("start_date")),
                name="core_program_end_date_gte_start_date",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End date must be on or after start date."},
            )


class Person(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="persons",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    preferred_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="person_record",
    )
    external_ids = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.preferred_name or self.first_name} {self.last_name}"


class Membership(models.Model):
    ROLES = [
        ("camper", "Camper"),
        ("counselor", "Counselor"),
        ("junior_counselor", "Junior Counselor"),
        ("specialist", "Specialist"),
        ("general_counselor", "General Counselor"),
        ("unit_head", "Unit Head"),
        ("leadership_team", "Leadership Team"),
        ("kitchen_staff", "Kitchen Staff"),
        ("maintenance", "Maintenance"),
        ("housekeeping", "Housekeeping"),
        ("camper_care", "Camper Care"),
        ("health_center", "Health Center"),
        ("special_diets", "Special Diets"),
        ("madrich", "Madrich"),
        ("faculty", "Faculty"),
        ("admin", "Admin"),
    ]

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=32, choices=ROLES)
    grade_level = models.IntegerField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("program", "person", "role")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.person} — {self.program} ({self.get_role_display()})"

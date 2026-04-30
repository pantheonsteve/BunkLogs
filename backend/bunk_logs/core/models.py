from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.db.models import Q

REFLECTION_FIELD_TYPES = frozenset(
    {"text", "textarea", "text_list", "rating_group", "multiple_choice", "single_choice"},
)


def validate_reflection_template_schema(schema: Any) -> None:
    if not isinstance(schema, dict):
        raise ValidationError({"schema": "Schema must be a JSON object."})
    fields = schema.get("fields")
    if not isinstance(fields, list) or len(fields) == 0:
        raise ValidationError({"schema": 'Schema must include a non-empty "fields" array.'})
    for i, field in enumerate(fields):
        loc = f"(field index {i})"
        if not isinstance(field, dict):
            raise ValidationError({"schema": f"Each field must be an object {loc}."})
        if "key" not in field or not isinstance(field["key"], str) or not field["key"].strip():
            raise ValidationError({"schema": f"Each field requires a non-empty string key {loc}."})
        ftype = field.get("type")
        if ftype not in REFLECTION_FIELD_TYPES:
            raise ValidationError(
                {
                    "schema": (
                        f"Unknown or missing type {loc}; allowed: "
                        f"{', '.join(sorted(REFLECTION_FIELD_TYPES))}."
                    ),
                },
            )
        if ftype == "rating_group":
            labels = field.get("scale_labels")
            if not isinstance(labels, dict) or len(labels) < 1:
                raise ValidationError(
                    {"schema": f"rating_group requires scale_labels with at least one language {loc}."},
                )
            for lang, vals in labels.items():
                if not lang or not isinstance(vals, list):
                    raise ValidationError(
                        {"schema": f"scale_labels must map language codes to lists {loc}."},
                    )
            cats = field.get("categories")
            if not isinstance(cats, list) or not cats:
                raise ValidationError({"schema": f"rating_group requires a non-empty categories array {loc}."})
            for j, cat in enumerate(cats):
                if not isinstance(cat, dict):
                    raise ValidationError({"schema": f"categories[{j}] must be an object {loc}."})
                ckey = cat.get("key")
                if not isinstance(ckey, str) or not ckey.strip():
                    raise ValidationError({"schema": f"categories[{j}] requires a non-empty key {loc}."})
                clabels = cat.get("labels")
                if not isinstance(clabels, dict) or len(clabels) < 1:
                    raise ValidationError(
                        {"schema": f"categories[{j}] requires labels with at least one language {loc}."},
                    )
        else:
            prompts = field.get("prompts")
            if not isinstance(prompts, dict) or len(prompts) < 1:
                raise ValidationError(
                    {"schema": f"Field requires prompts with at least one language code {loc}."},
                )


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


class ReflectionTemplate(models.Model):
    CADENCES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("biweekly", "Biweekly"),
        ("monthly", "Monthly"),
        ("on_demand", "On Demand"),
    ]

    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reflection_templates",
        help_text="Null = global template available to all orgs",
    )
    program_type = models.CharField(
        max_length=32,
        choices=Program.PROGRAM_TYPES,
        null=True,
        blank=True,
    )
    role = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Membership role this template targets. Null = applies to all roles in program type.",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    cadence = models.CharField(max_length=32, choices=CADENCES)
    schema = models.JSONField(
        help_text="JSON schema with localized prompts; see docs/reflection-template-schema.md",
    )
    languages = models.JSONField(
        default=list,
        blank=True,
        help_text="Supported language codes, e.g. ['en', 'es']",
    )
    is_active = models.BooleanField(default=True)
    version = models.IntegerField(default=1)
    parent_template = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="versions",
        help_text="Previous version of this template; for version history",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("organization", "slug", "version")]
        ordering = ["organization_id", "slug", "-version"]

    def __str__(self) -> str:
        org = self.organization.slug if self.organization else "global"
        return f"{self.name} ({org} v{self.version})"

    def clean(self) -> None:
        super().clean()
        validate_reflection_template_schema(self.schema)

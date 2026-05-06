from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.db.models import Q

from bunk_logs.core.managers import MembershipScopedManager
from bunk_logs.core.managers import OrgScopedManager
from bunk_logs.core.managers import ReflectionTemplateScopedManager
from bunk_logs.core.validators.template_schema import ALL_FIELD_TYPES
from bunk_logs.core.validators.template_schema import META_FIELD_TYPES
from bunk_logs.core.validators.template_schema import validate_template_schema

# Backward-compat alias used by management commands and existing tests
REFLECTION_FIELD_TYPES = ALL_FIELD_TYPES


def validate_reflection_template_schema(schema: Any) -> None:
    """Backward-compatible wrapper; call validate_template_schema directly for new code."""
    validate_template_schema(schema, [])


def validate_reflection_answers(schema: Any, answers: Any) -> None:
    """Ensure answers object matches template.schema field keys and basic value shapes."""
    if not isinstance(answers, dict):
        raise ValidationError({"answers": "Answers must be a JSON object."})
    if not isinstance(schema, dict):
        raise ValidationError({"answers": "Template schema is invalid."})
    fields = schema.get("fields")
    if not isinstance(fields, list):
        raise ValidationError({"answers": 'Template schema must include a "fields" array.'})

    for i, field in enumerate(fields):
        loc = f"(field index {i})"
        if not isinstance(field, dict):
            raise ValidationError({"answers": f"Invalid field definition in template {loc}."})
        key = field.get("key")
        if not isinstance(key, str) or not key.strip():
            raise ValidationError({"answers": f"Invalid field key in template {loc}."})
        ftype = field.get("type")
        if ftype not in REFLECTION_FIELD_TYPES:
            raise ValidationError({"answers": f"Unknown field type in template {loc}."})

        # Meta fields are rendered but not collected as answer data
        if ftype in META_FIELD_TYPES:
            continue

        required = field.get("required", True)
        if key not in answers:
            if required is False:
                continue
            raise ValidationError({"answers": f'Missing required answer for field "{key}".'})
        value = answers[key]
        if ftype in ("text", "textarea", "single_choice", "date"):
            if not isinstance(value, str):
                raise ValidationError({"answers": f'Field "{key}" must be a string.'})
        elif ftype == "text_list":
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                raise ValidationError({"answers": f'Field "{key}" must be a list of strings.'})
            min_items = field.get("min_items")
            max_items = field.get("max_items")
            if min_items is not None and len(value) < min_items:
                raise ValidationError(
                    {"answers": f'Field "{key}" requires at least {min_items} items.'},
                )
            if max_items is not None and len(value) > max_items:
                raise ValidationError(
                    {"answers": f'Field "{key}" allows at most {max_items} items.'},
                )
        elif ftype == "multiple_choice":
            if not isinstance(value, list):
                raise ValidationError({"answers": f'Field "{key}" must be a list.'})
        elif ftype == "yes_no":
            if value not in ("yes", "no", True, False):
                raise ValidationError(
                    {"answers": f'Field "{key}" must be "yes", "no", true, or false.'},
                )
        elif ftype == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError({"answers": f'Field "{key}" must be a number.'})
        elif ftype in ("rating_group", "single_rating"):
            if ftype == "single_rating":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValidationError(
                        {"answers": f'Field "{key}" must be a numeric rating.'},
                    )
            else:
                if not isinstance(value, dict):
                    raise ValidationError(
                        {"answers": f'Field "{key}" must be an object mapping categories to ratings.'},
                    )
                cats = field.get("categories")
                if not isinstance(cats, list):
                    raise ValidationError(
                        {"answers": f'Field "{key}" template categories are invalid.'},
                    )
                cat_keys = {
                    c.get("key")
                    for c in cats
                    if isinstance(c, dict) and isinstance(c.get("key"), str)
                }
                for ck, rating in value.items():
                    if ck not in cat_keys:
                        raise ValidationError(
                            {"answers": f'Field "{key}" contains unknown category "{ck}".'},
                        )
                    if isinstance(rating, bool) or not isinstance(rating, (int, float)):
                        raise ValidationError(
                            {"answers": f'Field "{key}" category "{ck}" must be a numeric rating.'},
                        )
                if required is not False:
                    missing = cat_keys - set(value.keys())
                    if missing:
                        raise ValidationError(
                            {
                                "answers": (
                                    f'Field "{key}" is missing ratings for: '
                                    f'{", ".join(sorted(missing))}.'
                                ),
                            },
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

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

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
        if self.organization_id:
            return f"[{self.organization.slug}] {self.name}"
        return self.name or "Program"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End date must be on or after start date."},
            )
        if self.organization_id and (self.name or "").strip():
            org_name = (self.organization.name or "").strip()
            display = (self.name or "").strip()
            if org_name and not display.startswith(org_name):
                raise ValidationError(
                    {
                        "name": (
                            "Program title must begin with the organization name "
                            f"({org_name!r}) so records stay identifiable across tenants."
                        ),
                    },
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

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

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

    objects = MembershipScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

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

    objects = ReflectionTemplateScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        unique_together = [("organization", "slug", "version")]
        ordering = ["organization_id", "slug", "-version"]

    def __str__(self) -> str:
        org = self.organization.slug if self.organization else "global"
        return f"{self.name} ({org} v{self.version})"

    def clean(self) -> None:
        super().clean()
        validate_template_schema(self.schema, self.languages or [])


class Reflection(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="reflections",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="reflections",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="reflections",
    )
    template = models.ForeignKey(
        ReflectionTemplate,
        on_delete=models.PROTECT,
        related_name="reflections",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reflections_submitted",
        help_text="Who actually submitted this reflection",
    )
    period_start = models.DateField(help_text="Start of period being reflected on")
    period_end = models.DateField(help_text="End of period being reflected on")
    answers = models.JSONField(help_text="Validated against template.schema")
    language = models.CharField(
        max_length=10,
        default="en",
        help_text="Language used to fill out this reflection",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_complete = models.BooleanField(default=True)

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-period_end"]
        indexes = [
            models.Index(fields=["organization", "program", "period_end"]),
            models.Index(fields=["person", "period_end"]),
            models.Index(fields=["template", "is_complete"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(period_end__gte=F("period_start")),
                name="core_reflection_period_end_gte_period_start",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person} — {self.template.slug} ({self.period_end})"

    def validate_answers(self) -> None:
        validate_reflection_answers(self.template.schema, self.answers)

    def clean(self) -> None:
        super().clean()
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValidationError(
                {"period_end": "End of period must be on or after start of period."},
            )
        if self.program_id and self.organization_id and self.program.organization_id != self.organization_id:
            raise ValidationError({"program": "Program must belong to the same organization."})
        if self.person_id and self.organization_id and self.person.organization_id != self.organization_id:
            raise ValidationError({"person": "Person must belong to the same organization."})
        if self.template_id and self.organization_id:
            to = self.template.organization_id
            if to is not None and to != self.organization_id:
                raise ValidationError({"template": "Template must be global or belong to the same organization."})
        if self.template_id:
            self.validate_answers()

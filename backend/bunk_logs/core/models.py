import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.db.models import F
from django.db.models import Q

from bunk_logs.core.managers import AssignmentGroupMembershipScopedManager
from bunk_logs.core.managers import AuditEventAllManager
from bunk_logs.core.managers import AuditEventScopedManager
from bunk_logs.core.managers import FieldKeyScopedManager
from bunk_logs.core.managers import MembershipScopedManager
from bunk_logs.core.managers import OrgScopedManager
from bunk_logs.core.managers import ProgramScopedManager
from bunk_logs.core.managers import ReflectionTemplateScopedManager
from bunk_logs.core.managers import SupervisionEventScopedManager
from bunk_logs.core.managers import SupervisionManager
from bunk_logs.core.state_machine import OrderStateMachine
from bunk_logs.core.state_machine import TransitionPlan
from bunk_logs.core.validators.template_schema import ALL_FIELD_TYPES
from bunk_logs.core.validators.template_schema import META_FIELD_TYPES
from bunk_logs.core.validators.template_schema import validate_template_coherence
from bunk_logs.core.validators.template_schema import validate_template_schema

# Backward-compat alias used by management commands and existing tests
REFLECTION_FIELD_TYPES = ALL_FIELD_TYPES


# Mapping from Membership.role to Membership.capability. Single source of truth
# kept in sync by Membership.save() and verified by a coverage test that
# asserts every role choice has a capability assignment. Permission code is
# expected to query on capability, not branch on individual role labels.
ROLE_TO_CAPABILITY: dict[str, str] = {
    "camper": "participant",
    "counselor": "participant",
    "junior_counselor": "participant",
    "specialist": "participant",
    "general_counselor": "participant",
    "kitchen_staff": "participant",
    "maintenance": "participant",
    "housekeeping": "participant",
    "madrich": "participant",
    "unit_head": "supervisor",
    "faculty": "supervisor",
    "camper_care": "supervisor",
    "leadership_team": "program_lead",
    "health_center": "domain_specialist",
    "special_diets": "domain_specialist",
    "admin": "admin",
}


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
    # ---- i18n (Step 7_5) ------------------------------------------------
    # ``LANGUAGE_CHOICES`` covers UI translation targets (English + Spanish in
    # Tier 1). ``CONTENT_LANGUAGE_CHOICES`` additionally allows Hebrew for
    # content authored by Israeli kitchen staff -- Hebrew UI / RTL layout
    # are deferred to Tier 2, but Hebrew *content* is supported now per
    # ``docs/user_stories/00_cross_cutting/i18n.md``. Keep the two lists
    # close together so adding a language is a single-file edit.
    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("es", "Spanish"),
        ("he", "Hebrew"),
    ]

    class TranslationPreference(models.TextChoices):
        TRANSLATION_FIRST = "translation_first", "Translation first"
        ORIGINAL_FIRST = "original_first", "Original first"

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
    preferred_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default="en",
        help_text=(
            "Preferred language for UI + email communications. Tier 1 ships "
            "English + Spanish UI; Hebrew renders natively (עברית) in the "
            "language picker but the surrounding UI stays English -- see "
            "docs/user_stories/00_cross_cutting/i18n.md."
        ),
    )
    translation_preference = models.CharField(
        max_length=24,
        choices=TranslationPreference.choices,
        default=TranslationPreference.TRANSLATION_FIRST,
        help_text=(
            "Per-reader preference for bilingual content (Story 44 criterion 6). "
            "Stored on Person so it persists across sessions. Only affects "
            "rendering when the content's language differs from English."
        ),
    )
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
    """A Person's participation in a Program with a specific role.

    ``role`` is the customer-facing label and template-routing key (16 values).
    ``capability`` is a derived RBAC layer with 5 values, kept in sync from
    ``role`` via ``ROLE_TO_CAPABILITY`` on every ``save()``. Permission code
    should query on ``capability``; do not mutate ``role`` via
    ``QuerySet.update()`` or ``bulk_create``, as those bypass the sync.
    """

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

    CAPABILITIES = [
        ("participant", "Participant"),
        ("supervisor", "Supervisor"),
        ("program_lead", "Program Lead"),
        ("domain_specialist", "Domain Specialist"),
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
    capability = models.CharField(
        max_length=32,
        choices=CAPABILITIES,
        db_index=True,
        help_text="RBAC layer derived from role via ROLE_TO_CAPABILITY.",
    )
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

    def save(self, *args, **kwargs):
        try:
            self.capability = ROLE_TO_CAPABILITY[self.role]
        except KeyError as exc:
            raise ValidationError(
                {"role": f"role {self.role!r} has no capability mapping."},
            ) from exc
        super().save(*args, **kwargs)


class AssignmentGroup(models.Model):
    GROUP_TYPES = [
        ("bunk", "Bunk"),
        ("classroom", "Classroom"),
        ("caseload", "Caseload"),
        ("unit", "Unit"),
        ("division", "Division"),
        ("cohort", "Cohort"),
        ("specialty", "Specialty/Activity Group"),
        ("custom", "Custom Group"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="assignment_groups",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="assignment_groups",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    group_type = models.CharField(max_length=32, choices=GROUP_TYPES)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        help_text="For nesting: bunk -> unit -> division",
    )
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        unique_together = [("program", "slug")]
        ordering = ["group_type", "name"]
        indexes = [
            models.Index(fields=["program", "group_type", "is_active"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_group_type_display()}: {self.name}"

    def get_descendants(self) -> list:
        """Recursive children for hierarchy queries (cache for perf if needed)."""
        descendants = list(AssignmentGroup.all_objects.filter(parent=self, is_active=True))
        for child in list(descendants):
            descendants.extend(child.get_descendants())
        return descendants


class AssignmentGroupMembership(models.Model):
    ROLES_IN_GROUP = [
        ("subject", "Subject"),
        ("author", "Author"),
    ]

    group = models.ForeignKey(
        AssignmentGroup,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="assignment_group_memberships",
    )
    role_in_group = models.CharField(max_length=16, choices=ROLES_IN_GROUP)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Role-specific data, e.g. {'is_lead_counselor': true}",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AssignmentGroupMembershipScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        unique_together = [("group", "person", "role_in_group")]
        indexes = [
            models.Index(fields=["group", "role_in_group", "is_active"]),
            models.Index(fields=["person", "role_in_group", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.person} as {self.get_role_in_group_display()} in {self.group}"


class RosterImportLog(models.Model):
    IMPORT_STATUS = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="roster_import_logs",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="roster_import_logs",
    )
    importer_type = models.CharField(max_length=64)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="roster_import_logs",
    )
    status = models.CharField(max_length=32, choices=IMPORT_STATUS, default="pending")
    summary = models.JSONField(default=dict, blank=True)
    csv_filename = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.importer_type} import for {self.program} ({self.status})"


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

    SUBJECT_MODES = [
        ("self", "Self-reflection (author == subject)"),
        ("single_subject", "About one other person"),
        ("multi_subject", "About multiple people in one submission"),
        ("group", "About a group/unit, no individual subject"),
    ]
    subject_mode = models.CharField(max_length=32, choices=SUBJECT_MODES, default="self")

    ASSIGNMENT_SCOPES = [
        ("none", "No group context"),
        ("per_subject_in_group", "One reflection per subject in the assignment group"),
        ("per_group", "One reflection per group as a whole"),
    ]
    assignment_scope = models.CharField(max_length=32, choices=ASSIGNMENT_SCOPES, default="none")

    assignment_group_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Which group types this template applies to, e.g. ['bunk']",
    )
    author_role_filter = models.JSONField(
        default=list,
        blank=True,
        help_text="Membership roles eligible to author this template, e.g. ['counselor', 'unit_head']",
    )
    subject_role_filter = models.JSONField(
        default=list,
        blank=True,
        help_text="Membership roles eligible to be subjects, e.g. ['camper']. Empty = any role.",
    )
    required_per_subject_per_period = models.IntegerField(
        default=1,
        help_text="How many reflections per subject per cadence period for completion",
    )
    subject_visible = models.BooleanField(
        default=False,
        help_text="Whether the subject can see reflections about themselves",
    )
    supports_privacy = models.BooleanField(
        default=False,
        help_text=(
            "Whether this template offers the per-reflection 'supervisors "
            "only' privacy toggle (Reflection.team_visibility). Off for "
            "self-reflection templates by default; on for templates where "
            "peer authors of the same AssignmentGroup would otherwise see "
            "the entry."
        ),
    )

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PUBLISHED,
        help_text=(
            "Lifecycle state. 'published' templates can collect responses, "
            "'draft' are LT-builder work-in-progress, 'archived' are "
            "preserved read-only for historical reflections. Old code that "
            "only inspects ``is_active`` keeps working because the default "
            "is 'published' (matches is_active=True)."
        ),
    )

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
        schema = self.schema or {}
        fields = schema.get("fields") if isinstance(schema, dict) else None
        if isinstance(fields, list) and fields:
            validate_template_schema(schema, self.languages or [])
        valid_roles = frozenset(role for role, _ in Membership.ROLES)
        validate_template_coherence(
            subject_mode=self.subject_mode or "self",
            assignment_scope=self.assignment_scope or "none",
            assignment_group_types=self.assignment_group_types or [],
            author_role_filter=self.author_role_filter or [],
            subject_role_filter=self.subject_role_filter or [],
            subject_visible=bool(self.subject_visible),
            valid_roles=valid_roles,
        )


class TemplateAssignment(models.Model):
    """A Leadership Team's binding of a ReflectionTemplate to a set of roles/people.

    LT users assign a published template to either a role (dynamic — new
    members joining mid-window get the template), a static list of
    individual Memberships (snapshotted at creation), or a tag-based
    group. Each assignment has its own date window and may override the
    template's cadence.

    Conflict resolution: when a new assignment overlaps an existing one
    on the same (template, target), the LT may ``"replace"`` (sets
    ``replaces`` FK and ends the prior assignment day-before),
    ``"run_both"`` (no coupling), or ``"cancel"`` (no record created;
    handled at API layer).
    """

    class TargetType(models.TextChoices):
        ROLE = "role", "Role (dynamic)"
        INDIVIDUALS = "individuals", "Individual memberships (static)"
        TAG_GROUP = "tag_group", "Tag group (dynamic)"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="template_assignments",
    )
    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name="template_assignments",
    )
    template = models.ForeignKey(
        ReflectionTemplate, on_delete=models.CASCADE, related_name="assignments",
    )
    target_type = models.CharField(max_length=16, choices=TargetType.choices)
    target_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Shape depends on target_type. role: {'role': 'kitchen_staff'}. "
            "individuals: {'membership_ids': [<int>...]}. "
            "tag_group: {'tag': 'kitchen-lead'}."
        ),
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    cadence_override = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        choices=ReflectionTemplate.CADENCES,
        help_text="If set, overrides template.cadence for this assignment.",
    )
    replaces = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replaced_by",
        help_text="Set when this assignment ended a prior one (conflict_resolution='replace').",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.SCHEDULED,
    )
    created_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="template_assignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-start_date", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "template", "status"]),
            models.Index(fields=["program", "start_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return (
            f"assignment template:{self.template_id} -> {self.target_type} "
            f"({self.start_date}-{self.end_date or 'open'})"
        )


class Reflection(models.Model):
    class TeamVisibility(models.TextChoices):
        TEAM = "team", "Visible to team"
        SUPERVISORS_ONLY = "supervisors_only", "Supervisors only"

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
    subject = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reflections_about",
        help_text="Who this reflection is ABOUT. Null when subject_mode='group'.",
    )
    subject_group = models.ForeignKey(
        AssignmentGroup,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reflections_as_subject",
        help_text="Set when subject_mode='group'",
    )
    author = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reflections_authored",
        help_text="Who FILLED OUT this reflection (may equal subject for self-reflection)",
    )
    assignment_group = models.ForeignKey(
        AssignmentGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reflections",
        help_text="Which group context this was authored in (e.g. which bunk)",
    )
    submission_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
        help_text="Groups multi-subject submissions together",
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
        help_text="Who actually submitted this reflection (User; audit trail)",
    )
    period_start = models.DateField(help_text="Start of period being reflected on")
    period_end = models.DateField(help_text="End of period being reflected on")
    answers = models.JSONField(help_text="Validated against template.schema")
    language = models.CharField(
        max_length=10,
        choices=Person.LANGUAGE_CHOICES,
        default="en",
        help_text=(
            "Language used to fill out this reflection. Non-English "
            "submissions trigger the server-side auto-translation task "
            "(see ``bunk_logs.core.translation``)."
        ),
    )
    team_visibility = models.CharField(
        max_length=24,
        choices=TeamVisibility.choices,
        default=TeamVisibility.TEAM,
        db_index=True,
        help_text=(
            "Who else (beyond author + admin + ancestor-group authors + "
            "unit-scoped supervisors of the subject) can read this reflection. "
            "Default 'team' keeps peer authors in the loop; 'supervisors_only' "
            "hides it from same-group peers and from the wellness-template "
            "shortcut."
        ),
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_complete = models.BooleanField(default=True)
    is_sensitive = models.BooleanField(
        default=False,
        null=True,
        help_text=(
            "When true, only the sensitive-variant audience for this content "
            "type may read the reflection (author and org admin always can)."
        ),
    )
    client_submission_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Client-supplied idempotency key (Step 7_6 Story 7 criterion 6). "
            "The frontend offline queue retries POSTs after reconnect; "
            "the API short-circuits duplicates by returning the existing "
            "row when (program, client_submission_id) already exists. "
            "Null for server-side / legacy creations."
        ),
    )

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-period_end"]
        indexes = [
            models.Index(fields=["organization", "program", "period_end"]),
            models.Index(fields=["subject", "period_end"]),
            models.Index(fields=["subject_group", "period_end"]),
            models.Index(fields=["assignment_group", "period_end"]),
            models.Index(fields=["author", "period_end"]),
            models.Index(fields=["template", "is_complete"]),
            models.Index(fields=["submission_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(period_end__gte=F("period_start")),
                name="core_reflection_period_end_gte_period_start",
            ),
            models.UniqueConstraint(
                fields=["program", "client_submission_id"],
                condition=Q(client_submission_id__isnull=False),
                name="core_reflection_client_submission_unique",
            ),
        ]

    def __str__(self) -> str:
        who = self.subject or self.subject_group or "?"
        return f"{who} — {self.template.slug} ({self.period_end})"

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
        if self.subject_id and self.organization_id and self.subject.organization_id != self.organization_id:
            raise ValidationError({"subject": "Subject must belong to the same organization."})
        if self.author_id and self.organization_id and self.author.organization_id != self.organization_id:
            raise ValidationError({"author": "Author must belong to the same organization."})
        if self.template_id and self.organization_id:
            to = self.template.organization_id
            if to is not None and to != self.organization_id:
                raise ValidationError({"template": "Template must be global or belong to the same organization."})
        if self.template_id:
            self.validate_answers()


class Note(models.Model):
    """Free-text note attached to a subject (camper profile, ticket, etc.)."""

    class NoteType(models.TextChoices):
        CAMPER_CARE = "camper_care", "Camper Care"
        SPECIALIST = "specialist", "Specialist"
        MAINTENANCE = "maintenance", "Maintenance"

    class MaintenanceVisibility(models.TextChoices):
        TEAM_ONLY = "team_only", "Team only"
        SUBMITTER_VISIBLE = "submitter_visible", "Submitter and team"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    subject = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="notes_about",
    )
    author = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notes_authored",
    )
    note_type = models.CharField(max_length=32, choices=NoteType.choices)
    body = models.TextField()
    is_sensitive = models.BooleanField(
        default=False,
        null=True,
        help_text="Narrows audience per the visibility model sensitive-variant table.",
    )

    class Category(models.TextChoices):
        MEDICAL = "medical", "Medical"
        FAMILY = "family", "Family"
        SOCIAL = "social", "Social"
        BEHAVIORAL = "behavioral", "Behavioral"
        OTHER = "other", "Other"

    category = models.CharField(
        max_length=16,
        choices=Category.choices,
        blank=True,
        default="",
        help_text=(
            "Camper Care note category (Story 21 criterion 2). Required by the "
            "Camper Care write endpoint; left blank for specialist / maintenance "
            "notes that don't use the enum."
        ),
    )
    maintenance_visibility = models.CharField(
        max_length=32,
        choices=MaintenanceVisibility.choices,
        default=MaintenanceVisibility.TEAM_ONLY,
        blank=True,
        help_text="Only used when note_type is maintenance.",
    )
    language = models.CharField(
        max_length=10,
        choices=Person.LANGUAGE_CHOICES,
        default="en",
        help_text=(
            "Language used to author this note. Non-English notes trigger "
            "the server-side auto-translation task once the Note edit views "
            "land (Steps 7_8 / 7_9 / 7_10)."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "program", "subject", "created_at"]),
            models.Index(fields=["note_type", "is_sensitive"]),
        ]

    def __str__(self) -> str:
        return f"{self.note_type} note about {self.subject_id}"


class ConcernReadState(models.Model):
    """Tracks per-user "I've read this concern" state for the Concerns Inbox.

    A concern is a (reflection, field_key) pair where the field's
    ``dashboard_role`` is ``open_concern`` and the answer is non-empty (text)
    OR the answer crosses a numeric threshold (rating ≤ 1 in the prior 14d
    window — surfaced in the per-subject view too).

    We don't denormalize the concern itself; instead the dashboard query joins
    this table to filter out already-read items per viewer.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="concern_read_states",
    )
    reflection = models.ForeignKey(
        Reflection,
        on_delete=models.CASCADE,
        related_name="concern_read_states",
    )
    field_key = models.CharField(
        max_length=64,
        help_text="Schema field key the concern came from (e.g. 'concerns', 'overall').",
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "reflection", "field_key")]
        ordering = ["-read_at"]
        indexes = [
            models.Index(fields=["user", "reflection"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} read {self.reflection_id}/{self.field_key}"


class FieldKey(models.Model):
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="field_keys",
        help_text="Null = global key available to all orgs",
    )
    key = models.CharField(max_length=64)
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    expected_field_type = models.CharField(
        max_length=32,
        blank=True,
        help_text="Optional hint for editor: text, rating_group, etc.",
    )
    expected_dashboard_role = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FieldKeyScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        unique_together = [("organization", "key")]
        ordering = ["key"]
        indexes = [
            models.Index(fields=["key"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["key"],
                condition=models.Q(organization__isnull=True),
                name="core_fieldkey_global_key_unique",
            ),
        ]

    def __str__(self) -> str:
        scope = self.organization.slug if self.organization_id else "global"
        return f"{self.key} ({scope})"


class OrderableContent(models.Model):
    """Abstract mixin: shared status + state-machine integration for order-like content.

    Concrete subclasses provide the rest of the domain model (subject, location,
    description, photos, etc.); this mixin owns the lifecycle. State changes
    must go through :py:meth:`transition_to` so the audit trail stays in sync.
    """

    class Status(models.TextChoices):
        NEW = OrderStateMachine.NEW, "New"
        IN_PROGRESS = OrderStateMachine.IN_PROGRESS, "In Progress"
        FULFILLED = OrderStateMachine.FULFILLED, "Fulfilled"
        UNABLE_TO_FULFILL = OrderStateMachine.UNABLE_TO_FULFILL, "Unable to Fulfill"

    class Urgency(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        URGENT = "urgent", "Urgent"

    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    urgency = models.CharField(
        max_length=16,
        choices=Urgency.choices,
        blank=True,
        default="",
        help_text=(
            "Optional priority. Used by Maintenance tickets; left blank "
            "for Camper Care orders unless the program opts in."
        ),
    )
    last_transition_at = models.DateTimeField(null=True, blank=True)
    last_transition_by = models.ForeignKey(
        "core.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Membership of the actor who applied the most recent transition.",
    )

    class Meta:
        abstract = True

    def _content_type_label(self) -> str:
        """Stable string identifier used by activity/audit events.

        Defaults to the model's class name in snake_case (``order``,
        ``maintenance_ticket``); subclasses may override to pin a different
        label across renames.
        """
        name = self.__class__.__name__
        out = []
        for i, ch in enumerate(name):
            if ch.isupper() and i > 0:
                out.append("_")
            out.append(ch.lower())
        return "".join(out)

    def transition_to(
        self,
        new_state: str,
        *,
        actor,
        note: str | None = None,
        reason: str | None = None,
    ) -> "OrderActivityEvent":
        """Validate via :class:`OrderStateMachine`, persist the new status,
        and record an :class:`OrderActivityEvent`.

        ``actor`` may be a :class:`Membership` or anything with ``user`` and
        ``program`` attrs (callers in tests sometimes pass a stub). The actor's
        program must match the order's program; cross-org actors are rejected.
        """
        plan: TransitionPlan = TransitionPlan.build(
            from_state=self.status,
            to_state=new_state,
            note=note,
            reason=reason,
        )
        actor_membership = _resolve_actor_membership(actor)
        if actor_membership is not None and self.program_id and (
            actor_membership.program_id != self.program_id
        ):
            raise ValidationError(
                {"actor": "Actor must be a Membership in the same Program."},
            )

        with transaction.atomic():
            event = OrderActivityEvent.all_objects.create(
                organization=self.organization,
                program=self.program,
                actor_membership=actor_membership,
                actor_user=getattr(actor_membership, "person", None) and actor_membership.person.user,
                event_type=OrderActivityEvent.EventType.STATE_CHANGE,
                content_type=self._content_type_label(),
                content_id=self.id,
                from_state=plan.from_state,
                to_state=plan.to_state,
                note=plan.note,
                reason=plan.reason,
                metadata={"requires_reason": plan.requires_reason},
            )
            # Pin ``last_transition_at`` to the event's ``created_at`` so the
            # 5-minute correction window and the activity log agree to the
            # microsecond. ``timezone.now()`` would drift slightly.
            self.status = plan.to_state
            self.last_transition_at = event.created_at
            self.last_transition_by = actor_membership
            self.save(update_fields=["status", "last_transition_at", "last_transition_by"])
            # Cross-cutting audit row (Step 7_4). Dual-write alongside
            # ``OrderActivityEvent`` until the 7_2 activity table is backfilled
            # and retired.
            from bunk_logs.core import audit as audit_module

            audit_module.state_changed(
                actor_membership,
                self,
                plan.from_state,
                plan.to_state,
                note=plan.reason or plan.note,
                metadata={
                    "activity_event_id": str(event.id),
                    "requires_reason": plan.requires_reason,
                    "transition_note": plan.note,
                },
            )
        return event

    def can_correct_last_transition(self, *, now=None) -> bool:
        """Whether the most recent transition is still inside the 5-minute window."""
        return OrderStateMachine.is_within_correction_window(
            self.last_transition_at, now=now,
        )

    def correct_last_transition(self, *, actor) -> "OrderActivityEvent":
        """Revert the most recent transition; only valid inside the 5-minute window.

        Returns the correction event. Raises :class:`OrderStateMachineError` /
        :class:`ValidationError` on misuse. Does not allow correcting a
        correction (correction events are not state changes by themselves).
        """
        from bunk_logs.core.state_machine import CorrectionWindowExpiredError
        from bunk_logs.core.state_machine import NoTransitionToCorrectError

        if not self.can_correct_last_transition():
            if self.last_transition_at is None:
                msg = "no transition to correct"
                raise NoTransitionToCorrectError(msg)
            msg = "the 5-minute correction window has expired"
            raise CorrectionWindowExpiredError(msg)

        last_event = (
            OrderActivityEvent.all_objects.filter(
                content_type=self._content_type_label(),
                content_id=self.id,
                event_type=OrderActivityEvent.EventType.STATE_CHANGE,
            )
            .order_by("-created_at")
            .first()
        )
        if last_event is None:
            msg = "no state-change activity event found"
            raise NoTransitionToCorrectError(msg)

        actor_membership = _resolve_actor_membership(actor)
        with transaction.atomic():
            self.status = last_event.from_state
            # Restore prior transition timestamp/actor by walking back one event.
            prior = (
                OrderActivityEvent.all_objects.filter(
                    content_type=self._content_type_label(),
                    content_id=self.id,
                    event_type=OrderActivityEvent.EventType.STATE_CHANGE,
                )
                .exclude(pk=last_event.pk)
                .order_by("-created_at")
                .first()
            )
            self.last_transition_at = prior.created_at if prior else None
            self.last_transition_by = prior.actor_membership if prior else None
            self.save(update_fields=["status", "last_transition_at", "last_transition_by"])

            correction_event = OrderActivityEvent.all_objects.create(
                organization=self.organization,
                program=self.program,
                actor_membership=actor_membership,
                actor_user=getattr(actor_membership, "person", None) and actor_membership.person.user,
                event_type=OrderActivityEvent.EventType.CORRECTION,
                content_type=self._content_type_label(),
                content_id=self.id,
                from_state=last_event.to_state,
                to_state=last_event.from_state,
                note="",
                reason="",
                correction_of=last_event,
                metadata={"corrected_event_id": str(last_event.id)},
            )
            # Dual-write a STATE_CHANGED audit row for the corrected transition
            # so the cross-cutting audit log stays a faithful timeline.
            from bunk_logs.core import audit as audit_module

            audit_module.state_changed(
                actor_membership,
                self,
                last_event.to_state,
                last_event.from_state,
                metadata={
                    "activity_event_id": str(correction_event.id),
                    "corrected_event_id": str(last_event.id),
                    "correction": True,
                },
            )
            return correction_event

    def available_transitions(self) -> list[str]:
        return OrderStateMachine.available_transitions(self.status)


def _resolve_actor_membership(actor):
    """Coerce a Membership-or-User-like object into a Membership instance.

    Returns ``None`` when no resolution is possible (e.g. tests passing
    ``None``). Concrete views are expected to pass a Membership directly.
    """
    if actor is None:
        return None
    if isinstance(actor, Membership):
        return actor
    membership = getattr(actor, "membership", None)
    if membership is not None:
        return membership
    return None


class Order(OrderableContent):
    """Camper Care order — see Stories 22-23 and the order_state_machine spec.

    Domain fields (subject, requested items, etc.) are added in Step 7_8;
    this skeleton owns the lifecycle so the state machine can be exercised
    independently and so 7_8 can extend rather than redefine the model.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="cc_orders",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="cc_orders",
    )
    subject = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cc_orders_about",
        help_text="Camper this order is for. Null when the order is bunk-scoped only.",
    )
    submitted_by = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cc_orders_submitted",
        help_text="Membership of the counselor / submitter.",
    )
    item = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text=(
            "Camper-care item requested (Story 7 criterion 2.ii). Free-text "
            "with autocomplete on the client against ``OrderItemSuggestion`` "
            "rows; the canonical value is stored here so admins maintaining "
            "the suggestion list don't retroactively rewrite history."
        ),
    )
    item_note = models.TextField(
        blank=True,
        default="",
        help_text="Optional note from the requester (Story 7 criterion 2.iii).",
    )
    description = models.TextField(blank=True)
    client_submission_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Client-supplied idempotency key (Step 7_6 Story 7 criterion 6). "
            "Unique with ``program`` so the offline queue can replay safely."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "program", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "client_submission_id"],
                condition=Q(client_submission_id__isnull=False),
                name="core_order_client_submission_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"Order {self.id} ({self.get_status_display()})"

    @staticmethod
    def fulfilling_role() -> str:
        return "camper_care"


class OrderItemSuggestion(models.Model):
    """Curated camper-care item suggestion list (Story 7 criterion 2.ii, decision C6).

    Admin maintains the list per ``program`` (Story 58). The Counselor form
    pulls from here as autocomplete options; counselors can still type free
    text. Storing per-program (not per-org) lets a TBE religious-school
    program disable the surface entirely by leaving the table empty for
    that program while Crane Lake summer 2026 has a populated list.
    """

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="order_item_suggestions",
    )
    label = models.CharField(
        max_length=120,
        help_text="Canonical display label, e.g. 'Toothbrush'.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Lower numbers appear first; ties break alphabetically.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProgramScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        unique_together = [("program", "label")]
        ordering = ["sort_order", "label"]
        indexes = [
            models.Index(fields=["program", "is_active", "sort_order"]),
        ]

    def __str__(self) -> str:
        return self.label

    @property
    def organization(self):
        return self.program.organization if self.program_id else None


class MaintenanceTicket(OrderableContent):
    """Maintenance ticket — see Stories 30-36 and the order_state_machine spec.

    Counselor-side submission fields (location, category, photos, urgency
    reason) land in Step 7_6; maintenance-team fulfillment surfaces land
    in Step 7_10.
    """

    class Category(models.TextChoices):
        PLUMBING = "plumbing", "Clogged plumbing"
        BROKEN_LIGHT = "broken_light", "Broken light"
        PEST = "pest", "Pest / Insect"
        LEAK = "leak", "Leak"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="maintenance_tickets",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="maintenance_tickets",
    )
    submitted_by = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maintenance_tickets_submitted",
    )
    title = models.CharField(max_length=255, blank=True)
    location = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Free-text camp location (Story 8 criterion 1.i). Defaults to "
            "the submitter's bunk on the client; persisted as the canonical "
            "value submitted so renames of bunks don't rewrite history."
        ),
    )
    category = models.CharField(
        max_length=24,
        choices=Category.choices,
        blank=True,
        default="",
        help_text="Triage category (Story 8 criterion 1.ii).",
    )
    description = models.TextField(blank=True)
    urgent_reason = models.TextField(
        blank=True,
        help_text="Required by API when urgency is 'urgent' (Story 8 criterion 2).",
    )
    client_submission_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Client-supplied idempotency key (Step 7_6 Story 8 criterion 4). "
            "Unique with ``program`` so the offline queue can replay safely."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "program", "status"]),
            models.Index(fields=["urgency", "status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "client_submission_id"],
                condition=Q(client_submission_id__isnull=False),
                name="core_maintenance_client_submission_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"Ticket {self.id} ({self.get_status_display()})"

    def clean(self) -> None:
        super().clean()
        if self.urgency == self.Urgency.URGENT and not (self.urgent_reason or "").strip():
            raise ValidationError(
                {"urgent_reason": "Required when urgency is 'urgent' (Story 8 criterion 2)."},
            )

    @staticmethod
    def fulfilling_role() -> str:
        return "maintenance"


def maintenance_ticket_photo_upload_path(instance: "TicketPhoto", filename: str) -> str:
    """Per-org, per-ticket key for ticket photo uploads.

    Layout keeps photos partitioned by organization so storage rules
    (lifecycle, replication, retention) can attach at the org prefix
    cleanly. Filename is the photo UUID + original extension so two
    counselors uploading ``IMG_1234.jpg`` minutes apart don't collide.
    """
    suffix = ""
    if "." in filename:
        suffix = "." + filename.rsplit(".", 1)[-1].lower()
    ticket_id = instance.ticket_id or "unknown"
    org_slug = "unscoped"
    if instance.ticket_id and instance.ticket.organization_id:
        org_slug = instance.ticket.organization.slug or "unscoped"
    return f"maintenance_tickets/{org_slug}/{ticket_id}/{instance.id}{suffix}"


class TicketPhoto(models.Model):
    """Photo attached to a :class:`MaintenanceTicket` (Story 8 criteria 1.iv, 3).

    Stored via the configured default storage backend -- S3 in production
    (see ``config/settings/production.py``) and the local filesystem in
    dev / tests. Counselors can add follow-up photos to their own open
    tickets per decision C5; the foreign key + ordering supports the
    "follow-ups appear in order under the original" UX without us having
    to model "primary vs follow-up" explicitly.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        MaintenanceTicket,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(
        upload_to=maintenance_ticket_photo_upload_path,
        max_length=512,
    )
    caption = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maintenance_ticket_photos_uploaded",
    )
    is_followup = models.BooleanField(
        default=False,
        help_text=(
            "True for photos added after the ticket was first submitted "
            "(decision C5: Counselors can add follow-up photos)."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["ticket", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Photo {self.id} for ticket {self.ticket_id}"

    @property
    def organization(self):
        return self.ticket.organization if self.ticket_id else None


class CamperDayState(models.Model):
    """Per-camper, per-date operational state set by UH or Camper Care.

    Story 3 criterion 8 (decision C1): a camper marked "off camp today"
    appears in a separate sub-section on the counselor's roster, does not
    count toward "expected," and cannot have a reflection submitted for
    them. UH and Camper Care set the flag; Counselors only read it.

    Modelled as a date-keyed row rather than a flag on Membership so:

    * future-dated absences (e.g. a parent calling ahead about Thursday)
      can be recorded without affecting today's roster;
    * Camper Care can keep a brief reason note alongside the flag;
    * the audit trail captures who marked it via ``set_by_membership`` and
      the cross-cutting :class:`AuditEvent` written by the view layer.

    The unique ``(camper, date, organization)`` constraint makes upserts
    safe -- toggling off-camp twice on the same date updates the existing
    row rather than creating duplicates.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="camper_day_states",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="camper_day_states",
    )
    camper = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="day_states",
        help_text="The camper (Person) whose state this row records.",
    )
    date = models.DateField(
        help_text="Operational date (per org rollover). One row per camper per date.",
    )
    is_off_camp = models.BooleanField(
        default=False,
        help_text="True when the camper is marked off-camp for the date.",
    )
    reason = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Optional context (e.g. 'home visit', 'medical leave'). Visible "
            "to UH, Camper Care, Leadership Team, Admin -- not surfaced to "
            "Counselors in the roster row."
        ),
    )
    set_by_membership = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="camper_day_states_set",
        help_text="Membership of the UH / Camper Care who toggled the flag.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        unique_together = [("organization", "camper", "date")]
        ordering = ["-date", "camper_id"]
        indexes = [
            models.Index(fields=["program", "date", "is_off_camp"]),
            models.Index(fields=["camper", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.camper_id} on {self.date} (off_camp={self.is_off_camp})"

    def clean(self) -> None:
        super().clean()
        if self.program_id and self.organization_id and self.program.organization_id != self.organization_id:
            raise ValidationError(
                {"program": "Program must belong to the same organization."},
            )
        if self.camper_id and self.organization_id and self.camper.organization_id != self.organization_id:
            raise ValidationError(
                {"camper": "Camper must belong to the same organization."},
            )


class OrderActivityEvent(models.Model):
    """Append-only activity log for orders and tickets.

    This is a minimal, forward-compatible stand-in for the cross-cutting
    audit trail (Step 7_4). When :class:`AuditEvent` lands, write a one-off
    backfill that copies these rows over and points new state changes at the
    audit module instead. Callers in this step go through
    :py:meth:`OrderableContent.transition_to`.
    """

    class EventType(models.TextChoices):
        STATE_CHANGE = "state_change", "State change"
        CORRECTION = "correction", "Correction (within 5-minute window)"
        NOTE = "note", "Note (no state change)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="order_activity_events",
    )
    program = models.ForeignKey(
        Program,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_activity_events",
    )
    actor_membership = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_activity_events",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_activity_events",
    )
    event_type = models.CharField(max_length=24, choices=EventType.choices, db_index=True)
    content_type = models.CharField(
        max_length=64,
        help_text="Stable label for the related model (e.g. 'order', 'maintenance_ticket').",
    )
    content_id = models.UUIDField()
    from_state = models.CharField(max_length=24, blank=True)
    to_state = models.CharField(max_length=24, blank=True)
    note = models.TextField(blank=True)
    reason = models.TextField(blank=True)
    correction_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="corrections",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["content_type", "content_id", "created_at"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} on {self.content_type}:{self.content_id}"


# ---------------------------------------------------------------------------
# Flag (Step 7_8) — Camper Care triage primitive
# ---------------------------------------------------------------------------


class Flag(models.Model):
    """A flag raised on a camper for a downstream role to triage (Story 20).

    Flags have a tiny three-state lifecycle separate from the order/ticket
    state machine: Active (just raised) -> Followed Up (interim, optional
    note) -> Resolved (terminal, required closing note). Resolved/Followed
    Up flags can be Reopened back to Active (requires a reason). State
    transitions write :class:`AuditEvent` rows so the timeline on the camper
    dashboard stays a faithful history.

    ``trigger_content_type`` + ``trigger_content_id`` point at the
    content (specialist note, counselor reflection, UH manual flag) that
    raised the flag, so Camper Care can jump straight to the source from
    the workspace. The triple is intentionally loose-typed
    (``CharField`` + ``UUIDField``) to avoid a fan-out of GenericForeignKey
    machinery for what's effectively a workspace pointer.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FOLLOWED_UP = "followed_up", "Followed Up"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="flags",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="flags",
    )
    subject_camper = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="flags_about",
        help_text="The camper this flag is raised on.",
    )
    raised_by_membership = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="flags_raised",
        help_text="Membership of the role who raised this flag.",
    )
    flagged_for_role = models.CharField(
        max_length=32,
        default="camper_care",
        help_text=(
            "Role responsible for triaging this flag. Tier 1 only routes to "
            "``camper_care``; future expansion keeps the field open."
        ),
    )
    trigger_content_type = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=(
            "Stable label of the model that raised the flag "
            "(e.g. ``specialist_note``, ``reflection``)."
        ),
    )
    trigger_content_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="PK of the trigger row, serialised as a string.",
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by_membership = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="flags_resolved",
    )

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "program", "status"]),
            models.Index(fields=["subject_camper", "status"]),
            models.Index(fields=["flagged_for_role", "status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Flag {self.id} on camper {self.subject_camper_id} ({self.status})"

    # -- state machine -----------------------------------------------------

    # (from_state, to_state) -> requires_reason (True for closing/reopen)
    _TRANSITIONS: dict[tuple[str, str], bool] = {
        (Status.ACTIVE, Status.FOLLOWED_UP): False,
        (Status.FOLLOWED_UP, Status.FOLLOWED_UP): False,
        (Status.ACTIVE, Status.RESOLVED): True,
        (Status.FOLLOWED_UP, Status.RESOLVED): True,
        (Status.RESOLVED, Status.ACTIVE): True,
        (Status.FOLLOWED_UP, Status.ACTIVE): True,
    }

    @classmethod
    def transition_requires_reason(cls, from_state: str, to_state: str) -> bool:
        return cls._TRANSITIONS.get((from_state, to_state), False)

    @classmethod
    def can_transition(cls, from_state: str, to_state: str) -> bool:
        return (from_state, to_state) in cls._TRANSITIONS

    def transition_to(
        self,
        new_state: str,
        *,
        actor,
        note: str = "",
    ) -> "AuditEvent":
        """Apply a state transition + write an audit row.

        ``note`` doubles as the closing note for ``RESOLVED`` and the reason
        for ``ACTIVE`` (reopen). For ``FOLLOWED_UP`` the note is optional and
        captured in metadata.
        """
        if not self.can_transition(self.status, new_state):
            msg = f"transition {self.status!r} -> {new_state!r} is not allowed"
            raise ValidationError({"to_state": msg})
        if self.transition_requires_reason(self.status, new_state):
            if not (note or "").strip():
                msg = "A note is required for this transition."
                raise ValidationError({"note": msg})

        from bunk_logs.core import audit as audit_module

        prior = self.status
        actor_membership = _resolve_actor_membership(actor)
        if actor_membership is not None and self.program_id and (
            actor_membership.program_id != self.program_id
        ):
            raise ValidationError(
                {"actor": "Actor must be a Membership in the same Program."},
            )

        with transaction.atomic():
            self.status = new_state
            update_fields = ["status", "updated_at"]
            if new_state == self.Status.RESOLVED:
                from django.utils import timezone
                self.resolved_at = timezone.now()
                self.resolved_by_membership = actor_membership
                update_fields += ["resolved_at", "resolved_by_membership"]
            elif new_state == self.Status.ACTIVE and prior == self.Status.RESOLVED:
                self.resolved_at = None
                self.resolved_by_membership = None
                update_fields += ["resolved_at", "resolved_by_membership"]
            self.save(update_fields=update_fields)

            return audit_module.state_changed(
                actor_membership,
                self,
                prior,
                new_state,
                note=note,
                content_type="flag",
            )


# ---------------------------------------------------------------------------
# Supervision primitive (Step 7_3)
# ---------------------------------------------------------------------------

# Capabilities allowed to *be* supervisors. ``admin`` can supervise anything;
# ``supervisor`` covers UH / faculty / camper_care (caseload); ``program_lead``
# covers LT / Director-of-Madrichim. ``domain_specialist`` and ``participant``
# capabilities are not supervisors and are rejected at validation time.
SUPERVISOR_CAPABILITIES: frozenset[str] = frozenset(
    {"supervisor", "program_lead", "admin"},
)


class Supervision(models.Model):
    """A supervision relationship between a supervisor Membership and a target.

    One primitive covers four patterns (see ``core/SUPERVISION.md``):

    * UH -> Counselor (``target_type=MEMBERSHIP``)
    * Camper Care -> Caseload Bunk (``target_type=BUNK``)
    * LT -> team-by-role (``target_type=ROLE_IN_PROGRAM``)
    * Director -> Madrich cohort (``target_type=ROLE_IN_PROGRAM``)

    Multiple supervisors per target is supported; the model is many one-to-many
    rows that share the same target. End-dating a row is the only modification
    permitted after creation -- see ``api.supervisions`` for the gate.
    """

    class TargetType(models.TextChoices):
        MEMBERSHIP = "membership", "Membership (direct supervisee)"
        ROLE_IN_PROGRAM = "role_in_program", "Role in program (team-by-role)"
        BUNK = "bunk", "Bunk (caseload entry)"

    supervisor_membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="supervises",
        help_text="Membership of the supervising role.",
    )
    target_type = models.CharField(
        max_length=24,
        choices=TargetType.choices,
        db_index=True,
    )
    target_membership = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="supervised_by",
        help_text="Target Membership when target_type=MEMBERSHIP.",
    )
    target_role = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text=(
            "Target Membership.role string when target_type=ROLE_IN_PROGRAM. "
            "Must be one of Membership.ROLES."
        ),
    )
    target_program = models.ForeignKey(
        Program,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="supervisions_scoped_to_role",
        help_text="Program scoping the role; required when target_type=ROLE_IN_PROGRAM.",
    )
    target_bunk = models.ForeignKey(
        AssignmentGroup,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="caseload_supervisions",
        help_text=(
            "AssignmentGroup with group_type='bunk' when target_type=BUNK. "
            "Spec uses 'Bunk' as shorthand; new code targets AssignmentGroup."
        ),
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SupervisionManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["supervisor_membership", "target_type"]),
            models.Index(fields=["target_membership"]),
            models.Index(fields=["target_program", "target_role"]),
            models.Index(fields=["target_bunk"]),
            models.Index(fields=["start_date", "end_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="core_supervision_end_date_gte_start_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.supervisor_membership} -> {self._target_repr()}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # Audit module fallback hooks (Step 7_4). Supervision rows have no direct
    # ``organization`` / ``program`` FK; both are derived through the
    # supervisor's Membership. These let ``bunk_logs.core.audit._org_program``
    # resolve the scope without a special-case branch.
    def _audit_organization(self):
        membership = self.supervisor_membership
        if membership is None or membership.program_id is None:
            return None
        return membership.program.organization

    def _audit_program(self):
        membership = self.supervisor_membership
        return membership.program if membership is not None else None

    def _target_repr(self) -> str:
        if self.target_type == self.TargetType.MEMBERSHIP:
            return f"membership:{self.target_membership_id}"
        if self.target_type == self.TargetType.ROLE_IN_PROGRAM:
            return f"role:{self.target_role}@program:{self.target_program_id}"
        return f"bunk:{self.target_bunk_id}"

    def is_active(self, today=None) -> bool:
        from django.utils import timezone

        ref = today or timezone.now().date()
        if self.start_date and self.start_date > ref:
            return False
        return not (self.end_date is not None and self.end_date < ref)

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}

        if self.supervisor_membership_id and (
            self.supervisor_membership.capability not in SUPERVISOR_CAPABILITIES
        ):
            errors["supervisor_membership"] = (
                "Supervisor must have a supervisor / program_lead / admin "
                f"capability (got {self.supervisor_membership.capability!r})."
            )

        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "End date must be on or after start date."

        # Target fields must match target_type. Exactly one set of fields is
        # required; the others must be empty so accidental cross-wiring is
        # caught at the model layer instead of via a runtime KeyError later.
        if self.target_type == self.TargetType.MEMBERSHIP:
            if not self.target_membership_id:
                errors["target_membership"] = (
                    "target_membership is required when target_type=MEMBERSHIP."
                )
            if self.target_role:
                errors["target_role"] = (
                    "target_role must be empty when target_type=MEMBERSHIP."
                )
            if self.target_program_id:
                errors["target_program"] = (
                    "target_program must be empty when target_type=MEMBERSHIP."
                )
            if self.target_bunk_id:
                errors["target_bunk"] = (
                    "target_bunk must be empty when target_type=MEMBERSHIP."
                )
        elif self.target_type == self.TargetType.ROLE_IN_PROGRAM:
            if not self.target_role:
                errors["target_role"] = (
                    "target_role is required when target_type=ROLE_IN_PROGRAM."
                )
            elif self.target_role not in {r for r, _ in Membership.ROLES}:
                errors["target_role"] = (
                    f"target_role {self.target_role!r} is not a known "
                    "Membership.role value."
                )
            if not self.target_program_id:
                errors["target_program"] = (
                    "target_program is required when target_type=ROLE_IN_PROGRAM."
                )
            if self.target_membership_id:
                errors["target_membership"] = (
                    "target_membership must be empty when target_type=ROLE_IN_PROGRAM."
                )
            if self.target_bunk_id:
                errors["target_bunk"] = (
                    "target_bunk must be empty when target_type=ROLE_IN_PROGRAM."
                )
        elif self.target_type == self.TargetType.BUNK:
            if not self.target_bunk_id:
                errors["target_bunk"] = (
                    "target_bunk is required when target_type=BUNK."
                )
            elif self.target_bunk.group_type != "bunk":
                errors["target_bunk"] = (
                    "target_bunk must be an AssignmentGroup with group_type='bunk'."
                )
            if self.target_membership_id:
                errors["target_membership"] = (
                    "target_membership must be empty when target_type=BUNK."
                )
            if self.target_program_id:
                errors["target_program"] = (
                    "target_program must be empty when target_type=BUNK."
                )
            if self.target_role:
                errors["target_role"] = (
                    "target_role must be empty when target_type=BUNK."
                )
        else:
            errors["target_type"] = f"Unknown target_type {self.target_type!r}."

        # Cross-organization checks: every leg of the relationship must live
        # in the same organization as the supervisor's program.
        sup_org_id = (
            self.supervisor_membership.program.organization_id
            if self.supervisor_membership_id
            else None
        )
        if sup_org_id is not None:
            if (
                self.target_membership_id
                and self.target_membership.program.organization_id != sup_org_id
            ):
                errors["target_membership"] = (
                    "Target Membership must belong to the same organization."
                )
            if (
                self.target_program_id
                and self.target_program.organization_id != sup_org_id
            ):
                errors["target_program"] = (
                    "Target Program must belong to the same organization."
                )
            if (
                self.target_bunk_id
                and self.target_bunk.organization_id != sup_org_id
            ):
                errors["target_bunk"] = (
                    "Target Bunk must belong to the same organization."
                )

        if errors:
            raise ValidationError(errors)


class SupervisionEvent(models.Model):
    """Append-only audit log for ``Supervision`` create / modify / end events.

    Forward-compatible stand-in for the cross-cutting ``AuditEvent`` model
    landing in Step 7_4. The column shape mirrors ``AuditEvent`` so the
    backfill is mechanical: copy rows over, point new writes at the audit
    module, then drop this table in a follow-up.
    """

    class EventType(models.TextChoices):
        CREATED = "created", "Supervision created"
        MODIFIED = "modified", "Supervision modified"
        ENDED = "ended", "Supervision ended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="supervision_events",
    )
    supervision = models.ForeignKey(
        Supervision,
        on_delete=models.CASCADE,
        related_name="events",
    )
    actor_membership = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervision_events_actor",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervision_events",
    )
    event_type = models.CharField(
        max_length=24,
        choices=EventType.choices,
        db_index=True,
    )
    before_state = models.JSONField(default=dict, blank=True)
    after_state = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SupervisionEventScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["supervision", "created_at"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} on supervision:{self.supervision_id}"


def record_supervision_event(
    *,
    supervision: Supervision,
    event_type: str,
    actor_membership: Membership | None = None,
    actor_user=None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    metadata: dict | None = None,
) -> SupervisionEvent:
    """Helper used by the API layer to write supervision audit rows.

    Lives next to the model so call sites stay terse and Step 7_4 has a
    single place to swap the implementation when ``AuditEvent`` lands.
    """
    org = supervision.supervisor_membership.program.organization
    return SupervisionEvent.all_objects.create(
        organization=org,
        supervision=supervision,
        actor_membership=actor_membership,
        actor_user=actor_user,
        event_type=event_type,
        before_state=before_state or {},
        after_state=after_state or {},
        metadata=metadata or {},
    )


def supervision_snapshot(supervision: Supervision) -> dict:
    """Compact, JSON-serializable snapshot of a Supervision row.

    Used for ``before_state`` / ``after_state`` in audit events. Kept here so
    the shape stays consistent across create / modify / end paths.
    """
    return {
        "supervisor_membership_id": supervision.supervisor_membership_id,
        "target_type": supervision.target_type,
        "target_membership_id": supervision.target_membership_id,
        "target_role": supervision.target_role,
        "target_program_id": supervision.target_program_id,
        "target_bunk_id": supervision.target_bunk_id,
        "start_date": (
            supervision.start_date.isoformat() if supervision.start_date else None
        ),
        "end_date": (
            supervision.end_date.isoformat() if supervision.end_date else None
        ),
    }


# ---------------------------------------------------------------------------
# Audit trail (Step 7_4)
# ---------------------------------------------------------------------------


class AuditEvent(models.Model):
    """Cross-cutting audit log -- the system of record for "who did what when".

    Per the canonical spec
    (``docs/user_stories/00_cross_cutting/audit_trail.md``), audit events are
    immutable: the default manager raises on ``update()`` / ``delete()`` to
    keep ViewSets and shell users honest. Use ``audit_module.created`` /
    ``edited`` / ``state_changed`` etc. helpers in
    :py:mod:`bunk_logs.core.audit` for the standard call sites; only
    migrations should call ``AuditEvent.all_objects.create`` (or
    ``bulk_create``) directly.

    ``content_type`` is the stable string label written by the producing
    code (e.g. ``order``, ``maintenance_ticket``, ``supervision``,
    ``reflection``, ``note``); ``content_id`` is the related row's UUID --
    audit rows for legacy int-PK content are out of scope until those
    models migrate to UUIDs.
    """

    class EventType(models.TextChoices):
        CREATED = "created", "Created"
        EDITED = "edited", "Edited"
        STATE_CHANGED = "state_changed", "State changed"
        DEACTIVATED = "deactivated", "Deactivated"
        REACTIVATED = "reactivated", "Reactivated"
        OVERRIDE_EDIT = "override_edit", "Admin override: edit"
        OVERRIDE_CLOSE = "override_close", "Admin override: close"
        OVERRIDE_RESOLVE = "override_resolve", "Admin override: resolve"
        AUDIT_VIEW = "audit_view", "Audit view (meta)"
        EXPORT = "export", "Export"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    actor_membership = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        help_text=(
            "Membership of the user who performed the action. Null for "
            "platform-support / migration writes that have no in-app actor."
        ),
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        help_text=(
            "User who performed the action -- captured even when no active "
            "Membership exists (e.g. Super Admins without an org admin row)."
        ),
    )
    event_type = models.CharField(
        max_length=24, choices=EventType.choices, db_index=True,
    )
    content_type = models.CharField(
        max_length=64,
        help_text="Stable label for the related model (e.g. 'order', 'reflection').",
    )
    content_id = models.CharField(
        max_length=64,
        help_text=(
            "Primary key of the related content row, serialised as a string. "
            "UUID-keyed content (Order, MaintenanceTicket) stores the UUID; "
            "int-keyed content (Reflection, Note, Supervision) stores the "
            "integer id. Synthetic events (e.g. EXPORT) may store an empty string."
        ),
        blank=True,
        default="",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    program = models.ForeignKey(
        Program,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    before_state = models.JSONField(default=dict, blank=True)
    after_state = models.JSONField(default=dict, blank=True)
    reason_note = models.TextField(blank=True, default="")
    is_admin_override = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = AuditEventScopedManager()
    all_objects = AuditEventAllManager()

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["content_type", "content_id", "created_at"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["actor_membership", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["is_admin_override", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} on {self.content_type}:{self.content_id}"

    def save(self, *args, **kwargs):
        # Application-layer immutability: once written, never rewritten.
        # ``self._state.adding`` is True for an INSERT and False for any
        # subsequent UPDATE, which is exactly what we want regardless of
        # whether ``pk`` was assigned client-side (UUID default).
        if not self._state.adding:
            msg = "AuditEvent rows are append-only; save() after creation is not permitted."
            raise NotImplementedError(msg)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        msg = "AuditEvent rows are append-only; delete() is not permitted."
        raise NotImplementedError(msg)


def reflection_snapshot(reflection: "Reflection") -> dict:
    """Compact, JSON-serializable snapshot of a Reflection for audit before/after.

    Captures only the fields a reviewer cares about when inspecting an edit
    -- the answers payload, the language, the privacy toggle, completion
    state. The template / subject / author are immutable post-create.
    """
    return {
        "answers": reflection.answers,
        "language": reflection.language,
        "team_visibility": reflection.team_visibility,
        "is_complete": reflection.is_complete,
        "is_sensitive": reflection.is_sensitive,
        "updated_at": (
            reflection.updated_at.isoformat()
            if getattr(reflection, "updated_at", None)
            else None
        ),
    }


def note_snapshot(note: "Note") -> dict:
    """Compact, JSON-serializable snapshot of a Note for audit before/after."""
    return {
        "body": note.body,
        "is_sensitive": note.is_sensitive,
        "maintenance_visibility": note.maintenance_visibility,
        "language": note.language,
        "updated_at": (
            note.updated_at.isoformat()
            if getattr(note, "updated_at", None)
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Auto-translation (Step 7_5)
# ---------------------------------------------------------------------------


class TranslationRecord(models.Model):
    """Server-generated English translation of a non-English content row.

    Per ``docs/user_stories/00_cross_cutting/i18n.md``: every Reflection /
    Note submitted with ``language != 'en'`` enqueues an Anthropic-backed
    Celery task that persists its result here. Readers consume the
    *latest* row per (content_type, content_id) -- historical rows stay
    on disk for up to 90 days so audit reviewers can see how a piece of
    content was translated over successive edits, then the nightly GC
    task (``bunk_logs.core.translation.tasks.purge_expired_translations``)
    drops anything older.

    Statuses follow the Story 44 reader-side state machine: ``pending``
    -> ``completed`` for the happy path, ``failed_retryable`` while
    Celery is backing off, ``failed_terminal`` after exhausting the
    retry budget. The serializer in ``bunk_logs.api.reflections``
    surfaces these directly so the frontend ``TranslationDisplay``
    component can render the right state without further translation.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED_RETRYABLE = "failed_retryable", "Failed (retrying)"
        FAILED_TERMINAL = "failed_terminal", "Failed (terminal)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="translation_records",
    )
    content_type = models.CharField(
        max_length=64,
        help_text="Stable label for the translated model ('reflection' or 'note').",
    )
    content_id = models.CharField(
        max_length=64,
        help_text=(
            "PK of the translated content row, serialised as a string -- "
            "matches the ``AuditEvent.content_id`` convention."
        ),
    )
    source_language = models.CharField(
        max_length=10,
        choices=Person.LANGUAGE_CHOICES,
        help_text="ISO code of the original content language ('es' or 'he').",
    )
    target_language = models.CharField(
        max_length=10,
        choices=Person.LANGUAGE_CHOICES,
        default="en",
        help_text="ISO code of the translation target. Tier 1 is English-only.",
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    translated_text = models.TextField(
        blank=True,
        default="",
        help_text="English translation. Empty while ``status='pending'``.",
    )
    model_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text=(
            "Identifier of the Anthropic model that produced the translation "
            "(e.g. 'claude-sonnet-4-5'). Captured for reproducibility."
        ),
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    tokens_used = models.PositiveIntegerField(
        default=0,
        help_text="Total input+output tokens reported by the Anthropic response.",
    )
    last_error = models.TextField(
        blank=True,
        default="",
        help_text="Exception message captured on the most recent failed attempt.",
    )
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Currently-enqueued Celery task id, so re-translation on edit "
            "can revoke the pending task before queueing a fresh one."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "content_id", "-created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"TranslationRecord({self.content_type}:{self.content_id} "
            f"{self.source_language}->{self.target_language} {self.status})"
        )

    @classmethod
    def latest_for(cls, content_type: str, content_id) -> "TranslationRecord | None":
        """Return the most recent TranslationRecord for a content row, or None."""
        return (
            cls.all_objects.filter(
                content_type=content_type, content_id=str(content_id),
            )
            .order_by("-created_at")
            .first()
        )


# ---------------------------------------------------------------------------
# Leadership Team — attention markers (Step 7_12)
# ---------------------------------------------------------------------------


class ReflectionAttentionMarker(models.Model):
    """Per-supervisor "needs attention" annotation on a Reflection (Story 46 c5).

    Markers are visible to the supervisor who placed them AND to anyone
    sharing a same-target Supervision (co-supervisor scope). They do NOT
    mutate the reflection itself and do NOT notify the author. The
    canonical product spec is ``docs/user_stories/07_leadership_team/STORIES.md``.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="reflection_attention_markers",
    )
    reflection = models.ForeignKey(
        Reflection,
        on_delete=models.CASCADE,
        related_name="attention_markers",
    )
    marker_membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="attention_markers_placed",
        help_text="Supervisor Membership that placed the marker.",
    )
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OrgScopedManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        unique_together = [("reflection", "marker_membership")]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reflection", "created_at"]),
            models.Index(fields=["marker_membership", "created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"attention marker on reflection:{self.reflection_id} "
            f"by membership:{self.marker_membership_id}"
        )

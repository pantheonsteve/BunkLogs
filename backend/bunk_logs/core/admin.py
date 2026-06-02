from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.widgets import AdminTextareaWidget
from django.db import models
from django.shortcuts import render

from .admin_organization import AUTHOR_SCOPE_FIELD_PREFIX
from .admin_organization import AUTHOR_SCOPE_HELP
from .admin_organization import MembershipSubjectNoteAuthorField
from .admin_organization import OrganizationAdminForm
from .admin_organization import apply_membership_author_override
from .admin_organization import membership_author_override_initial
from .models import AssignmentDashboardGrant
from .models import AssignmentGroup
from .models import AssignmentGroupMembership
from .models import FieldKey
from .models import Membership
from .models import Organization
from .models import Person
from .models import Program
from .models import Reflection
from .models import ReflectionTemplate
from .models import RosterImportLog
from .models import TemplateAssignment


class ProgramAdminForm(forms.ModelForm):
    """Normalize titles in admin so staff can type a short label; model still enforces the rule."""

    class Meta:
        model = Program
        fields = (
            "organization",
            "name",
            "slug",
            "program_type",
            "start_date",
            "end_date",
            "is_active",
            "settings",
        )

    def clean(self):
        super().clean()
        org = self.cleaned_data.get("organization")
        name = (self.cleaned_data.get("name") or "").strip()
        if not org or not name:
            return self.cleaned_data
        oname = (org.name or "").strip()
        if oname and not name.startswith(oname):
            self.cleaned_data["name"] = f"{oname} - {name}"
        return self.cleaned_data


class ProgramInlineForm(forms.ModelForm):
    """Inline variant — organization is implied by the parent Organization row."""

    class Meta:
        model = Program
        fields = ("name", "slug", "program_type", "start_date", "end_date", "is_active")

    def __init__(self, *args, parent_organization=None, **kwargs):
        self.parent_organization = parent_organization
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        org = getattr(self.instance, "organization", None) or self.parent_organization
        name = (self.cleaned_data.get("name") or "").strip()
        if not org or not name:
            return self.cleaned_data
        oname = (org.name or "").strip()
        if oname and not name.startswith(oname):
            self.cleaned_data["name"] = f"{oname} - {name}"
        return self.cleaned_data


class ProgramInline(admin.TabularInline):
    model = Program
    form = ProgramInlineForm
    extra = 0
    show_change_link = True
    fields = ("name", "slug", "program_type", "start_date", "end_date", "is_active")

    def get_queryset(self, request):
        return Program.all_objects.select_related("organization")

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)
        parent_org = obj
        form_class = self.form

        class WrappedProgramInlineForm(form_class):
            def __init__(self, *args, **kwargs):
                kwargs.setdefault("parent_organization", parent_org)
                super().__init__(*args, **kwargs)

        FormSet.form = WrappedProgramInlineForm
        return FormSet


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    form = OrganizationAdminForm
    list_display = ["name", "slug", "is_active", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "slug"]
    list_filter = ["is_active"]
    inlines = [ProgramInline]
    readonly_fields = ["created_at", "updated_at"]

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """Pin tenant context to the org being edited so inline Program rows validate."""
        from bunk_logs.core.context import clear_current_organization
        from bunk_logs.core.context import set_current_organization

        org = self.get_object(request, object_id) if object_id else None
        if org is not None:
            set_current_organization(org)
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        finally:
            if org is not None:
                clear_current_organization()

    def get_fieldsets(self, request, obj=None):
        role_fields = tuple(
            f"{AUTHOR_SCOPE_FIELD_PREFIX}{role_value}"
            for role_value, _ in Membership.ROLES
        )
        return (
            (None, {"fields": ("name", "slug", "is_active")}),
            (
                "Subject note authoring by role",
                {
                    "fields": role_fields,
                    "description": AUTHOR_SCOPE_HELP,
                },
            ),
            (
                "Advanced",
                {
                    "fields": ("settings_json",),
                    "classes": ("collapse",),
                },
            ),
            (
                "Timestamps",
                {
                    "fields": ("created_at", "updated_at"),
                    "classes": ("collapse",),
                },
            ),
        )


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return Person.all_objects.all()

    list_display = [
        "full_name",
        "organization",
        "email",
        "user",
        "created_at",
    ]
    list_filter = ["organization"]
    search_fields = ["first_name", "last_name", "preferred_name", "email"]
    autocomplete_fields = ["organization", "user"]
    readonly_fields = ["created_at"]


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    form = ProgramAdminForm

    def get_queryset(self, request):
        return Program.all_objects.select_related("organization")

    list_display = [
        "organization",
        "name",
        "slug",
        "program_type",
        "start_date",
        "end_date",
        "is_active",
    ]
    list_filter = ["organization", "program_type", "is_active"]
    search_fields = ["name", "slug", "organization__name", "organization__slug"]
    ordering = ("organization__name", "-start_date", "name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["organization"]


class AssignmentGroupMembershipInline(admin.TabularInline):
    model = AssignmentGroupMembership
    extra = 0
    fields = ("person", "role_in_group", "is_active", "start_date", "end_date")
    autocomplete_fields = ("person",)

    def get_queryset(self, request):
        return AssignmentGroupMembership.all_objects.select_related("person")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "person":
            kwargs.setdefault("queryset", Person.all_objects.order_by("last_name", "first_name"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(AssignmentGroup)
class AssignmentGroupAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return AssignmentGroup.all_objects.select_related("organization", "program", "parent")

    list_display = ["name", "group_type", "program", "organization", "parent", "is_active"]
    list_filter = ["group_type", "program__organization", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["organization", "program"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [AssignmentGroupMembershipInline]

    actions = ["deactivate_groups"]

    @admin.action(description="Deactivate selected groups")
    def deactivate_groups(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} group(s).")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "program":
            kwargs.setdefault("queryset", Program.all_objects.select_related("organization"))
        if db_field.name == "parent":
            kwargs.setdefault("queryset", AssignmentGroup.all_objects.select_related("program"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(AssignmentGroupMembership)
class AssignmentGroupMembershipAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return AssignmentGroupMembership.all_objects.select_related("group__organization", "person")

    list_display = ["person", "group", "role_in_group", "is_active", "start_date", "end_date"]
    list_filter = ["role_in_group", "is_active", "group__organization"]
    search_fields = [
        "person__first_name",
        "person__last_name",
        "person__preferred_name",
        "group__name",
    ]
    autocomplete_fields = ["group", "person"]
    readonly_fields = ["created_at"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "group":
            kwargs.setdefault("queryset", AssignmentGroup.all_objects.select_related("program__organization"))
        elif db_field.name == "person":
            kwargs.setdefault("queryset", Person.all_objects.select_related("organization"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ReflectionTemplateAdminForm(forms.ModelForm):
    class Meta:
        model = ReflectionTemplate
        fields = (
            "organization",
            "program_type",
            "role",
            "name",
            "slug",
            "description",
            "cadence",
            "schema",
            "languages",
            "is_active",
            "version",
            "parent_template",
            "subject_mode",
            "assignment_scope",
            "assignment_group_types",
            "author_role_filter",
            "subject_role_filter",
            "required_per_subject_per_period",
            "subject_visible",
        )


@admin.register(ReflectionTemplate)
class ReflectionTemplateAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return ReflectionTemplate.all_objects.all()

    form = ReflectionTemplateAdminForm
    formfield_overrides = {
        models.JSONField: {
            "widget": AdminTextareaWidget(
                attrs={
                    "rows": 22,
                    "cols": 100,
                    "style": "font-family: monospace; font-size: 12px;",
                },
            ),
        },
    }
    list_display = [
        "name",
        "slug",
        "version",
        "organization",
        "program_type",
        "role",
        "cadence",
        "is_active",
        "created_at",
    ]
    list_filter = ["cadence", "is_active", "program_type", "organization"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["organization", "parent_template"]
    readonly_fields = ["created_at"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent_template":
            kwargs.setdefault("queryset", ReflectionTemplate.all_objects.all())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(TemplateAssignment)
class TemplateAssignmentAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return TemplateAssignment.all_objects.select_related(
            "organization", "program", "template", "assignment_group", "created_by__person",
        )

    formfield_overrides = {
        models.JSONField: {
            "widget": AdminTextareaWidget(
                attrs={
                    "rows": 6,
                    "cols": 80,
                    "style": "font-family: monospace; font-size: 12px;",
                },
            ),
        },
    }
    list_display = [
        "id",
        "template",
        "organization",
        "program",
        "target_type",
        "status",
        "is_required",
        "start_date",
        "end_date",
        "created_at",
    ]
    list_filter = ["status", "target_type", "is_required", "organization"]
    search_fields = ["title", "template__name", "template__slug"]
    autocomplete_fields = ["organization", "program", "template", "assignment_group", "replaces"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "start_date"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "program":
            kwargs.setdefault("queryset", Program.all_objects.select_related("organization"))
        elif db_field.name == "template":
            kwargs.setdefault("queryset", ReflectionTemplate.all_objects.all())
        elif db_field.name == "assignment_group":
            kwargs.setdefault("queryset", AssignmentGroup.all_objects.select_related("program"))
        elif db_field.name == "replaces":
            kwargs.setdefault("queryset", TemplateAssignment.all_objects.all())
        elif db_field.name == "created_by":
            kwargs.setdefault(
                "queryset",
                Membership.all_objects.select_related("person", "program"),
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(AssignmentDashboardGrant)
class AssignmentDashboardGrantAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return AssignmentDashboardGrant.objects.select_related(
            "organization", "assignment__template", "membership__person", "granted_by__person",
        )

    list_display = ["id", "assignment", "membership", "organization", "granted_by", "created_at"]
    list_filter = ["organization"]
    search_fields = [
        "assignment__title",
        "assignment__template__name",
        "membership__person__first_name",
        "membership__person__last_name",
    ]
    autocomplete_fields = ["organization", "assignment", "membership", "granted_by"]
    readonly_fields = ["created_at"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assignment":
            kwargs.setdefault("queryset", TemplateAssignment.all_objects.select_related("template"))
        elif db_field.name in ("membership", "granted_by"):
            kwargs.setdefault(
                "queryset",
                Membership.all_objects.select_related("person", "program"),
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Reflection)
class ReflectionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return Reflection.all_objects.select_related(
            "program__organization", "subject", "author", "template", "assignment_group",
        )

    @admin.display(description="Organization", ordering="program__organization__name")
    def program_organization_name(self, obj):
        return obj.program.organization.name

    list_display = [
        "subject",
        "author",
        "program_organization_name",
        "program",
        "template",
        "assignment_group",
        "period_start",
        "period_end",
        "language",
        "is_complete",
        "submitted_at",
    ]
    list_filter = [
        "program__organization",
        "template",
        "template__role",
        "period_end",
        "is_complete",
        "language",
    ]
    search_fields = [
        "subject__first_name",
        "subject__last_name",
        "subject__preferred_name",
        "author__first_name",
        "author__last_name",
        "program__name",
        "template__name",
        "template__slug",
    ]
    autocomplete_fields = ["organization", "program", "subject", "author", "template", "submitted_by", "assignment_group"]
    readonly_fields = ["submitted_at", "updated_at", "submission_id"]
    date_hierarchy = "period_end"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "program":
            kwargs.setdefault(
                "queryset",
                Program.all_objects.select_related("organization"),
            )
        elif db_field.name in ("subject", "author"):
            kwargs.setdefault(
                "queryset",
                Person.all_objects.select_related("organization"),
            )
        elif db_field.name == "template":
            kwargs.setdefault("queryset", ReflectionTemplate.all_objects.all())
        elif db_field.name == "assignment_group":
            kwargs.setdefault("queryset", AssignmentGroup.all_objects.select_related("program"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(FieldKey)
class FieldKeyAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return FieldKey.all_objects.select_related("organization")

    list_display = [
        "key",
        "display_name",
        "organization",
        "expected_field_type",
        "expected_dashboard_role",
        "created_at",
    ]
    list_filter = ["organization", "expected_field_type", "expected_dashboard_role"]
    search_fields = ["key", "display_name", "description"]
    autocomplete_fields = ["organization"]
    readonly_fields = ["created_at"]

    @admin.display(description="Scope")
    def scope(self, obj):
        return "global" if obj.organization_id is None else obj.organization.slug


@admin.register(RosterImportLog)
class RosterImportLogAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return RosterImportLog.all_objects.select_related("organization", "program", "initiated_by")

    list_display = ["importer_type", "program", "organization", "status", "csv_filename", "started_at", "completed_at"]
    list_filter = ["importer_type", "status", "organization"]
    search_fields = ["csv_filename", "program__name"]
    readonly_fields = ["started_at", "completed_at", "summary", "status"]

    def has_add_permission(self, request):
        return False


def _normalize_tags(values) -> list[str]:
    """Lowercase, strip, dedupe (preserving order)."""
    seen: set[str] = set()
    result: list[str] = []
    for v in values:
        if v is None:
            continue
        t = str(v).strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        result.append(t)
    return result


def _parse_tag_input(text: str) -> list[str]:
    """Accept comma- or newline-separated text and return a normalized tag list."""
    if not text:
        return []
    parts = [p.strip() for chunk in text.replace("\n", ",").split(",") for p in [chunk]]
    return _normalize_tags(parts)


class MembershipTagsWidget(forms.Textarea):
    """Render the JSON list of tags as comma-separated text for editing in admin."""

    def format_value(self, value):
        if isinstance(value, list):
            return ", ".join(str(t) for t in value)
        if isinstance(value, str) and value.startswith("["):
            try:
                import json

                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return ", ".join(str(t) for t in parsed)
            except (ValueError, TypeError):
                pass
        return super().format_value(value)


class MembershipTagsField(forms.Field):
    widget = MembershipTagsWidget(attrs={"rows": 2, "cols": 60})

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault(
            "help_text",
            "Comma- or newline-separated tags (e.g. international, waterfront).",
        )
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return _normalize_tags(value)
        return _parse_tag_input(str(value))

    def prepare_value(self, value):
        if isinstance(value, list):
            return ", ".join(str(t) for t in value)
        return value


class MembershipAdminForm(forms.ModelForm):
    tags = MembershipTagsField()
    subject_note_author_override = MembershipSubjectNoteAuthorField()

    class Meta:
        model = Membership
        fields = (
            "program",
            "person",
            "role",
            "grade_level",
            "tags",
            "start_date",
            "end_date",
            "is_active",
            "subject_note_author_override",
            "metadata",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["subject_note_author_override"].initial = (
                membership_author_override_initial(self.instance.metadata)
            )

    def save(self, commit=True):
        membership = super().save(commit=False)
        override = self.cleaned_data.get("subject_note_author_override", "")
        membership.metadata = apply_membership_author_override(
            membership.metadata,
            override,
        )
        if commit:
            membership.save()
        return membership


class BulkTagForm(forms.Form):
    OP_CHOICES = (
        ("add", "Add tag(s) to selected"),
        ("remove", "Remove tag(s) from selected"),
    )
    operation = forms.ChoiceField(choices=OP_CHOICES)
    tags_text = forms.CharField(
        label="Tags",
        widget=forms.Textarea(attrs={"rows": 2, "cols": 60}),
        help_text="Comma- or newline-separated tags.",
    )


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    form = MembershipAdminForm
    actions = ["bulk_edit_tags"]

    def get_queryset(self, request):
        return Membership.all_objects.select_related("program__organization", "person")

    @admin.display(description="Organization", ordering="program__organization__name")
    def program_organization_name(self, obj):
        return obj.program.organization.name

    @admin.display(description="Tags")
    def tags_display(self, obj):
        if not obj.tags:
            return "—"
        return ", ".join(str(t) for t in obj.tags)

    list_display = [
        "person",
        "program_organization_name",
        "program",
        "role",
        "capability",
        "tags_display",
        "grade_level",
        "is_active",
        "start_date",
        "end_date",
        "created_at",
    ]
    list_filter = ["role", "capability", "is_active", "program__organization"]
    search_fields = [
        "person__first_name",
        "person__last_name",
        "person__preferred_name",
        "person__email",
        "program__name",
        "tags",
    ]
    autocomplete_fields = ["program", "person"]
    readonly_fields = ["capability", "created_at"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # The admin is privileged staff territory; bypass OrgScopedManager so the
        # form's FK validation works even when the logged-in user has no Person
        # record (i.e. request.organization is None). The admin changelist itself
        # already uses all_objects via get_queryset.
        if db_field.name == "program":
            kwargs.setdefault(
                "queryset",
                Program.all_objects.select_related("organization"),
            )
        elif db_field.name == "person":
            kwargs.setdefault(
                "queryset",
                Person.all_objects.select_related("organization"),
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.action(description="Edit tags on selected memberships")
    def bulk_edit_tags(self, request, queryset):
        if "apply" in request.POST:
            form = BulkTagForm(request.POST)
            if form.is_valid():
                tags = _parse_tag_input(form.cleaned_data["tags_text"])
                op = form.cleaned_data["operation"]
                updated = 0
                for membership in queryset:
                    current = list(membership.tags or [])
                    if op == "add":
                        new = _normalize_tags([*current, *tags])
                    else:
                        remove = set(tags)
                        new = [t for t in _normalize_tags(current) if t not in remove]
                    if new != current:
                        membership.tags = new
                        membership.save(update_fields=["tags"])
                        updated += 1
                self.message_user(
                    request,
                    f"Updated tags on {updated} membership(s).",
                    messages.SUCCESS,
                )
                return None
        else:
            form = BulkTagForm()

        return render(
            request,
            "admin/core/membership/bulk_tag_action.html",
            context={
                "form": form,
                "memberships": queryset,
                "action_name": "bulk_edit_tags",
            },
        )

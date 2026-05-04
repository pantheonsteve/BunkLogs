from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.widgets import AdminTextareaWidget
from django.db import models
from django.shortcuts import render

from .models import Membership
from .models import Organization
from .models import Person
from .models import Program
from .models import Reflection
from .models import ReflectionTemplate


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


class ProgramInline(admin.TabularInline):
    model = Program
    form = ProgramAdminForm
    extra = 0
    show_change_link = True
    fields = ("name", "slug", "program_type", "start_date", "end_date", "is_active")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "slug"]
    list_filter = ["is_active"]
    inlines = [ProgramInline]


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


@admin.register(Reflection)
class ReflectionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return Reflection.all_objects.select_related("program__organization", "person", "template")

    @admin.display(description="Organization", ordering="program__organization__name")
    def program_organization_name(self, obj):
        return obj.program.organization.name

    list_display = [
        "person",
        "program_organization_name",
        "program",
        "template",
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
        "person__first_name",
        "person__last_name",
        "person__preferred_name",
        "program__name",
        "template__name",
        "template__slug",
    ]
    autocomplete_fields = ["organization", "program", "person", "template", "submitted_by"]
    readonly_fields = ["submitted_at", "updated_at"]
    date_hierarchy = "period_end"


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
            "metadata",
        )


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
        "tags_display",
        "grade_level",
        "is_active",
        "start_date",
        "end_date",
        "created_at",
    ]
    list_filter = ["role", "is_active", "program__organization"]
    search_fields = [
        "person__first_name",
        "person__last_name",
        "person__preferred_name",
        "person__email",
        "program__name",
        "tags",
    ]
    autocomplete_fields = ["program", "person"]
    readonly_fields = ["created_at"]

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

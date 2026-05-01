from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminTextareaWidget
from django.db import models

from .models import Membership
from .models import Organization
from .models import Person
from .models import Program
from .models import Reflection
from .models import ReflectionTemplate


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "slug"]
    list_filter = ["is_active"]


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
    def get_queryset(self, request):
        return Program.all_objects.all()

    list_display = [
        "name",
        "slug",
        "organization",
        "program_type",
        "start_date",
        "end_date",
        "is_active",
    ]
    list_filter = ["program_type", "is_active"]
    search_fields = ["name", "slug"]
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
        return Reflection.all_objects.all()

    list_display = [
        "person",
        "program",
        "template",
        "period_start",
        "period_end",
        "language",
        "is_complete",
        "submitted_at",
    ]
    list_filter = [
        "program",
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


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return Membership.all_objects.all()

    list_display = [
        "person",
        "program",
        "role",
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
    ]
    autocomplete_fields = ["program", "person"]
    readonly_fields = ["created_at"]

from django.contrib import admin

from .models import Membership
from .models import Organization
from .models import Person
from .models import Program


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "slug"]
    list_filter = ["is_active"]


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
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


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
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

"""Admin registrations for the Observation entity and its satellites.

These models all use OrgScopedManager as ``objects``; the admin must read and
write through ``all_objects`` so staff aren't filtered by request tenant.
"""

from django.contrib import admin

from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

from .models import Observation
from .models import ObservationArchive
from .models import ObservationReadReceipt
from .models import ObservationRecipient
from .models import ObservationReply
from .models import ObservationSubject


class ObservationSubjectInline(admin.TabularInline):
    model = ObservationSubject
    extra = 0
    autocomplete_fields = ["subject"]

    def get_queryset(self, request):
        return ObservationSubject.objects.select_related("subject")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "subject":
            kwargs.setdefault("queryset", Person.all_objects.select_related("organization"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ObservationRecipientInline(admin.TabularInline):
    model = ObservationRecipient
    extra = 0
    fields = ("person", "option_key", "bunk_id_at_capture")
    autocomplete_fields = ["person"]

    def get_queryset(self, request):
        return ObservationRecipient.objects.select_related("person")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "person":
            kwargs.setdefault("queryset", Person.all_objects.select_related("organization"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ObservationReplyInline(admin.TabularInline):
    model = ObservationReply
    extra = 0
    fields = ("author", "author_role_at_write", "body", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ["author"]

    def get_queryset(self, request):
        return ObservationReply.objects.select_related("author")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs.setdefault("queryset", Person.all_objects.select_related("organization"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return Observation.all_objects.select_related(
            "organization", "program", "author", "amendment_of",
        )

    list_display = [
        "id",
        "organization",
        "program",
        "author",
        "sensitivity",
        "context",
        "subject_visible",
        "language",
        "created_at",
    ]
    list_filter = ["organization", "sensitivity", "subject_visible", "language", "context"]
    search_fields = [
        "body",
        "author__first_name",
        "author__last_name",
        "author__preferred_name",
        "context",
    ]
    autocomplete_fields = ["organization", "program", "author", "amendment_of"]
    readonly_fields = ["created_at", "updated_at", "legacy_source"]
    date_hierarchy = "created_at"
    inlines = [ObservationSubjectInline, ObservationRecipientInline, ObservationReplyInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "program":
            kwargs.setdefault("queryset", Program.all_objects.select_related("organization"))
        elif db_field.name == "author":
            kwargs.setdefault("queryset", Person.all_objects.select_related("organization"))
        elif db_field.name == "amendment_of":
            kwargs.setdefault("queryset", Observation.all_objects.all())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ObservationReply)
class ObservationReplyAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return ObservationReply.objects.select_related("observation", "author")

    list_display = ["id", "observation", "author", "author_role_at_write", "created_at"]
    list_filter = ["author_role_at_write"]
    search_fields = ["body", "author__first_name", "author__last_name"]
    autocomplete_fields = ["observation", "author"]
    readonly_fields = ["created_at"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs.setdefault("queryset", Person.all_objects.select_related("organization"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ObservationReadReceipt)
class ObservationReadReceiptAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return ObservationReadReceipt.objects.select_related("observation", "person")

    list_display = ["id", "observation", "person", "last_read_at", "last_read_entry_id"]
    search_fields = ["person__first_name", "person__last_name"]
    autocomplete_fields = ["observation", "person"]


@admin.register(ObservationArchive)
class ObservationArchiveAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return ObservationArchive.objects.select_related("observation", "person")

    list_display = ["id", "observation", "person", "archived_at"]
    search_fields = ["person__first_name", "person__last_name"]
    autocomplete_fields = ["observation", "person"]
    readonly_fields = ["archived_at"]

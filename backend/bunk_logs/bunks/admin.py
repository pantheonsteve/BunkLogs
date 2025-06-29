import tempfile
from pathlib import Path

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import path
from django.urls import reverse

from .forms import BunkCsvImportForm
from .forms import CabinCsvImportForm
from .forms import UnitCsvImportForm
from .forms import UnitForm
from .forms import CounselorBunkAssignmentCsvImportForm
from .forms import UnitStaffAssignmentCsvImportForm
from .models import Bunk
from .models import Cabin
from .models import Session
from .models import Unit
from .models import UnitStaffAssignment
from .models import CounselorBunkAssignment
from .services.imports import import_bunks_from_csv
from .services.imports import import_cabins_from_csv
from .services.imports import import_units_from_csv
from .services.imports import import_counselor_bunk_assignments_from_csv
from .services.imports import import_unit_staff_assignments_from_csv
from bunk_logs.utils.admin import TestDataAdminMixin


@admin.register(Unit)
class UnitAdmin(TestDataAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "get_primary_unit_head",
        "get_primary_camper_care",
        "created_at",
        "updated_at",
    )
    search_fields = ("name",)
    list_filter = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    
    def get_primary_unit_head(self, obj):
        """Display the primary unit head."""
        unit_head = obj.primary_unit_head
        if unit_head:
            return f"{unit_head.get_full_name()} ({unit_head.email})"
        return "None"
    get_primary_unit_head.short_description = "Primary Unit Head"
    
    def get_primary_camper_care(self, obj):
        """Display the primary camper care."""
        camper_care = obj.primary_camper_care
        if camper_care:
            return f"{camper_care.get_full_name()} ({camper_care.email})"
        return "None"
    get_primary_camper_care.short_description = "Primary Camper Care"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-units/", self.import_units, name="unit_import_csv"),
        ]
        return custom_urls + urls

    def import_units(self, request):
        if request.method == "POST":
            form = UnitCsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]

                # Save the uploaded file to a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                # Process the CSV file
                result = import_units_from_csv(temp_path, dry_run=dry_run)

                if dry_run:
                    messages.info(
                        request,
                        "Dry run completed. "
                        f"{result['success_count']} units would be imported.",
                    )
                else:
                    messages.success(
                        request,
                        f"Successfully imported {result['success_count']} units.",
                    )

                if result["error_count"] > 0:
                    for error in result["errors"]:
                        messages.error(
                            request,
                            f"Error in row {error['row']}: {error['error']}",
                        )

                # Clean up the temporary file
                temp_path.unlink(missing_ok=True)

                return redirect("admin:bunks_unit_changelist")
        else:
            form = UnitCsvImportForm()

            # ruff: noqa: SLF001
        context = {
            "form": form,
            "title": "Import Units from CSV",
            # Django admin templates use opts by convention
            "opts": self.model._meta,  # Required by Django admin templates
            "app_label": self.model._meta.app_label,
            "model_name": self.model._meta.model_name,
        }
        return render(request, "admin/csv_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_units"] = reverse("admin:unit_import_csv")
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(UnitStaffAssignment)
class UnitStaffAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "unit",
        "staff_member",
        "role",
        "is_primary",
        "start_date",
        "end_date",
        "created_at",
    )
    list_filter = ("role", "is_primary", "start_date", "end_date", "created_at")
    search_fields = ("unit__name", "staff_member__first_name", "staff_member__last_name", "staff_member__email")
    autocomplete_fields = ["unit", "staff_member"]
    date_hierarchy = "start_date"
    
    fieldsets = (
        (None, {
            "fields": ("unit", "staff_member", "role", "is_primary")
        }),
        ("Dates", {
            "fields": ("start_date", "end_date")
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('unit', 'staff_member')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-assignments/",
                self.import_assignments,
                name="unitstaffassignment_import_csv",
            ),
        ]
        return custom_urls + urls

    def import_assignments(self, request):
        if request.method == "POST":
            form = UnitStaffAssignmentCsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]

                # Save the uploaded file to a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                result = import_unit_staff_assignments_from_csv(temp_path, dry_run=dry_run)

                if dry_run:
                    messages.info(
                        request,
                        f"Dry run completed. {result['success_count']} assignments would be imported.",
                    )
                else:
                    messages.success(
                        request,
                        f"Successfully imported {result['success_count']} assignments.",
                    )

                if result["error_count"] > 0:
                    for error in result["errors"]:
                        messages.error(
                            request,
                            f"Row {error['row']}: {error['error']}",
                        )

                # Clean up the temporary file
                temp_path.unlink(missing_ok=True)

                return redirect("admin:bunks_unitstaffassignment_changelist")
        else:
            form = UnitStaffAssignmentCsvImportForm()

        context = {
            "form": form,
            "title": "Import Unit Staff Assignments",
            "opts": self.model._meta,
            "app_label": self.model._meta.app_label,
            "model_name": self.model._meta.model_name,
        }
        return render(request, "admin/csv_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_assignments"] = reverse("admin:unitstaffassignment_import_csv")
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Cabin)
class CabinAdmin(TestDataAdminMixin, admin.ModelAdmin):
    list_display = ("name", "capacity", "location", "notes")  # Adjust fields as needed
    search_fields = ("name", "location")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-cabins/", self.import_cabins, name="cabin_import_csv"),
        ]
        return custom_urls + urls

    def import_cabins(self, request):
        if request.method == "POST":
            form = CabinCsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]

                # Save the uploaded file to a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                # Process the CSV file
                result = import_cabins_from_csv(temp_path, dry_run=dry_run)

                if dry_run:
                    messages.info(
                        request,
                        "Dry run completed. "
                        f"{result['success_count']} cabins would be imported.",
                    )
                else:
                    messages.success(
                        request,
                        f"Successfully imported {result['success_count']} cabins.",
                    )

                if result["error_count"] > 0:
                    for error in result["errors"]:
                        messages.error(
                            request,
                            f"Error in row {error['row']}: {error['error']}",
                        )

                # Clean up the temporary file
                temp_path.unlink(missing_ok=True)

                return redirect("admin:bunks_cabin_changelist")
        else:
            form = CabinCsvImportForm()

        # ruff: noqa: SLF001
        context = {
            "form": form,
            "title": "Import Cabins from CSV",
            # Django admin templates use opts by convention
            "opts": self.model._meta,  # Required by Django admin templates
            "app_label": self.model._meta.app_label,
            "model_name": self.model._meta.model_name,
        }
        return render(request, "admin/csv_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_cabins"] = reverse("admin:cabin_import_csv")
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Session)
class SessionAdmin(TestDataAdminMixin, admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")  # Adjust fields as needed
    search_fields = ("name", "start_date", "end_date")


class CounselorBunkAssignmentInline(admin.TabularInline):
    model = CounselorBunkAssignment
    extra = 0
    autocomplete_fields = ["counselor"]
    fields = ["counselor", "start_date", "end_date", "is_primary"]


@admin.register(Bunk)
class BunkAdmin(TestDataAdminMixin, admin.ModelAdmin):
    list_display = ("name", "cabin", "session", "unit", "is_active", "get_current_counselors_display", "is_test_data_colored")
    list_filter = ("is_active", "session", "cabin", "unit")
    search_fields = ("cabin__name", "session__name")
    actions = ["activate_bunks", "deactivate_bunks"]
    inlines = [CounselorBunkAssignmentInline]
    
    def get_current_counselors_display(self, obj):
        """Display current counselors"""
        counselors = obj.get_current_counselors()
        if counselors:
            names = [counselor.get_full_name() for counselor in counselors]
            return ", ".join(names)
        return "None"
    get_current_counselors_display.short_description = "Current Counselors"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-bunks/", self.import_bunks, name="bunk_import_csv"),
        ]
        return custom_urls + urls

    def import_bunks(self, request):
        if request.method == "POST":
            form = BunkCsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]
                # Save the uploaded file to a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                # Process the CSV file
                result = import_bunks_from_csv(temp_path, dry_run=dry_run)

                if dry_run:
                    messages.info(
                        request,
                        "Dry run completed. "
                        f"{result['created']} bunks would be imported.",
                    )
                else:
                    messages.success(
                        request,
                        f"Successfully imported {result['created']} bunks.",
                    )
                if result["errors"]:
                    for error in result["errors"]:
                        messages.error(
                            request,
                            f"Error: {error}",
                        )
                # Clean up the temporary file
                temp_path.unlink(missing_ok=True)
                return redirect("admin:bunks_bunk_changelist")
        else:
            form = BunkCsvImportForm()
        context = {
            "form": form,
            "title": "Import Bunks from CSV",
            # Django admin templates use opts by convention
            "opts": self.model._meta,  # Required by Django admin templates
            "app_label": self.model._meta.app_label,
            "model_name": self.model._meta.model_name,
        }
        return render(request, "admin/csv_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_bunks"] = reverse("admin:bunk_import_csv")
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(
        description="Mark selected bunks as active",
    )
    def activate_bunks(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} bunks were activated.")

    @admin.action(
        description="Mark selected bunks as inactive",
    )
    def deactivate_bunks(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} bunks were deactivated.")


@admin.register(CounselorBunkAssignment)
class CounselorBunkAssignmentAdmin(TestDataAdminMixin, admin.ModelAdmin):
    list_display = (
        "counselor",
        "bunk",
        "start_date",
        "end_date",
        "is_primary",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_primary",
        "start_date",
        "end_date",
        "bunk__session",
        "bunk__unit",
        "created_at",
    )
    search_fields = (
        "counselor__first_name",
        "counselor__last_name",
        "counselor__email",
        "bunk__cabin__name",
    )
    date_hierarchy = "start_date"
    autocomplete_fields = ["counselor", "bunk"]
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-counselor-assignments/", self.import_counselor_assignments, name="counselor_assignment_import_csv"),
        ]
        return custom_urls + urls

    def import_counselor_assignments(self, request):
        if request.method == "POST":
            form = CounselorBunkAssignmentCsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]
                
                # Save the uploaded file to a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                # Process the CSV file
                result = import_counselor_bunk_assignments_from_csv(temp_path, dry_run=dry_run)

                if dry_run:
                    messages.info(
                        request,
                        f"Dry run completed. {result['success_count']} counselor assignments would be processed. "
                        f"Created: {result['created']}, Updated: {result['updated']}"
                    )
                else:
                    messages.success(
                        request,
                        f"Successfully processed {result['success_count']} counselor assignments. "
                        f"Created: {result['created']}, Updated: {result['updated']}"
                    )

                # Display any errors
                for error in result["errors"]:
                    messages.error(request, error)

                # Display any warnings
                for warning in result["warnings"]:
                    messages.warning(request, warning)

                # Clean up temporary file
                temp_path.unlink(missing_ok=True)

                return redirect("..")
        else:
            form = CounselorBunkAssignmentCsvImportForm()

        return render(
            request,
            "admin/csv_import_form.html",
            {
                "form": form,
                "title": "Import Counselor Bunk Assignments from CSV",
                "subtitle": "Upload a CSV file with counselor assignment data",
                "expected_headers": [
                    "counselor_email (required): Email of the counselor",
                    "cabin_name (required): Name of the cabin", 
                    "session_name (required): Name of the session",
                    "start_date (required): Start date in YYYY-MM-DD format",
                    "end_date (optional): End date in YYYY-MM-DD format (blank for ongoing)",
                    "is_primary (optional): 'true'/'false' or '1'/'0' for primary counselor",
                ],
                "sample_data": [
                    "counselor_email,cabin_name,session_name,start_date,end_date,is_primary",
                    "john.doe@example.com,Cabin A,Summer 2025,2025-06-15,2025-08-15,true",
                    "jane.smith@example.com,Cabin B,Summer 2025,2025-06-15,,false",
                ],
            },
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_counselor_assignments"] = reverse("admin:counselor_assignment_import_csv")
        return super().changelist_view(request, extra_context=extra_context)
    
    def is_active(self, obj):
        """Display if the assignment is currently active"""
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = "Currently Active"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "counselor", "bunk", "bunk__cabin", "bunk__session", "bunk__unit"
        )

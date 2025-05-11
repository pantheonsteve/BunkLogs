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
from .models import Bunk
from .models import Cabin
from .models import Session
from .models import Unit
from .services.imports import import_bunks_from_csv
from .services.imports import import_cabins_from_csv
from .services.imports import import_units_from_csv


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "unit_head",
        "created_at",
        "updated_at",
    )  # Adjust fields as needed
    search_fields = ("name", "unit_head")
    list_filter = ("unit_head", "created_at", "updated_at")
    date_hierarchy = "created_at"
    autocomplete_fields = ["unit_head"]

    form = UnitForm

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


@admin.register(Cabin)
class CabinAdmin(admin.ModelAdmin):
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
class SessionAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")  # Adjust fields as needed
    search_fields = ("name", "start_date", "end_date")


@admin.register(Bunk)
class BunkAdmin(admin.ModelAdmin):
    list_display = ("name", "cabin", "session", "unit", "is_active")
    list_filter = ("is_active", "session", "cabin", "unit")
    search_fields = ("cabin__name", "session__name")
    actions = ["activate_bunks", "deactivate_bunks"]

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

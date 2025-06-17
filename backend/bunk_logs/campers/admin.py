import logging
import tempfile
from pathlib import Path

from bunklogs.models import BunkLog
from django.contrib import admin
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import NoReverseMatch
from django.urls import path
from django.urls import reverse

from .forms import BunkAssignmentCsvImportForm
from .forms import CamperCsvImportForm
from .models import Camper
from .models import CamperBunkAssignment
from .services.imports import import_bunk_assignments_from_csv
from .services.imports import import_campers_from_csv
from bunk_logs.utils.admin import TestDataAdminMixin

# Define constants
MAX_DISPLAY_ITEMS = 5

# Set up logger
logger = logging.getLogger(__name__)


@admin.register(Camper)
class CamperAdmin(TestDataAdminMixin, admin.ModelAdmin):
    list_display = ("first_name", "last_name", "age")  # Adjust fields as needed
    list_filter = ("last_name", "first_name")
    search_fields = ("first_name", "last_name", "age")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-campers/",
                self.import_campers,
                name="campers_camper_import_csv",
            ),
        ]
        return custom_urls + urls

    def import_campers(self, request):
        if request.method == "POST":
            form = CamperCsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]

                # Save the uploaded file to a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                # Pass the temp_path to the import function, not the csv_file
                result = import_campers_from_csv(temp_path, dry_run=dry_run)

                if dry_run:
                    messages.info(
                        request,
                        "Dry run completed. "
                        f"{result['success_count']} campers would be imported.",
                    )
                else:
                    messages.success(
                        request,
                        f"Successfully imported {result['success_count']} campers.",
                    )

                if result["error_count"] > 0:
                    for error in result["errors"]:
                        messages.error(
                            request,
                            f"Row {error['row']}: {error['error']}",
                        )

                # Clean up the temporary file
                temp_path.unlink(missing_ok=True)

                return redirect("admin:campers_camper_changelist")
        else:
            form = CamperCsvImportForm()

        context = {
            "form": form,
            "title": "Import Campers",
            # Use the admin's opts property instead of accessing _meta directly
            "opts": self.opts,
            "app_label": self.opts.app_label,
            "model_name": self.opts.model_name,
        }
        return render(request, "admin/csv_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            extra_context["import_campers"] = reverse("admin:campers_camper_import_csv")
            logger.debug("Generated URL: %s", extra_context["import_campers"])
        except NoReverseMatch:
            logger.exception("Error generating URL")
            # Add a fallback URL as a temporary solution
            extra_context["import_campers"] = "/admin/campers/camper/import-csv/"
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(CamperBunkAssignment)
class CamperBunkAssignmentAdmin(TestDataAdminMixin, admin.ModelAdmin):
    list_display = ("camper", "bunk", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "bunk__session", "bunk__cabin")
    search_fields = ("camper__first_name", "camper__last_name", "bunk__cabin__name")
    readonly_fields = ("session_dates",)
    actions = ["deactivate_assignments", "activate_assignments"]

    @admin.action(
        description="Deactivate selected assignments",
    )
    def deactivate_assignments(self, request, queryset):
        """Bulk action to deactivate assignments instead of deleting them."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{updated} assignments have been deactivated.",
            messages.SUCCESS,
        )

    @admin.action(
        description="Activate selected assignments",
    )
    def activate_assignments(self, request, queryset):
        """Bulk action to reactivate assignments."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"{updated} assignments have been activated.",
            messages.SUCCESS,
        )

    def delete_model(self, request, obj):
        """Override delete_model to gracefully handle protected errors."""
        try:
            obj.delete()
            self.message_user(
                request,
                "Assignment successfully deleted.",
                messages.SUCCESS,
            )
        except ProtectedError:
            # Count bunk logs referencing this assignment
            logs_count = BunkLog.objects.filter(bunk_assignment=obj).count()

            error_message = (
                f"Cannot delete this assignment because it is referenced by "
                f"{logs_count} bunk logs. Consider deactivating it instead of "
                f"deleting by setting 'is_active' to False."
            )
            self.message_user(request, error_message, messages.ERROR)

    def delete_queryset(self, request, queryset):
        """Override delete_queryset to gracefully handle protected errors when
        bulk deleting."""
        protected_assignments = []
        deleted_count = 0

        for obj in queryset:
            try:
                obj.delete()
                deleted_count += 1
            except ProtectedError:
                protected_assignments.append(str(obj))

        if protected_assignments:
            error_message = (
                f"Could not delete {len(protected_assignments)} assignments because "
                f"they are referenced by bunk logs: "
                f"{', '.join(protected_assignments[:MAX_DISPLAY_ITEMS])}"
            )
            if len(protected_assignments) > MAX_DISPLAY_ITEMS:
                error_message += (
                    f" and {len(protected_assignments) - MAX_DISPLAY_ITEMS} more."
                )
            else:
                error_message += "."

            error_message += " Consider using the 'Deactivate' action instead."
            self.message_user(request, error_message, messages.ERROR)

        if deleted_count:
            self.message_user(
                request,
                f"Successfully deleted {deleted_count} assignments.",
                messages.SUCCESS,
            )

    def session_dates(self, obj):
        """Display session start and end dates."""
        if obj.bunk and obj.bunk.session:
            session_start = obj.bunk.session.start_date.strftime("%Y-%m-%d")
            session_end = obj.bunk.session.end_date.strftime("%Y-%m-%d")
            return f"Session dates: {session_start} to {session_end}"
        return "No session associated with this bunk"

    session_dates.short_description = "Session Information"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-assignments/",
                self.import_assignments,
                name="campers_camperbunkassignment_import_csv",
            ),
        ]
        return custom_urls + urls

    def import_assignments(self, request):
        if request.method == "POST":
            form = BunkAssignmentCsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]

                # Save the uploaded file to a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                result = import_bunk_assignments_from_csv(temp_path, dry_run=dry_run)

                if dry_run:
                    messages.info(
                        request,
                        f"Dry run completed. {result['success_count']} assignments "
                        f"would be imported.",
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

                return redirect("admin:campers_camperbunkassignment_changelist")
        else:
            form = BunkAssignmentCsvImportForm()

        context = {
            "form": form,
            "title": "Import Bunk Assignments",
            # Use the admin's opts property instead of accessing _meta directly
            "opts": self.opts,
            "app_label": self.opts.app_label,
            "model_name": self.opts.model_name,
        }
        return render(request, "admin/csv_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            # Use the correct URL name pattern that follows Django admin conventions
            extra_context["import_assignments"] = reverse(
                "admin:campers_camperbunkassignment_import_csv",
            )
            # Add logging to help debug URL generation
            logger.debug("Generated URL: %s", extra_context["import_assignments"])
        except NoReverseMatch:
            logger.exception("Error generating import URL")
            # Fallback to hardcoded URL
            extra_context["import_url"] = (
                "/admin/campers/camperbunkassignment/import-assignments/"
            )
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(
        description="Session Information",
    )
    def session_dates(self, obj):
        if obj.bunk and obj.bunk.session:
            session_start = obj.bunk.session.start_date.strftime("%Y-%m-%d")
            session_end = obj.bunk.session.end_date.strftime("%Y-%m-%d")
            return f"Session dates: {session_start} to {session_end}"
        return "No session associated with this bunk"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.bunk and obj.bunk.session:
            form.base_fields[
                "start_date"
            ].help_text = (
                f"Session starts on {obj.bunk.session.start_date.strftime('%Y-%m-%d')}"
            )
            form.base_fields[
                "end_date"
            ].help_text = (
                f"Session ends on {obj.bunk.session.end_date.strftime('%Y-%m-%d')}"
            )
        return form

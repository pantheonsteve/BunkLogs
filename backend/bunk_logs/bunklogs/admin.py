import tempfile
from pathlib import Path

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import path
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from bunk_logs.campers.models import CamperBunkAssignment
from bunk_logs.utils.admin import TestDataAdminMixin

from .forms import BunkLogAdminForm
from .forms import BunkLogCsvImportForm
from .forms import BunkSelectionForm
from .models import BunkLog
from .models import CounselorLog
from .models import KitchenStaffLog
from .models import LeadershipLog
from .models import StaffLog
from .services.imports import generate_sample_csv
from .services.imports import import_bunk_logs_from_csv


@admin.register(BunkLog)
class BunkLogAdmin(TestDataAdminMixin, admin.ModelAdmin):
    form = BunkLogAdminForm

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Update the queryset based on the bunk
        if "bunk_assignment" in form.base_fields:
            bunk_id = request.GET.get("bunk")
            if bunk_id:
                form.base_fields[
                    "bunk_assignment"
                ].queryset = CamperBunkAssignment.objects.filter(
                    bunk_id=bunk_id,
                    is_active=True,
                ).select_related("camper")
        return form

    list_display = ("date", "get_local_creation_date", "get_camper_name", "get_bunk_name", "counselor")
    list_filter = ("date", "bunk_assignment__bunk", "counselor")
    list_editable = ("date",)  # Allow quick editing of dates in list view
    list_display_links = ("get_camper_name",)  # Make camper name the clickable link instead of date
    search_fields = (
        "bunk_assignment__camper__first_name",
        "bunk_assignment__camper__last_name",
        "counselor__email",
        "description",
    )

    def save_model(self, request, obj, form, change):
        """Override save to provide better error messages for duplicates."""
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            if "unique constraint" in str(e).lower() and "bunk_assignment_id_date" in str(e):
                from django.contrib import messages
                messages.error(
                    request,
                    f"A log already exists for {obj.bunk_assignment.camper} on {obj.date}. "
                    f"Please choose a different date or edit the existing log.",
                )
                raise
            raise

    @admin.display(
        description=_("Created (Local)"),
    )
    def get_local_creation_date(self, obj):
        """Show the local creation date for debugging purposes."""
        from django.utils import timezone
        local_created = timezone.localtime(obj.created_at)
        return local_created.strftime("%Y-%m-%d %H:%M")

    @admin.display(
        description=_("Camper"),
    )
    def get_camper_name(self, obj):
        return obj.bunk_assignment.camper

    @admin.display(
        description=_("Bunk"),
    )
    def get_bunk_name(self, obj):
        return obj.bunk_assignment.bunk.name

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "select-bunk/",
                self.admin_site.admin_view(self.select_bunk_view),
                name="bunklog_select_bunk",
            ),
            path("import-bunklogs/", self.import_bunklogs, name="bunklogs_bunklog_import_csv"),
        ]
        return custom_urls + urls

    def select_bunk_view(self, request):
        """View for selecting a bunk before adding a bunk log."""
        if request.method == "POST":
            form = BunkSelectionForm(request.POST)
            if form.is_valid():
                bunk_id = form.cleaned_data["bunk"].id
                add_url = reverse("admin:bunklogs_bunklog_add")
                return redirect(f"{add_url}?bunk={bunk_id}")
        else:
            form = BunkSelectionForm()

        context = {
            "form": form,
            "title": _("Select Bunk"),
            "opts": self.opts,
            "list_url": "admin:bunklogs_bunklog_changelist",
        }
        return render(request, "admin/bunklogs/select_bunk.html", context)

    def import_bunklogs(self, request):
        if request.method == "POST":
            form = BunkLogCsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]

                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                try:
                    default_counselor_email = request.user.email if request.user.is_staff else None

                    result = import_bunk_logs_from_csv(
                        temp_path,
                        dry_run=dry_run,
                        default_counselor_email=default_counselor_email,
                    )

                    if dry_run:
                        messages.info(
                            request,
                            "Dry run completed. "
                            f"{result['success_count']} bunklogs would be imported.",
                        )
                    else:
                        messages.success(
                            request,
                            f"Successfully imported {result['success_count']} bunklogs.",
                        )

                    if result["error_count"] > 0:
                        for error in result["errors"]:
                            messages.error(
                                request,
                                f"Error in row {error['row']}: {error['error']}",
                            )
                except Exception as e:
                    messages.error(request, f"Import failed: {e!s}")
                finally:
                    temp_path.unlink(missing_ok=True)

                return redirect("admin:bunklogs_bunklog_changelist")
        else:
            form = BunkLogCsvImportForm()

        context = {
            "form": form,
            "title": "Import BunkLogs from CSV",
            "opts": self.model._meta,
            "app_label": self.model._meta.app_label,
            "model_name": self.model._meta.model_name,
            "sample_csv": generate_sample_csv(),
        }
        return render(request, "admin/csv_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_bunklogs"] = reverse("admin:bunklogs_bunklog_import_csv")
        return super().changelist_view(request, extra_context=extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        """Override add view to check for bunk parameter and filter assignments."""
        bunk_id = request.GET.get("bunk")
        if not bunk_id:
            return redirect("../select-bunk/")
        return super().add_view(request, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter bunk assignments based on selected bunk and active status."""
        if db_field.name == "bunk_assignment":
            bunk_id = request.GET.get("bunk")
            if bunk_id:
                kwargs["queryset"] = CamperBunkAssignment.objects.filter(
                    bunk_id=bunk_id,
                    is_active=True,
                    bunk__is_active=True,
                ).select_related("camper")
            else:
                kwargs["queryset"] = CamperBunkAssignment.objects.filter(
                    is_active=True,
                    bunk__is_active=True,
                ).select_related("camper")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Roles allowed to view their own staff logs in the admin
_SELF_VIEW_ROLES = ["Counselor", "Leadership", "Kitchen Staff"]
_ADMIN_WRITE_ROLES = ["Counselor", "Leadership", "Kitchen Staff", "Admin"]


class StaffLogAdmin(TestDataAdminMixin, admin.ModelAdmin):
    """Base admin for StaffLog and its proxy models."""

    list_display = (
        "date",
        "get_local_creation_date",
        "staff_member",
        "get_staff_role",
        "day_quality_score",
        "support_level_score",
        "day_off",
        "staff_care_support_needed",
    )
    list_filter = (
        "date",
        "staff_member__role",
        "day_off",
        "staff_care_support_needed",
        "day_quality_score",
        "support_level_score",
    )
    list_editable = ("date",)
    list_display_links = ("staff_member",)
    search_fields = (
        "staff_member__first_name",
        "staff_member__last_name",
        "staff_member__email",
        "elaboration",
        "values_reflection",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("staff_member", "date"),
        }),
        ("Scores", {
            "fields": ("day_quality_score", "support_level_score"),
            "description": "Rate your day and support level on a scale of 1-5",
        }),
        ("Status", {
            "fields": ("day_off", "staff_care_support_needed"),
        }),
        ("Reflections", {
            "fields": ("elaboration", "values_reflection"),
            "classes": ("wide",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description=_("Created (Local)"))
    def get_local_creation_date(self, obj):
        from django.utils import timezone
        local_created = timezone.localtime(obj.created_at)
        return local_created.strftime("%Y-%m-%d %H:%M")

    @admin.display(description=_("Role"))
    def get_staff_role(self, obj):
        return obj.staff_member.role

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_staff or request.user.role == "Admin":
            return qs

        if request.user.role in ["Unit Head", "Camper Care"]:
            from django.utils import timezone

            from bunk_logs.bunks.models import UnitStaffAssignment
            from bunk_logs.users.models import User

            role_map = {"Unit Head": "unit_head", "Camper Care": "camper_care"}
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=request.user,
                role=role_map[request.user.role],
                start_date__lte=timezone.now().date(),
                end_date__isnull=True,
            ).values_list("unit_id", flat=True)

            counselor_ids = User.objects.filter(
                role="Counselor",
                assigned_bunks__unit_id__in=set(unit_assignments),
            ).values_list("id", flat=True)

            return qs.filter(staff_member_id__in=counselor_ids)

        if request.user.role in _SELF_VIEW_ROLES:
            return qs.filter(staff_member=request.user)

        return qs.none()

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False

        if request.user.is_staff or request.user.role == "Admin":
            return True

        if request.user.role in ["Unit Head", "Camper Care"]:
            return False

        if request.user.role in _SELF_VIEW_ROLES and obj:
            from django.utils import timezone
            today = timezone.now().date()
            log_created_date = obj.created_at.date() if obj.created_at else obj.date
            return obj.staff_member == request.user and today == log_created_date

        return False

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        return request.user.role in _ADMIN_WRITE_ROLES or request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        return request.user.is_staff or request.user.role == "Admin"


@admin.register(StaffLog)
class StaffLogMainAdmin(StaffLogAdmin):
    """Admin for all staff logs (combined view)."""


@admin.register(CounselorLog)
class CounselorLogAdmin(StaffLogAdmin):
    """Admin for Counselor logs only."""

    def get_queryset(self, request):
        return super().get_queryset(request).filter(staff_member__role="Counselor")


@admin.register(LeadershipLog)
class LeadershipLogAdmin(StaffLogAdmin):
    """Admin for Leadership Team logs only."""

    def get_queryset(self, request):
        return super().get_queryset(request).filter(staff_member__role="Leadership")


@admin.register(KitchenStaffLog)
class KitchenStaffLogAdmin(StaffLogAdmin):
    """Admin for Kitchen Staff logs only."""

    def get_queryset(self, request):
        return super().get_queryset(request).filter(staff_member__role="Kitchen Staff")

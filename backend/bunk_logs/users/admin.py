import tempfile
from pathlib import Path

from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import admin as auth_admin
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import path
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .forms import UserCsvImportForm
from .models import User
from .services.imports import import_users_from_csv
from bunk_logs.utils.admin import TestDataAdminMixin

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class UserAdmin(TestDataAdminMixin, auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "role",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["email", "first_name", "last_name", "role", "is_superuser"]
    search_fields = ["name"]
    ordering = ["id"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-users/", self.import_users, name="user_import_csv"),
        ]
        return custom_urls + urls

    def import_users(self, request):
        if request.method == "POST":
            form = UserCsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                dry_run = form.cleaned_data["dry_run"]
                batch_size = form.cleaned_data["batch_size"]
                use_fast_hashing = form.cleaned_data["use_fast_hashing"]

                # Save the uploaded file to a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in csv_file.chunks():
                        temp_file.write(chunk)

                try:
                    # Process the CSV file with optimizations
                    result = import_users_from_csv(
                        temp_path, 
                        dry_run=dry_run,
                        batch_size=batch_size,
                        use_fast_hashing=use_fast_hashing
                    )

                    if dry_run:
                        messages.info(
                            request,
                            "Dry run completed. "
                            f"{result['success_count']} users would be imported.",
                        )
                    else:
                        messages.success(
                            request,
                            f"Successfully imported {result['success_count']} users using batch size of {batch_size}.",
                        )

                    if result["error_count"] > 0:
                        for error in result["errors"]:
                            messages.error(
                                request,
                                f"Error in row {error['row']}: {error['error']}",
                            )

                except Exception as e:
                    messages.error(
                        request,
                        f"Import failed: {str(e)}. Try reducing the batch size or using fast hashing.",
                    )
                finally:
                    # Clean up the temporary file
                    temp_path.unlink(missing_ok=True)

                return redirect("admin:users_user_changelist")
        else:
            form = UserCsvImportForm()

        context = {
            "form": form,
            "title": "Import Users from CSV",
            # Django admin templates use opts by convention
            "opts": self.model._meta,  # Required by Django admin templates
            "app_label": self.model._meta.app_label,
            "model_name": self.model._meta.model_name,
        }
        return render(request, "admin/users_csv_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_users"] = reverse("admin:user_import_csv")
        return super().changelist_view(request, extra_context=extra_context)
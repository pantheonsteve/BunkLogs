# your_app/forms.py
from django import forms

from bunk_logs.users.models import User  # Use the fully qualified import path

from .models import Unit


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = [
            "name",
            "unit_head",
            "camper_care",
        ]  # Include the new camper_care field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        all_users = User.objects.all()

        unit_head_users = User.objects.filter(role=User.UNIT_HEAD)

        # If no results, try variations of the role name
        if not unit_head_users.exists():
            # Try uppercase with underscore (UNIT_HEAD)
            unit_head_users = User.objects.filter(role="UNIT_HEAD")

            # If still no results, try with space (Unit Head)
            if not unit_head_users.exists():
                unit_head_users = User.objects.filter(role="Unit Head")

                # Try case insensitive search as a fallback
                if not unit_head_users.exists():
                    unit_head_users = User.objects.filter(role__icontains="unit")

                    # Last resort: show all users
                    if not unit_head_users.exists():
                        unit_head_users = all_users

        self.fields["unit_head"].queryset = unit_head_users

        # Set up camper_care field queryset
        camper_care_users = User.objects.filter(role=User.CAMPER_CARE)

        # If no results, try variations of the role name
        if not camper_care_users.exists():
            # Try with space
            camper_care_users = User.objects.filter(role="Camper Care")

            # Try case insensitive search as a fallback
            if not camper_care_users.exists():
                camper_care_users = User.objects.filter(role__icontains="camper care")

                # Last resort: show all users
                if not camper_care_users.exists():
                    camper_care_users = all_users

        self.fields["camper_care"].queryset = camper_care_users


class CabinCsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Please upload a CSV file with the required headers.",
    )
    dry_run = forms.BooleanField(
        required=False,
        label="Dry run",
        help_text="Validate the import without saving to database.",
    )


class UnitCsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV with the required columns",
    )
    dry_run = forms.BooleanField(
        required=False,
        label="Dry run",
        help_text="Validate without saving to database",
    )
    create_missing_users = forms.BooleanField(
        required=False,
        label="Create missing users",
        help_text="Create new unit head users if they don't exist (disabled)",
    )


class BunkCsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Please upload a CSV file with the required headers.",
    )
    dry_run = forms.BooleanField(
        required=False,
        label="Dry run",
        help_text="Validate the import without saving to database.",
    )

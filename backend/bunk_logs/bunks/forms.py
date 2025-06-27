# your_app/forms.py
from django import forms

from bunk_logs.users.models import User  # Use the fully qualified import path

from .models import Unit


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = [
            "name",
        ]  # Removed legacy unit_head and camper_care fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No special field configuration needed since we removed the legacy fields


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

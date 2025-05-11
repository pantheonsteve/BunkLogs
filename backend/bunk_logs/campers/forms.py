from django import forms


class CamperCsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV with correct columns",
    )

    dry_run = forms.BooleanField(
        required=False,
        label="Dry run",
        help_text="Validate without saving to database",
    )

    def clean(self):
        cleaned_data = super().clean()
        csv_file = cleaned_data.get("csv_file")
        if csv_file:
            if not csv_file.name.endswith(".csv"):
                self.add_error("csv_file", "File must be a CSV file")
        return cleaned_data


class BunkAssignmentCsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV with correct columns",
    )
    dry_run = forms.BooleanField(
        required=False,
        label="Dry run",
        help_text="Validate without saving to database",
    )

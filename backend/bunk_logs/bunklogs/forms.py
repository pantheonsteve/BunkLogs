from bunk_logs.campers.models import CamperBunkAssignment
from django import forms
from django.utils.translation import gettext_lazy as _

from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.bunks.models import Bunk


class BunkLogForm(forms.ModelForm):
    class Meta:
        model = BunkLog
        fields = [
            "date",
            "bunk_assignment",
            "counselor",
            "not_on_camp",
            "social_score",
            "behavior_score",
            "participation_score",
            "request_camper_care_help",
            "request_unit_head_help",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "bunk_assignment" in self.fields:
            # Get the bunk_id from the request
            request = kwargs.get("request")
            if request and request.GET.get("bunk"):
                bunk_id = request.GET.get("bunk")
                queryset = CamperBunkAssignment.objects.filter(
                    bunk_id=bunk_id,
                    is_active=True,
                ).select_related("camper")
                self.fields["bunk_assignment"].queryset = queryset

                # Use a custom label for each option
                self.fields["bunk_assignment"].label_from_instance = (
                    lambda obj: f"{obj.camper.first_name} {obj.camper.last_name}"
                )


class CustomModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.camper.first_name} {obj.camper.last_name}"


class BunkSelectionForm(forms.Form):
    """
    Form for selecting a bunk before creating a bunk log.
    """

    bunk = forms.ModelChoiceField(
        queryset=Bunk.objects.filter(is_active=True),
        label=_("Select a bunk"),
        empty_label=_("-- Choose a bunk --"),
    )


class BunkLogAdminForm(forms.ModelForm):
    class Meta:
        model = BunkLog
        # Replace "__all__" with an explicit list of fields
        fields = [
            "date",
            "bunk_assignment",
            "counselor",
            "not_on_camp",
            "social_score",
            "behavior_score",
            "participation_score",
            "request_camper_care_help",
            "request_unit_head_help",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace the field with our custom field
        if "bunk_assignment" in self.fields:
            # Preserve the current queryset
            queryset = self.fields["bunk_assignment"].queryset
            self.fields["bunk_assignment"] = CustomModelChoiceField(
                queryset=queryset,
                required=self.fields["bunk_assignment"].required,
                widget=self.fields["bunk_assignment"].widget,
            )


class BunkLogCsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV file",
        help_text="A CSV file containing bunklog data.",
    )
    dry_run = forms.BooleanField(
        label="Dry run",
        required=False,
        initial=True,
        help_text="Perform a dry run without saving changes.",
    )

from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.forms import EmailField
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User
        field_classes = {"email": EmailField}


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        fields = ("email",)
        field_classes = {"email": EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """

    class Meta:
        model = User
        fields = ("email",)


class UserSocialSignupForm(SocialSignupForm):
    """
    Form for social signup in case auto-signup is disabled.
    """
    
    def save(self, request):
        # Initialize the user
        user = super().save(request)
        
        # Set default role for social signups
        user.role = 'Counselor'
        user.save()
        
        return user


class UserCsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV with user data. Required columns: email, first_name, last_name. Optional: role, password, is_active, is_staff",
    )
    dry_run = forms.BooleanField(
        required=False,
        label="Dry run",
        help_text="Validate the import without saving to database",
    )
    batch_size = forms.IntegerField(
        initial=25,
        min_value=1,
        max_value=100,
        label="Batch size",
        help_text="Number of users to process per batch (smaller batches are safer for large imports)",
    )
    use_fast_hashing = forms.BooleanField(
        initial=True,
        required=False,
        label="Use fast password hashing",
        help_text="Use faster (but less secure) password hashing for bulk imports. Recommended for large datasets.",
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError("File must be a CSV file (.csv)")
        return csv_file

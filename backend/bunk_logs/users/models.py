from typing import ClassVar, Optional

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField, BooleanField, EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for Bunk Logs.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    first_name = CharField(_("First Name of User"), blank=True, max_length=255)  # type: ignore[assignment]
    last_name = CharField(_("Last Name of User"), blank=True, max_length=255)  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]
    profile_complete = models.BooleanField(default=False)

    # Adding name property to fix Google login
    @property
    def name(self) -> str:
        """Return the user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or ""
    
    @name.setter
    def name(self, value: Optional[str]) -> None:
        """Set the user's name by splitting into first and last name."""
        if not value:
            return
        
        parts = value.strip().split(maxsplit=1)
        self.first_name = parts[0]
        self.last_name = parts[1] if len(parts) > 1 else ""

    ADMIN = "Admin"
    CAMPER_CARE = "Camper Care"
    UNIT_HEAD = "Unit Head"
    COUNSELOR = "Counselor"

    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (CAMPER_CARE, "Camper Care"),
        (UNIT_HEAD, "Unit Head"),
        (COUNSELOR, "Counselor"),
    ]

    role = models.CharField(
        max_length=255,
        choices=ROLE_CHOICES,
        blank=True,
        default="",
    )

    # Adding a field to track if user profile is complete
    profile_complete = BooleanField(_("Profile Complete"), default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    class Meta:
        app_label = "users"

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

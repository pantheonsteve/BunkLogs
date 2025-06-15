from __future__ import annotations

import typing

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect

if typing.TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin
    from bunk_logs.users.models import User

class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Constructs the email confirmation (activation) url."""
        # Use dynamic FRONTEND_URL from settings
        return f"{settings.FRONTEND_URL}/verify-email/{emailconfirmation.key}"
    
    def get_password_reset_url(self, request, passwordreset):
        """Constructs the password reset url."""
        # Use dynamic FRONTEND_URL from settings
        return f"{settings.FRONTEND_URL}/accounts/password/reset/key/{passwordreset.key}"

    def get_login_redirect_url(self, request):
        """
        Override to redirect to frontend after login
        """
        return settings.LOGIN_REDIRECT_URL

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: SocialLogin) -> bool:
        """Allow social account signup even if regular registration is closed"""
        return True
    
    def get_login_error_url(self, request, provider, error=None, exception=None, extra_context=None):
        """Override to redirect to the configured frontend URL for errors"""
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://bunklogs.net')
        return f"{frontend_url}/signin?auth_error={error or 'unknown'}"
    
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed.
        """
        # Check if this social account is already connected to a user
        if sociallogin.is_existing:
            # Social account already connected, continue with the login flow
            return
        
        # Check if we have a user with the same email
        email = sociallogin.account.extra_data.get('email')
        if email:
            User = sociallogin.user.__class__
            try:
                # Try to find an existing user with this email
                user = User.objects.get(email=email)
                # Connect the social account to this user and login
                sociallogin.connect(request, user)
                # Skip the rest of the social login flow and redirect using dynamic URL
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
            except User.DoesNotExist:
                # No existing user, continue with normal flow
                pass
                
    def populate_user(self, request: HttpRequest, sociallogin: SocialLogin, data: dict) -> User:
        """Populate user instance with data from social provider"""
        user = super().populate_user(request, sociallogin, data)
        
        # Extract name data
        if not user.first_name or not user.last_name:
            if name := data.get("name"):
                parts = name.split()
                if len(parts) > 1:
                    user.first_name = parts[0]
                    user.last_name = " ".join(parts[1:])
                else:
                    user.first_name = name
            elif first_name := data.get("first_name"):
                user.first_name = first_name
                if last_name := data.get("last_name"):
                    user.last_name = last_name
        
        # Set role for new social users
        if not getattr(user, 'pk', None):  # Only for new users
            user.role = 'Counselor'  # Default role
            
        return user
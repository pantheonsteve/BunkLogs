from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest
from rest_framework_simplejwt.tokens import RefreshToken

class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)
    
    def get_email_confirmation_url(self, request, emailconfirmation):
        """Constructs the email confirmation (activation) url."""
        url = super().get_email_confirmation_url(request, emailconfirmation)
        
        if settings.DEBUG:
            return f"{settings.FRONTEND_URL}/verify-email/{emailconfirmation.key}"
        
        return f"{settings.FRONTEND_URL}/verify-email/{emailconfirmation.key}"
    
    def get_login_redirect_url(self, request):
        """
        Override to redirect to frontend after login
        """
        return settings.LOGIN_REDIRECT_URL

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        """Allow social account signup even if regular registration is closed"""
        return True
    
    def populate_user(self, request, sociallogin, data):
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
    
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        # Store tokens in the session - will be used in the redirect view
        request.session['auth_tokens'] = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        return user
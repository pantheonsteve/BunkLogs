from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings

class DefaultAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        """Constructs the email confirmation (activation) url.
        
        Note that if you have architected your system such that email
        confirmations are sent outside of the request context, the request
        may be None.
        """
        url = super().get_email_confirmation_url(request, emailconfirmation)
        
        # For local development
        if settings.DEBUG:
            return f"http://localhost:5173/verify-email/{emailconfirmation.key}"
        
        # For production
        return f"https://bunklogs.net/verify-email/{emailconfirmation.key}"
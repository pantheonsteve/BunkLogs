from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from bunk_logs.core.identity import active_membership_roles
from bunk_logs.core.identity import organizations_payload

User = get_user_model()

def build_user_auth_payload(user) -> dict:
    """User details for login / impersonation responses.

    ``organizations`` carries the per-org capability + membership roles the
    frontend routes on; ``membership_roles`` is the flattened union kept for
    backwards compatibility during the transition.
    """
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": getattr(user, "first_name", ""),
        "last_name": getattr(user, "last_name", ""),
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "membership_roles": active_membership_roles(user),
        "organizations": organizations_payload(user),
    }

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    def validate(self, attrs):
        # Strip whitespace from email
        if self.username_field in attrs:
            attrs[self.username_field] = attrs[self.username_field].strip()

        # Add custom claims to the token
        data = super().validate(attrs)
        refresh = self.get_token(self.user)

        # Add extra claims to the token
        refresh["email"] = self.user.email
        refresh["user_id"] = str(self.user.id)

        # Return the token data
        data["access"] = str(refresh.access_token)
        data["refresh"] = str(refresh)

        data["user"] = build_user_auth_payload(self.user)

        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@ensure_csrf_cookie
def get_csrf_token(request):
    """
    Return CSRF token for JavaScript clients
    """
    token = get_token(request)
    return JsonResponse({"detail": "CSRF cookie set", "csrfToken": token})

def get_auth_status(request):
    """
    Return authentication status and user info
    """
    if request.user.is_authenticated:
        return JsonResponse({
            "isAuthenticated": True,
            "user": {
                "id": request.user.id,
                "email": request.user.email,
                "firstName": request.user.first_name,
                "lastName": request.user.last_name,
                "name": request.user.name,
                "profileComplete": request.user.profile_complete,
                "membership_roles": active_membership_roles(request.user),
                "organizations": organizations_payload(request.user),
            },
        })
    return JsonResponse({
        "isAuthenticated": False,
    })

import json
import logging

from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.models import SocialToken
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import OpenApiResponse
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person

from .serializers import ApiUserSerializer
from .serializers import SocialAppDiagnosticResponseSerializer

User = get_user_model()

logger = logging.getLogger(__name__)


def _active_membership_roles(user) -> list[str]:
    """Distinct active multi-tenant Membership roles for ``user``."""
    person = Person.all_objects.filter(user=user).first()
    if person is None:
        return []
    return sorted(
        set(
            Membership.all_objects.filter(
                person=person,
                is_active=True,
            ).values_list("role", flat=True),
        ),
    )


@method_decorator(csrf_exempt, name="dispatch")
class UserCreate(generics.CreateAPIView):
    """User registration view."""

    serializer_class = ApiUserSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = ApiUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


def get_user_by_id(request, user_id):
    """Endpoint to get user details by ID."""
    try:
        user = User.objects.get(id=user_id)
        serializer = ApiUserSerializer(user)
        return JsonResponse(serializer.data)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)


@login_required
def google_login_callback(request):
    user = request.user
    social_account = SocialAccount.objects.filter(user=user).first()
    if not social_account:
        return redirect("http://localhost:5173/login/callback/?error=NoSocialAccount")

    token = SocialToken.objects.filter(
        account=social_account,
        account__providers="google",
    ).first()
    if token:
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        return redirect(f"http://localhost:5173/login/callback/?token={access_token}")
    return redirect("http://localhost:5173/login/callback/?error=NoGoogleTokenFound")


@csrf_exempt
def validate_google_token(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            google_access_token = data.get("access_token")
            if not google_access_token:
                return JsonResponse({"error": "No access token provided"}, status=400)
            return JsonResponse({"valid": True})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    return JsonResponse({"error": "Invalid request method - not allowed"}, status=405)


class UserDetailsView(viewsets.ReadOnlyModelViewSet):
    """Custom User Details View to ensure JSON response."""

    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated]
    serializer_class = ApiUserSerializer

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    def list(self, request):
        user = request.user
        data = ApiUserSerializer(user).data
        data["groups"] = [group.name for group in user.groups.all()]
        return Response(data)


@extend_schema(
    summary="Get user by email",
    description="Endpoint to get user details by email.",
    parameters=[
        OpenApiParameter(
            name="email",
            description="User email address",
            required=True,
            type=OpenApiTypes.STR,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ApiUserSerializer,
            description="User details retrieved successfully",
        ),
        404: OpenApiResponse(description="User not found"),
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_by_email(request, email):
    """Return user profile fields used by the frontend auth bootstrap."""
    try:
        user = User.objects.prefetch_related("groups").get(email=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    if request.user.is_authenticated:
        if not request.user.is_staff and request.user.email != email:
            raise PermissionDenied("You do not have permission to view this user's details")

    data = ApiUserSerializer(user).data
    if request.user.is_authenticated:
        data["groups"] = [group.name for group in user.groups.all()]
    else:
        data = {
            "id": data.get("id"),
            "email": data.get("email"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "role": data.get("role"),
            "membership_roles": data.get("membership_roles", []),
        }
    return Response(data)


class FixSocialAppsView(APIView):
    """Diagnostic endpoint to fix MultipleObjectsReturned error with Google OAuth."""

    permission_classes = [IsAuthenticated]
    serializer_class = SocialAppDiagnosticResponseSerializer

    @extend_schema(
        summary="Fix social authentication apps",
        description=(
            "Diagnostic endpoint to fix MultipleObjectsReturned error with Google OAuth. "
            "GET: List all SocialApp entries for Google. "
            "POST: Keep only the most recent app and delete duplicates"
        ),
        methods=["GET", "POST"],
        responses={
            200: OpenApiResponse(
                response=SocialAppDiagnosticResponseSerializer,
                description="Social apps diagnostic information or fix completed",
            ),
            403: OpenApiResponse(description="Forbidden - Staff access required"),
        },
    )
    def get(self, request):
        if not request.user.is_staff:
            return Response({"error": "Staff access required"}, status=403)
        google_apps = SocialApp.objects.filter(provider="google")
        apps_data = [
            {
                "id": app.id,
                "name": app.name,
                "client_id": app.client_id[:10] + "...",
                "created": app.date_added.isoformat() if hasattr(app, "date_added") else "unknown",
            }
            for app in google_apps
        ]
        response_data = {
            "count": google_apps.count(),
            "google_apps": apps_data,
            "message": "To fix, make a POST request to this endpoint to keep only the latest app",
        }
        serializer = self.serializer_class(response_data)
        return Response(serializer.data)

    @extend_schema(
        summary="Fix social authentication apps",
        description=(
            "Diagnostic endpoint to fix MultipleObjectsReturned error with Google OAuth. "
            "POST: Keep only the most recent app and delete duplicates"
        ),
        responses={
            200: OpenApiResponse(
                response=SocialAppDiagnosticResponseSerializer,
                description="Social apps diagnostic information or fix completed",
            ),
            403: OpenApiResponse(description="Forbidden - Staff access required"),
        },
    )
    def post(self, request):
        if not request.user.is_staff:
            return Response({"error": "Staff access required"}, status=403)
        google_apps = SocialApp.objects.filter(provider="google")
        count = google_apps.count()
        if count <= 1:
            response_data = {
                "count": count,
                "google_apps": [
                    {
                        "id": app.id,
                        "name": app.name,
                        "client_id": app.client_id[:10] + "...",
                        "created": app.date_added.isoformat() if hasattr(app, "date_added") else "unknown",
                    }
                    for app in google_apps
                ],
                "message": "No duplicates to fix",
            }
            serializer = self.serializer_class(response_data)
            return Response(serializer.data)
        latest_app = google_apps.order_by("-id").first()
        google_apps.exclude(id=latest_app.id).delete()
        response_data = {
            "count": 1,
            "google_apps": [
                {
                    "id": latest_app.id,
                    "name": latest_app.name,
                    "client_id": latest_app.client_id[:10] + "...",
                    "created": latest_app.date_added.isoformat() if hasattr(latest_app, "date_added") else "unknown",
                },
            ],
            "message": f"Fixed! Kept app ID {latest_app.id} and deleted {count - 1} duplicate(s)",
        }
        serializer = self.serializer_class(response_data)
        return Response(serializer.data)


@extend_schema(
    summary="Authentication debug view",
    description="View for debugging authentication status",
    responses={
        200: OpenApiResponse(description="Authentication debug information"),
    },
)
@login_required
def auth_debug_view(request):
    """View for debugging authentication status."""
    social_accounts = [
        {
            "provider": account.provider,
            "uid": account.uid,
            "last_login": account.last_login,
            "date_joined": account.date_joined,
        }
        for account in SocialAccount.objects.filter(user=request.user)
    ]
    return JsonResponse(
        {
            "uid": request.user.id,
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "role": request.user.role,
            "is_staff": request.user.is_staff,
            "social_accounts": social_accounts,
            "session_keys": list(request.session.keys()),
        },
    )

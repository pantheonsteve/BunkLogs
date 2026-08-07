"""Retained user endpoints on /api/v1/.

The legacy single-tenant viewsets (bunks, units, campers, bunk logs,
counselor logs, orders) were removed in the User.role retirement; their
functionality lives in the role-scoped multi-tenant endpoints (dashboards,
reflections, orders state machine).
"""

import logging

from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import OpenApiResponse
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import ApiUserSerializer

User = get_user_model()

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class UserCreate(generics.CreateAPIView):
    """
    User registration view.
    """
    serializer_class = ApiUserSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication for user creation


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
        404: OpenApiResponse(
            description="User not found",
        ),
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_by_email(request, email):
    """Return the profile payload the frontend auth context routes on.

    Full details go to the user themselves and staff; anyone else gets a
    minimal public shape (no membership or org context).
    """
    try:
        user = User.objects.prefetch_related("groups").get(email=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    is_self_or_staff = request.user.is_authenticated and (
        request.user.is_staff or request.user.email == email
    )
    if request.user.is_authenticated and not is_self_or_staff:
        msg = "You do not have permission to view this user's details"
        raise PermissionDenied(msg)

    data = ApiUserSerializer(user).data
    if not request.user.is_authenticated:
        return Response({
            "id": data.get("id"),
            "email": data.get("email"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
        })

    data["groups"] = [group.name for group in user.groups.all()]
    return Response(data)

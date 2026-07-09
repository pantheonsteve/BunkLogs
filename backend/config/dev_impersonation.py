"""Local-only dev impersonation endpoints.

Mint JWT tokens for any user so developers can view the UI as that user.
Refuses to run when DEBUG is False or the database host is not local.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from bunk_logs.api.views import _active_membership_roles

User = get_user_model()

LOCAL_DB_HOST_ALLOWLIST = {"localhost", "127.0.0.1", "postgres", "::1", ""}


def dev_impersonation_enabled() -> bool:
    if not settings.DEBUG:
        return False
    host = (settings.DATABASES.get("default", {}).get("HOST") or "").strip().lower()
    return host in LOCAL_DB_HOST_ALLOWLIST


def _disabled_response() -> Response:
    return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)


def _build_token_payload(user) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["email"] = user.email
    refresh["user_id"] = str(user.id)
    if hasattr(user, "role"):
        refresh["role"] = getattr(user, "role", "User")

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": getattr(user, "first_name", ""),
            "last_name": getattr(user, "last_name", ""),
            "role": getattr(user, "role", "User"),
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "membership_roles": _active_membership_roles(user),
        },
    }


def _user_summary(user) -> dict:
    name = f"{user.first_name} {user.last_name}".strip()
    return {
        "id": str(user.id),
        "email": user.email,
        "name": name or user.email,
        "role": getattr(user, "role", ""),
        "is_active": user.is_active,
        "membership_roles": _active_membership_roles(user),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def dev_impersonation_status(request):
    if not dev_impersonation_enabled():
        return _disabled_response()
    return Response({"enabled": True})


@api_view(["GET"])
@permission_classes([AllowAny])
def dev_impersonation_users(request):
    if not dev_impersonation_enabled():
        return _disabled_response()

    query = (request.query_params.get("q") or "").strip()
    users = User.objects.order_by("email")
    if query:
        users = users.filter(
            Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query),
        )

    return Response({
        "results": [_user_summary(user) for user in users[:50]],
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def dev_impersonation_login(request):
    if not dev_impersonation_enabled():
        return _disabled_response()

    user_id = request.data.get("user_id")
    email = (request.data.get("email") or "").strip()
    if not user_id and not email:
        return Response(
            {"detail": "Provide user_id or email."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        if user_id:
            user = User.objects.get(pk=user_id)
        else:
            user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response(
            {"detail": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not user.is_active:
        return Response(
            {"detail": "User is inactive."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(_build_token_payload(user))

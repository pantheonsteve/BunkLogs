from typing import Any

from django.contrib.auth import get_user_model
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    membership_roles = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "profile_complete",
            "membership_roles",
            "organizations",
        ]
        read_only_fields = ["id", "is_active", "is_staff"]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_membership_roles(self, obj) -> list[str]:
        """Distinct active multi-tenant Membership roles for this user."""
        from bunk_logs.core.identity import active_membership_roles

        return active_membership_roles(obj)

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_organizations(self, obj) -> list[dict[str, Any]]:
        """Per-org capability + membership roles (see ``organizations_payload``)."""
        from bunk_logs.core.identity import organizations_payload

        return organizations_payload(obj)

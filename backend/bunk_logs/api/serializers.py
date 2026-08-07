"""User-facing serializers for the retained /api/v1/ user endpoints.

The legacy single-tenant serializers (bunks, campers, bunk logs, orders)
were removed with their viewsets in the User.role retirement; role and
capability context now comes from Memberships via ``core.identity``.
"""

from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from bunk_logs.users.models import User


class ApiUserSerializer(serializers.ModelSerializer):
    membership_roles = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("first_name", "last_name", "id", "email", "profile_complete",
                  "is_active", "is_staff", "is_superuser", "date_joined",
                  "membership_roles", "organizations",
                  "password")
        extra_kwargs = {
            "password": {"write_only": True},
            "is_staff": {"read_only": True},
            "is_superuser": {"read_only": True},
        }

    def to_representation(self, instance):
        """Prefer the linked multi-tenant Person's name for display.

        ``Person`` is the canonical identity in the multi-tenant model, so
        a name edited there should surface in the UI. We override output
        only (the model ``first_name``/``last_name`` stay writable for the
        registration flow) and fall back to the ``User`` name when there's
        no linked Person or the Person name is blank.
        """
        data = super().to_representation(instance)
        from bunk_logs.core.models import Person

        person = Person.all_objects.filter(user=instance).first()
        if person:
            if person.first_name:
                data["first_name"] = person.first_name
            if person.last_name:
                data["last_name"] = person.last_name
        return data

    def create(self, validated_data):
        """Create a new user (active by default) and set the password."""
        validated_data["is_active"] = True
        user = User(**validated_data)
        user.set_password(validated_data["password"])
        user.save()
        return user

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

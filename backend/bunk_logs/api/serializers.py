from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.users.models import User


class ApiUserSerializer(serializers.ModelSerializer):
    membership_roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "role",
            "id",
            "email",
            "profile_complete",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "membership_roles",
            "password",
        )
        extra_kwargs = {
            "password": {"write_only": True},
            "is_staff": {"read_only": True},
            "is_superuser": {"read_only": True},
        }

    def to_representation(self, instance):
        """Prefer the linked Person's name for display when present."""
        data = super().to_representation(instance)
        person = Person.all_objects.filter(user=instance).first()
        if person:
            if person.first_name:
                data["first_name"] = person.first_name
            if person.last_name:
                data["last_name"] = person.last_name
        return data

    def create(self, validated_data):
        if "role" not in validated_data or not validated_data["role"]:
            validated_data["role"] = "Counselor"
        validated_data["is_active"] = True
        user = User(**validated_data)
        user.set_password(validated_data["password"])
        user.save()
        return user

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_membership_roles(self, obj) -> list[str]:
        person = Person.all_objects.filter(user=obj).first()
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


class SocialAppDiagnosticSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    client_id = serializers.CharField()
    created = serializers.CharField()


class SocialAppDiagnosticResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    google_apps = SocialAppDiagnosticSerializer(many=True)
    message = serializers.CharField()

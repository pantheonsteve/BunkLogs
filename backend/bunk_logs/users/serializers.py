from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from bunk_logs.bunks.models import CounselorBunkAssignment
from bunk_logs.bunks.models import UnitStaffAssignment

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    bunks = serializers.SerializerMethodField()
    units = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_staff",
            "profile_complete",
            "bunks",
            "units",
        ]
        read_only_fields = ["id", "is_active", "is_staff"]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_bunks(self, obj) -> list[dict[str, Any]]:
        if obj.role == "Counselor":
            today = timezone.now().date()
            assignments = CounselorBunkAssignment.objects.filter(
                counselor=obj,
                start_date__lte=today,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=today),
            ).select_related("bunk__cabin", "bunk__session")
            return [{
                "id": str(a.bunk.id),
                "name": a.bunk.name,
                "cabin": a.bunk.cabin.name if a.bunk.cabin else None,
                "session": a.bunk.session.name if a.bunk.session else None,
            } for a in assignments]
        return []

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_units(self, obj) -> list[dict[str, Any]]:
        if obj.role == "Unit Head":
            today = timezone.now().date()
            assignments = UnitStaffAssignment.objects.filter(
                staff_member=obj,
                role="unit_head",
                start_date__lte=today,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=today),
            ).select_related("unit")
            return [{
                "id": str(a.unit.id),
                "name": a.unit.name,
            } for a in assignments]
        return []

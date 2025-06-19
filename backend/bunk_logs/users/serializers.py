from django.contrib.auth import get_user_model
from rest_framework import serializers
from bunk_logs.bunks.models import Bunk
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from typing import List, Dict, Any

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
    def get_bunks(self, obj) -> List[Dict[str, Any]]:
        if obj.role == 'Counselor':
            bunks = obj.assigned_bunks.filter(is_active=True)
            return [{
                'id': str(bunk.id),
                'name': bunk.name,
                'cabin': bunk.cabin.name if bunk.cabin else None,
                'session': bunk.session.name if bunk.session else None,
            } for bunk in bunks]
        return []
    
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_units(self, obj) -> List[Dict[str, Any]]:
        if obj.role == 'Unit Head':
            units = obj.managed_units.all()
            return [{
                'id': str(unit.id),
                'name': unit.name,
            } for unit in units]
        return []
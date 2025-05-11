from django.contrib.auth import get_user_model
from rest_framework import serializers
from bunks.models import Bunk

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
    
    def get_bunks(self, obj):
        if obj.role == 'Counselor':
            bunks = obj.assigned_bunks.filter(is_active=True)
            return [{
                'id': str(bunk.id),
                'name': bunk.name,
                'cabin': bunk.cabin.name if bunk.cabin else None,
                'session': bunk.session.name if bunk.session else None,
            } for bunk in bunks]
        return []
    
    def get_units(self, obj):
        if obj.role == 'Unit Head':
            units = obj.managed_units.all()
            return [{
                'id': str(unit.id),
                'name': unit.name,
            } for unit in units]
        return []
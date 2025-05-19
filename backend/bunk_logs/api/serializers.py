from campers.models import Camper
from campers.models import CamperBunkAssignment
from rest_framework import serializers

from bunk_logs.users.models import User
from bunks.models import Bunk
from bunks.models import Cabin
from bunks.models import Session
from bunks.models import Unit
from bunklogs.models import BunkLog


class CabinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cabin
        fields = "__all__"


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = "__all__"


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = "__all__"


# Simple User serializer for nested relationships to avoid recursion
class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "id", "email"]


# Simple Bunk serializer for nested relationships to avoid recursion
class SimpleBunkSerializer(serializers.ModelSerializer):
    unit = UnitSerializer()
    cabin = CabinSerializer()
    session = SessionSerializer()
    counselors = SimpleUserSerializer(many=True, read_only=True)  # Use SimpleUserSerializer here

    class Meta:
        model = Bunk
        fields = ['counselors', 'session', 'unit', 'cabin', 'id']  # Exclude the field causing recursion


class UserSerializer(serializers.ModelSerializer):
    bunks = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    unit_bunks = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ("first_name", "last_name", "role", "id", "email", "profile_complete", 
                  "is_active", "is_staff", "is_superuser", "date_joined", 
                  "bunks", "unit", "unit_bunks", "username", "password")
        extra_kwargs = {
            'password': {'write_only': True},
            'is_active': {'read_only': True},
            'is_staff': {'read_only': True},
            'is_superuser': {'read_only': True},
        }

    def create(self, validated_data):
        """
        Create a new user and set the password.
        """
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user
    
    def get_bunks(self, obj):
        if obj.role == 'Counselor':
            # Use SimpleBunkSerializer instead of BunkSerializer to avoid recursion
            return SimpleBunkSerializer(Bunk.objects.filter(counselors=obj), many=True).data
        return []
    
    def get_unit(self, obj):
        if obj.role == 'Unit Head' and hasattr(obj, 'unit'):
            return UnitSerializer(obj.unit).data
        return None
    
    def get_unit_bunks(self, obj):
        if obj.role == 'Unit Head' and hasattr(obj, 'unit'):
            bunks = Bunk.objects.filter(unit=obj.unit)
            return SimpleBunkSerializer(bunks, many=True).data
        return []


class BunkSerializer(serializers.ModelSerializer):
    unit = UnitSerializer()
    cabin = CabinSerializer()
    session = SessionSerializer()
    counselors = SimpleUserSerializer(many=True, read_only=True)  # Use SimpleUserSerializer here

    class Meta:
        model = Bunk
        fields = "__all__"


class CamperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camper
        fields = ["bunk_assignment", "first_name", "last_name", "date_of_birth", "emergency_contact_name",]


class CamperBunkAssignmentSerializer(serializers.ModelSerializer):
    bunk = SimpleBunkSerializer()  # Use SimpleBunkSerializer to avoid recursion
    camper = CamperSerializer()

    class Meta:
        model = CamperBunkAssignment
        fields = ["id","bunk", "camper"]


class BunkLogSerializer(serializers.ModelSerializer):
    """
    Serializer for BunkLog model.
    For POST requests, you need to provide:
    - date
    - bunk_assignment (id)
    - counselor (id)
    - other fields as needed
    """
    class Meta:
        model = BunkLog
        fields = '__all__'
        
    def validate(self, data):
        """
        Validate the BunkLog data.
        """
        # Validate scores are between 1 and 5 if provided
        for score_field in ['social_score', 'behavior_score', 'participation_score']:
            if score_field in data and data[score_field] is not None:
                score = data[score_field]
                if score < 1 or score > 5:
                    raise serializers.ValidationError({score_field: "Score must be between 1 and 5"})
        
        # Check for duplicate bunk logs (same camper on same date)
        if self.instance is None:  # Only for creation, not updates
            existing = BunkLog.objects.filter(
                bunk_assignment=data['bunk_assignment'],
                date=data['date']
            ).exists()
            
            if existing:
                raise serializers.ValidationError(
                    "A bunk log already exists for this camper on this date."
                )
                
        return data
    
class CamperBunkLogSerializer(serializers.ModelSerializer):
    """
    Serializer for bunklogs related to a specific camper.
    """
    camper = serializers.SerializerMethodField()
    bunk = SimpleBunkSerializer(read_only=True)  # Use SimpleBunkSerializer
    bunk_assignment = CamperBunkAssignmentSerializer(read_only=True)

    class Meta:
        model = BunkLog
        fields = [
            "date",
            "bunk",
            "counselor",
            "not_on_camp",
            "social_score",
            "behavior_score",
            "participation_score",
            "request_camper_care_help",
            "request_unit_head_help",
            "description",
            "camper",
            "bunk_assignment",
            "id"
        ]
    
    def get_camper(self, obj):
        return CamperSerializer(obj.bunk_assignment.camper).data
    
    def get_bunk(self, obj):
        return SimpleBunkSerializer(obj.bunk_assignment.bunk).data  # Use SimpleBunkSerializer


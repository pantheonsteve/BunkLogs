from bunk_logs.campers.models import Camper
from bunk_logs.campers.models import CamperBunkAssignment
from typing import Optional, Dict, Any, List
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes

from bunk_logs.users.models import User
from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import Unit
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.bunklogs.models import BunkLog, CounselorLog
from bunk_logs.orders.models import Order, OrderItem, Item, ItemCategory, OrderType


class CabinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cabin
        fields = "__all__"


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = "__all__"


# Simple User serializer for nested relationships to avoid recursion
class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "id", "email"]


class UnitSerializer(serializers.ModelSerializer):
    unit_head_details = serializers.SerializerMethodField()
    camper_care_details = serializers.SerializerMethodField()
    # New fields for multiple staff
    staff_assignments = serializers.SerializerMethodField()
    unit_heads = serializers.SerializerMethodField()
    camper_care_staff = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = ["id", "name", "created_at", "updated_at", "unit_head_details", "camper_care_details", 
                 "staff_assignments", "unit_heads", "camper_care_staff"]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_unit_head_details(self, obj) -> Optional[Dict[str, Any]]:
        # Backward compatibility - return primary unit head
        primary = obj.primary_unit_head
        if primary:
            return {
                "id": primary.id,
                "first_name": primary.first_name,
                "last_name": primary.last_name,
                "email": primary.email,
                "role": primary.role,
            }
        return None

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_camper_care_details(self, obj) -> Optional[Dict[str, Any]]:
        # Backward compatibility - return primary camper care
        primary = obj.primary_camper_care
        if primary:
            return {
                "id": primary.id,
                "first_name": primary.first_name,
                "last_name": primary.last_name,
                "email": primary.email,
                "role": primary.role,
            }
        return None

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_staff_assignments(self, obj) -> List[Dict[str, Any]]:
        from django.utils import timezone
        assignments = obj.staff_assignments.filter(
            start_date__lte=timezone.now().date(),
            end_date__isnull=True
        ).select_related('staff_member')
        return [{
            'id': assignment.id,
            'staff_member': {
                'id': assignment.staff_member.id,
                'first_name': assignment.staff_member.first_name,
                'last_name': assignment.staff_member.last_name,
                'email': assignment.staff_member.email,
            },
            'role': assignment.role,
            'role_display': assignment.get_role_display(),
            'is_primary': assignment.is_primary,
            'start_date': assignment.start_date,
            'end_date': assignment.end_date,
        } for assignment in assignments]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_unit_heads(self, obj) -> List[Dict[str, Any]]:
        return [{
            'id': staff.id,
            'first_name': staff.first_name,
            'last_name': staff.last_name,
            'email': staff.email,
            'is_primary': staff in [obj.primary_unit_head] if obj.primary_unit_head else False
        } for staff in obj.all_unit_heads]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_camper_care_staff(self, obj) -> List[Dict[str, Any]]:
        return [{
            'id': staff.id,
            'first_name': staff.first_name,
            'last_name': staff.last_name,
            'email': staff.email,
            'is_primary': staff in [obj.primary_camper_care] if obj.primary_camper_care else False
        } for staff in obj.all_camper_care]


class UnitStaffAssignmentSerializer(serializers.ModelSerializer):
    staff_member_name = serializers.CharField(source='staff_member.get_full_name', read_only=True)
    staff_member_details = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    
    class Meta:
        model = UnitStaffAssignment
        fields = ['id', 'unit', 'staff_member', 'staff_member_name', 'staff_member_details', 
                 'role', 'role_display', 'is_primary', 'start_date', 'end_date', 
                 'created_at', 'updated_at', 'unit_name']

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_staff_member_details(self, obj) -> Dict[str, Any]:
        return {
            'id': obj.staff_member.id,  # Corrected to use 'id' instead of 'user_id'
            'first_name': obj.staff_member.first_name,
            'last_name': obj.staff_member.last_name,
            'email': obj.staff_member.email,
            'role': obj.staff_member.role,
        }


# Simple Unit serializer for nested relationships to avoid recursion
class SimpleUnitSerializer(serializers.ModelSerializer):
    unit_head = serializers.SerializerMethodField()
    camper_care = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = ["id", "name", "unit_head", "camper_care"]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_unit_head(self, obj) -> Optional[Dict[str, Any]]:
        if obj.unit_head:
            return SimpleUserSerializer(obj.unit_head).data
        return None

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_camper_care(self, obj) -> Optional[Dict[str, Any]]:
        if obj.camper_care:
            return SimpleUserSerializer(obj.camper_care).data
        return None


# Simple Bunk serializer for nested relationships to avoid recursion
class SimpleBunkSerializer(serializers.ModelSerializer):
    unit = SimpleUnitSerializer()
    cabin = CabinSerializer()
    session = SessionSerializer()
    counselors = SimpleUserSerializer(many=True, read_only=True)  # Use SimpleUserSerializer here

    class Meta:
        model = Bunk
        fields = ['counselors', 'session', 'unit', 'cabin', 'id']  # Exclude the field causing recursion


class ApiUserSerializer(serializers.ModelSerializer):
    bunks = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    unit_bunks = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ("first_name", "last_name", "role", "id", "email", "profile_complete", 
                  "is_active", "is_staff", "is_superuser", "date_joined", 
                  "bunks", "unit", "unit_bunks", "password")
        extra_kwargs = {
            'password': {'write_only': True},
            'is_staff': {'read_only': True},
            'is_superuser': {'read_only': True},
        }

    def create(self, validated_data):
        """
        Create a new user and set the password.
        Automatically set role to "Counselor" and is_active to True for new registrations.
        """
        # Set default role for new users if not provided
        if 'role' not in validated_data or not validated_data['role']:
            validated_data['role'] = 'Counselor'
        
        # Set user as active by default
        validated_data['is_active'] = True
        
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user
    
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_bunks(self, obj) -> List[Dict[str, Any]]:
        if obj.role == 'Counselor':
            # Use SimpleBunkSerializer instead of BunkSerializer to avoid recursion
            return SimpleBunkSerializer(Bunk.objects.filter(counselors=obj), many=True).data
        return []
    
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_unit(self, obj) -> Optional[Dict[str, Any]]:
        if obj.role == 'Unit Head' and hasattr(obj, 'unit'):
            return UnitSerializer(obj.unit).data
        return None
    
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_unit_bunks(self, obj) -> List[Dict[str, Any]]:
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
        fields = ["id", "first_name", "last_name", "date_of_birth", "emergency_contact_name", 
                  "emergency_contact_phone", "camper_notes"]


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
    - other fields as needed
    Note: counselor is automatically set to the current user
    """
    counselor = serializers.PrimaryKeyRelatedField(read_only=True)  # Make counselor read-only
    
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
    counselor = SimpleUserSerializer(read_only=True)  # Use SimpleUserSerializer for counselor

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


class CounselorLogSerializer(serializers.ModelSerializer):
    """
    Serializer for CounselorLog model.
    For POST requests, you need to provide:
    - date
    - day_quality_score (1-5)
    - support_level_score (1-5)
    - elaboration
    - day_off (boolean)
    - staff_care_support_needed (boolean)
    - values_reflection
    Note: counselor is automatically set to the current user
    """
    counselor = serializers.PrimaryKeyRelatedField(read_only=True)  # Make counselor read-only
    
    class Meta:
        model = CounselorLog
        fields = '__all__'
        
    def validate(self, data):
        """
        Validate the CounselorLog data.
        """
        # Validate scores are between 1 and 5
        for score_field in ['day_quality_score', 'support_level_score']:
            if score_field in data and data[score_field] is not None:
                score = data[score_field]
                if score < 1 or score > 5:
                    raise serializers.ValidationError({score_field: "Score must be between 1 and 5"})
        
        # Check for duplicate counselor logs (same counselor on same date)
        # Only perform this check if we have a request context (i.e., in DRF views)
        if self.instance is None and hasattr(self, 'context') and 'request' in self.context:  # Only for creation, not updates
            existing = CounselorLog.objects.filter(
                counselor=self.context['request'].user,
                date=data['date']
            ).exists()
            
            if existing:
                raise serializers.ValidationError(
                    "A counselor log already exists for this date."
                )
                
        return data
        

class SimpleCamperBunkAssignmentSerializer(serializers.ModelSerializer):
    """
    Simple serializer for CamperBunkAssignment to avoid circular imports
    """
    bunk_name = serializers.CharField(source='bunk.name', read_only=True)
    
    class Meta:
        model = CamperBunkAssignment
        fields = ["id", "bunk_name", "bunk", "start_date", "end_date", "is_active"]


class CamperWithAssignmentsSerializer(serializers.ModelSerializer):
    """
    Extended Camper serializer that includes bunk assignments
    Use this when you need to display a camper with their bunk assignments
    """
    bunk_assignments = serializers.SerializerMethodField()
    
    class Meta:
        model = Camper
        fields = ["id", "first_name", "last_name", "date_of_birth", "emergency_contact_name", 
                  "emergency_contact_phone", "camper_notes", "bunk_assignments"]
    
    def get_bunk_assignments(self, obj):
        from bunk_logs.api.serializers import SimpleCamperBunkAssignmentSerializer
        assignments = obj.bunk_assignments.filter(is_active=True)
        return SimpleCamperBunkAssignmentSerializer(assignments, many=True).data


# Order-related serializers
class ItemCategorySerializer(serializers.ModelSerializer):
    """Serializer for ItemCategory model."""
    class Meta:
        model = ItemCategory
        fields = ['id', 'category_name', 'category_description']


class ItemSerializer(serializers.ModelSerializer):
    """Serializer for Item model."""
    item_category_name = serializers.CharField(source='item_category.category_name', read_only=True)
    
    class Meta:
        model = Item
        fields = ['id', 'item_name', 'item_description', 'available', 'item_category', 'item_category_name']


class OrderTypeSerializer(serializers.ModelSerializer):
    """Serializer for OrderType model."""
    item_categories = ItemCategorySerializer(many=True, read_only=True)
    item_category_ids = serializers.PrimaryKeyRelatedField(
        queryset=ItemCategory.objects.all(),
        many=True,
        write_only=True,
        source='item_categories'
    )
    
    class Meta:
        model = OrderType
        fields = ['id', 'type_name', 'type_description', 'item_categories', 'item_category_ids']


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""
    item_name = serializers.CharField(source='item.item_name', read_only=True)
    item_description = serializers.CharField(source='item.item_description', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'item', 'item_name', 'item_description', 'item_quantity']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    order_bunk_name = serializers.CharField(source='order_bunk.name', read_only=True)
    order_bunk_cabin = serializers.CharField(source='order_bunk.cabin', read_only=True)
    order_bunk_session = serializers.CharField(source='order_bunk.session', read_only=True)
    order_type_name = serializers.CharField(source='order_type.type_name', read_only=True)
    order_items = OrderItemSerializer(many=True)
    order_status_display = serializers.CharField(source='get_order_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_email', 'user_name', 'order_date', 'order_status', 
            'order_status_display', 'order_bunk', 'order_bunk_name', 'order_bunk_cabin', 'order_bunk_session', 'order_type', 
            'order_type_name', 'order_items'
        ]
        read_only_fields = ['order_date', 'user']
    
    @extend_schema_field(OpenApiTypes.STR)
    def get_user_name(self, obj) -> str:
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return ""
    
    def update(self, instance, validated_data):
        """Handle updating order with nested order items."""
        order_items_data = validated_data.pop('order_items', None)
        
        # Update the order instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle order items update if provided
        if order_items_data is not None:
            # Delete existing order items
            instance.order_items.all().delete()
            
            # Create new order items
            for item_data in order_items_data:
                OrderItem.objects.create(order=instance, **item_data)
        
        return instance
    
    def validate_order_items(self, value):
        """Validate that order items are not empty and quantities are positive."""
        if value is not None:
            if not value:
                raise serializers.ValidationError("At least one order item is required.")
            
            for item_data in value:
                if item_data.get('item_quantity', 0) <= 0:
                    raise serializers.ValidationError("Item quantity must be greater than 0.")
        
        return value


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders with order items."""
    order_items = OrderItemSerializer(many=True)
    
    class Meta:
        model = Order
        fields = ['order_status', 'order_bunk', 'order_type', 'order_items']
    
    def create(self, validated_data):
        order_items_data = validated_data.pop('order_items')
        # Set user from request context
        validated_data['user'] = self.context['request'].user
        order = Order.objects.create(**validated_data)
        
        # Create order items
        for item_data in order_items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        return order
    
    def validate_order_items(self, value):
        """Validate that order items are not empty and quantities are positive."""
        if not value:
            raise serializers.ValidationError("At least one order item is required.")
        
        for item_data in value:
            if item_data.get('item_quantity', 0) <= 0:
                raise serializers.ValidationError("Item quantity must be greater than 0.")
        
        return value


# Simplified serializers for nested relationships
class SimpleOrderTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderType
        fields = ['id', 'type_name', 'type_description']


class SimpleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'item_name', 'item_description', 'available']


# Unit Head and Camper Care specific serializers
class UnitCounselorSerializer(serializers.ModelSerializer):
    """Serializer for counselors in unit-specific endpoints."""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']


class UnitCamperSerializer(serializers.ModelSerializer):
    """Serializer for campers in unit-specific endpoints."""
    bunk_log = serializers.SerializerMethodField()
    
    class Meta:
        model = Camper
        fields = ['id', 'first_name', 'last_name', 'bunk_log']
    
    def get_bunk_log(self, obj):
        """Get bunk log for this camper on the specified date."""
        # Get the date from the context (passed from the view)
        date = self.context.get('date')
        if not date:
            return None
        
        # Get the camper's active bunk assignment
        from bunk_logs.campers.models import CamperBunkAssignment
        assignment = CamperBunkAssignment.objects.filter(
            camper=obj, 
            is_active=True
        ).first()
        
        if not assignment:
            return None
        
        # Get the bunk log for this assignment and date
        from bunk_logs.bunklogs.models import BunkLog
        try:
            bunk_log = BunkLog.objects.get(
                bunk_assignment=assignment,
                date=date
            )
            # Get the serialized bunk log data
            bunk_log_data = BunkLogSerializer(bunk_log).data
            
            # Add counselor first and last names
            if bunk_log.counselor:
                bunk_log_data['counselor_first_name'] = bunk_log.counselor.first_name
                bunk_log_data['counselor_last_name'] = bunk_log.counselor.last_name
                bunk_log_data['counselor_email'] = bunk_log.counselor.email
            
            return bunk_log_data
        except BunkLog.DoesNotExist:
            return None


class UnitBunkDetailSerializer(serializers.ModelSerializer):
    """Detailed bunk serializer for unit endpoints including counselors and campers."""
    counselors = UnitCounselorSerializer(many=True, read_only=True)
    campers = serializers.SerializerMethodField()
    cabin_name = serializers.CharField(source='cabin.name', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    
    class Meta:
        model = Bunk
        fields = ['id', 'cabin_name', 'session_name', 'counselors', 'campers']
    
    def get_campers(self, obj):
        """Get active campers assigned to this bunk."""
        active_assignments = obj.camper_assignments.filter(is_active=True)
        campers = [assignment.camper for assignment in active_assignments]
        # Pass the date context from the parent serializer
        context = self.context.copy() if self.context else {}
        return UnitCamperSerializer(campers, many=True, context=context).data


class UnitHeadBunksSerializer(serializers.ModelSerializer):
    """Serializer for Unit Head endpoint response."""
    bunks = serializers.SerializerMethodField()
    
    class Meta:
        model = Unit
        fields = ['id', 'name', 'bunks']
    
    def get_bunks(self, obj):
        """Get bunks with date context for bunk logs."""
        bunks = obj.bunks.all()
        # Pass the context from the view to the bunk serializer
        context = self.context.copy() if self.context else {}
        return UnitBunkDetailSerializer(bunks, many=True, context=context).data


class CamperCareBunksSerializer(serializers.ModelSerializer):
    """Serializer for Camper Care endpoint response."""
    bunks = serializers.SerializerMethodField()
    
    class Meta:
        model = Unit
        fields = ['id', 'name', 'bunks']
    
    def get_bunks(self, obj):
        """Get bunks with date context for bunk logs."""
        bunks = obj.bunks.all()
        # Pass the context from the view to the bunk serializer
        context = self.context.copy() if self.context else {}
        return UnitBunkDetailSerializer(bunks, many=True, context=context).data


class SocialAppDiagnosticSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    client_id = serializers.CharField()
    created = serializers.CharField()

class SocialAppDiagnosticResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    message = serializers.CharField()
    google_apps = SocialAppDiagnosticSerializer(many=True)
from campers.models import Camper
from campers.models import CamperBunkAssignment
from rest_framework import serializers

from bunk_logs.users.models import User
from bunks.models import Bunk
from bunks.models import Cabin
from bunks.models import Session
from bunks.models import Unit
from bunklogs.models import BunkLog
from bunk_logs.orders.models import Order, OrderItem, Item, ItemCategory, OrderType


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
    
    def get_user_name(self, obj):
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
        fields = ['id', 'type_name']


class SimpleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'item_name', 'available']
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from campers.models import Camper
from campers.models import CamperBunkAssignment

from bunks.models import Bunk
from bunks.models import Unit
from bunklogs.models import BunkLog
from bunk_logs.orders.models import Order, OrderItem, Item, ItemCategory, OrderType

from .serializers import BunkLogSerializer
from .serializers import BunkSerializer
from .serializers import CamperBunkAssignmentSerializer
from .serializers import CamperSerializer
from .serializers import UnitSerializer, SimpleBunkSerializer
from .serializers import CamperBunkLogSerializer
from .serializers import UserSerializer
from .serializers import (
    OrderSerializer, OrderCreateSerializer, ItemSerializer, 
    ItemCategorySerializer, OrderTypeSerializer, SimpleOrderTypeSerializer,
    SimpleItemSerializer
)

from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken

from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken

import json

#from .permissions import BunkAccessPermission
#from .permissions import IsCounselorForBunk
#from .permissions import DebugPermission

User = get_user_model()


class UserCreate(generics.CreateAPIView):
    """
    User registration view.
    """
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    
def get_user_by_id(request, user_id):
    """
    Endpoint to get user details by ID.
    """
    try:
        user = User.objects.get(id=user_id)
        serializer = UserSerializer(user)
        return JsonResponse(serializer.data)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    

@login_required
def google_login_callback(request):
    user = request.user

    social_accounts = SocialAccount.objects.filter(user=user)
    print("Social Account for user:", social_accounts)

    social_account = social_accounts.first()

    if not social_account:
        print("No social account found for user.", user)
        return redirect('http://localhost:5173/login/callback/?error=NoSocialAccount')
    
    token = SocialToken.objects.filter(account=social_account, account__providers='google').first()

    if token:
        print("Google token found:", token)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        return redirect(f'http://localhost:5173/login/callback/?token={access_token}')
        # Here you can use the token to fetch user data from Google if needed
    else:
        print("No token found for social account.")
        return redirect('http://localhost:5173/login/callback/?error=NoGoogleTokenFound')

@csrf_exempt
def validate_google_token(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            google_access_token = data.get('access_token')
            print("Google access token:", google_access_token)
            if not google_access_token:
                return JsonResponse({'error': 'No access token provided'}, status=400)
            return JsonResponse({'valid': True})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    return JsonResponse({'error': 'Invalid request method - not allowed'}, status=405)

class UserDetailsView(viewsets.ViewSet):
    """
    Custom User Details View to ensure JSON response
    """
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        user = request.user
        serializer = UserSerializer(user)
        data = serializer.data
        
        # If you want to add groups as a special case (since it's a many-to-many field)
        data['groups'] = [group.name for group in user.groups.all()]
        
        # Manually add bunk data to avoid circular references
        from bunks.models import Bunk
        assigned_bunks = []
        for bunk in Bunk.objects.filter(counselors=user):
            assigned_bunks.append({
                "id": str(bunk.id),
                "name": bunk.name,
                "cabin": str(bunk.cabin) if hasattr(bunk, 'cabin') else None,
                "session": str(bunk.session) if hasattr(bunk, 'session') else None,
                # Add any other basic bunk fields needed but avoid nesting counselors here
            })
        data['assigned_bunks'] = assigned_bunks

        return Response(data)

# Remove the existing retrieve method as we'll use a dedicated function-based view instead

@api_view(['GET'])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny
def get_user_by_email(request, email):
    """
    Endpoint to get user details by email.
    """
    try:
        # Get user by email
        user = User.objects.get(email=email)
        
        # Adjust security check to handle unauthenticated requests
        if request.user.is_authenticated:
            # For authenticated users, check permissions
            if not request.user.is_staff and request.user.email != email:
                # Special case for Unit Heads - they should see full details for users in their units
                if request.user.role == 'Unit Head' and hasattr(request.user, 'unit'):
                    # Get the bunks in the Unit Head's unit
                    unit_bunks = Bunk.objects.filter(unit=request.user.unit)
                    # Check if requested user is a counselor in any of those bunks
                    if not unit_bunks.filter(counselors=user).exists():
                        raise PermissionDenied("You do not have permission to view this user's details")
                else:
                    raise PermissionDenied("You do not have permission to view this user's details")
        
        # Continue with existing code for serialization and response
        serializer = UserSerializer(user)
        data = serializer.data

        assigned_bunks = []
        for bunk in Bunk.objects.filter(counselors=user):
            assigned_bunks.append({
                "id": str(bunk.id),
                "bunk_id": str(bunk.id),
                "name": bunk.name,
                "cabin": str(bunk.cabin) if hasattr(bunk, 'cabin') else None,
                "session": str(bunk.session) if hasattr(bunk, 'session') else None,
            })
        data['assigned_bunks'] = assigned_bunks
        
        # Add unit information for Unit Heads
        if user.role == 'Unit Head':
            units = []
            for unit in Unit.objects.filter(unit_head=user):
                units.append({
                    "id": str(unit.id),
                    "name": unit.name,
                })
            data['units'] = units
            data['unit_name'] = unit.name
            # Add all bunks in this unit
            unit_bunks = Bunk.objects.filter(unit=unit)
            data['unit_bunks'] = BunkSerializer(unit_bunks, many=True).data
        
        # If the user is not authenticated, only return basic non-sensitive information
        if not request.user.is_authenticated:
            # Filter data to only include safe fields
            safe_data = {
                "id": data.get("id"),
                "email": data.get("email"),
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "role": data.get("role"),
                "bunks": data.get("assigned_bunks"),
                "units": data.get("units"),
                "unit_name": data.get("unit_name"),
                "unit_bunks": data.get("unit_bunks"),
            }
            return Response(safe_data)
            
        # For authenticated users, return all data
        data['groups'] = [group.name for group in user.groups.all()]
        
        return Response(data)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

class BunkViewSet(viewsets.ModelViewSet):
    renderer_classes = [JSONRenderer]
    permission_classes = [AllowAny]
    queryset = Bunk.objects.all()
    serializer_class = BunkSerializer
    lookup_field = 'id'  # Set lookup_field to match the URL parameter name
    
    def get_queryset(self):
        """
        Optionally filter bunks by ID.
        """
        queryset = Bunk.objects.all()
        bunk_id = self.request.query_params.get('id', None)
        if bunk_id is not None:
            queryset = queryset.filter(id=bunk_id)
        return queryset

class BunkLogsInfoByDateViewSet(APIView):
    """         
    API view to get bunk logs info by date.
    The endpoint will be '/api/v1/bunklogs/<str:bunk_id>/logs/<str:date>/'
    where 'bunk_id' is the ID of the bunk and 'date' is the date in YYYY-MM-DD format.
    The response will first search for all of the bunk_assignemnts for the bunk on that date.
    Then, it will search for all of the bunk logs for those assignments.
    The response will include the bunk assignment ID and the bunk log ID.
    If no bunk logs are found, the response will return an empty list.
    """
    renderer_classes = [JSONRenderer]
    permission_classes = [AllowAny]
    def get(self, request, bunk_id, date):
        try:
            # Get the bunk
            bunk = Bunk.objects.get(id=bunk_id)
            serialized_bunk = BunkSerializer(bunk).data
            # Get the unit
            unit = Unit.objects.filter(bunks=bunk).first()
            serialized_unit = UnitSerializer(unit).data if unit else None
            # Get camper assignments for this bunk
            assignments = CamperBunkAssignment.objects.filter(
                bunk=bunk,
                is_active=True,
            ).select_related('camper')
            # Get bunk logs for these assignments on the given date
            campers_data = []
            for assignment in assignments:
                # Get bunk log for this assignment and date (if exists)
                try:
                    bunk_log = BunkLog.objects.get(
                        bunk_assignment=assignment,
                        date=date
                    )
                    serialized_log = BunkLogSerializer(bunk_log).data
                    
                    # Add counselor details to the serialized log
                    if bunk_log.counselor:
                        serialized_log['counselor_first_name'] = bunk_log.counselor.first_name
                        serialized_log['counselor_last_name'] = bunk_log.counselor.last_name
                        serialized_log['counselor_email'] = bunk_log.counselor.email
                except BunkLog.DoesNotExist:
                    serialized_log = None
                # Add to campers list
                campers_data.append({
                    "camper_id": str(assignment.camper.id),
                    "camper_first_name": assignment.camper.first_name,
                    "camper_last_name": assignment.camper.last_name,
                    "bunk_assignment_id": str(assignment.id),
                    "bunk_log": serialized_log,
                })
            # Get counselors for this bunk
            counselors_data = []  # You'll need to implement this part
            for counselor in bunk.counselors.all():
                counselors_data.append({
                    "id": str(counselor.id),
                    "first_name": counselor.first_name,
                    "last_name": counselor.last_name,
                    "email": counselor.email,
                })
            response_data = {
                "date": date,
                "bunk": serialized_bunk,
                "unit": serialized_unit,
                "campers": campers_data,
                "counselors": counselors_data
            }
            return Response(response_data)
        except Bunk.DoesNotExist:
            return Response({"error": f"Bunk with ID {bunk_id} not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class UnitViewSet(viewsets.ModelViewSet):
    renderer_classes = [JSONRenderer]
    permission_classes = [AllowAny]
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer

class CamperViewSet(viewsets.ModelViewSet):
    renderer_classes = [JSONRenderer]
    permission_classes = [AllowAny]
    queryset = Camper.objects.all()
    serializer_class = CamperSerializer

class CamperBunkAssignmentViewSet(viewsets.ModelViewSet):
    renderer_classes = [JSONRenderer]
    permission_classes = [AllowAny]
    queryset = CamperBunkAssignment.objects.all()
    serializer_class = CamperBunkAssignmentSerializer

class BunkLogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = BunkLog.objects.all()
    serializer_class = BunkLogSerializer
    def get_queryset(self):
        user = self.request.user
        # Admin/staff can see all
        if user.is_staff or user.role == 'Admin':
            return BunkLog.objects.all()
        # Unit heads can see logs for bunks in their units
        if user.role == 'Unit Head':
            return BunkLog.objects.filter(
                bunk_assignment__bunk__unit__in=user.managed_units.all()
            )
        # Counselors can only see logs for their bunks
        if user.role == 'Counselor':
            return BunkLog.objects.filter(
                bunk_assignment__bunk__in=user.assigned_bunks.all()
            )
        # Default: see nothing
        return BunkLog.objects.none()

    def perform_create(self, serializer):
        # Verify the user is allowed to create a log for this bunk assignment
        bunk_assignment = serializer.validated_data.get('bunk_assignment')
        if self.request.user.role == 'Counselor':
            # Check if user is a counselor for this bunk
            if not self.request.user.assigned_bunks.filter(id=bunk_assignment.bunk.id).exists():
                raise PermissionDenied("You are not authorized to create logs for this bunk.")
        # Set the counselor automatically to the current user
        serializer.save(counselor=self.request.user)

class CamperBunkLogViewSet(APIView):
    renderer_classes = [JSONRenderer]
    permission_classes = [AllowAny]
    queryset = BunkLog.objects.all()
    serializer_class = BunkLogSerializer
    def get(self, request, camper_id):
        try:
            # Get the camper
            camper = Camper.objects.get(id=camper_id)
            serialized_camper = CamperSerializer(camper).data
            # Get the bunk assignments for this camper
            assignments = CamperBunkAssignment.objects.filter(camper=camper)
            # Get the bunk logs for these assignments
            bunk_logs = BunkLog.objects.filter(
                bunk_assignment__in=assignments
            ).select_related('bunk_assignment__bunk')
            # Serialize the bunk logs
            serialized_bunk_logs = CamperBunkLogSerializer(bunk_logs, many=True).data
            # Prepare the response data
            response_data = {
                "camper": serialized_camper,
                "bunk_logs": serialized_bunk_logs,
                "bunk_assignments": [
                    {
                        "id": str(assignment.id),
                        "bunk_name": assignment.bunk.name,
                        "bunk_id": str(assignment.bunk.id),
                        "is_active": assignment.is_active,
                        "start_date": assignment.start_date,
                        "end_date": assignment.end_date,
                    } for assignment in assignments
                ],
            }
            return Response(response_data)
        except Camper.DoesNotExist:
            return Response({"error": f"Camper with ID {camper_id} not found"}, status=404)


# Order-related API Views

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order model with CRUD operations.
    - GET /api/orders/ - List all orders
    - GET /api/orders/{id}/ - Retrieve specific order
    - POST /api/orders/ - Create new order
    - PUT /api/orders/{id}/ - Update order
    - DELETE /api/orders/{id}/ - Delete order
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter orders based on user role."""
        user = self.request.user
        if user.is_staff or user.role in ['counselor', 'admin']:
            # Staff and counselors can see all orders
            return Order.objects.all().select_related('user', 'order_bunk', 'order_type').prefetch_related('order_items__item')
        else:
            # Regular users can only see their own orders
            return Order.objects.filter(user=user).select_related('user', 'order_bunk', 'order_type').prefetch_related('order_items__item')
    
    def get_serializer_class(self):
        """Use different serializers for create vs read operations."""
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def perform_create(self, serializer):
        """Set the user to the current authenticated user."""
        serializer.save(user=self.request.user)


class ItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Item model.
    - GET /api/items/ - List all available items
    - GET /api/items/{id}/ - Retrieve specific item
    - POST /api/items/ - Create new item (staff only)
    - PUT /api/items/{id}/ - Update item (staff only)
    - DELETE /api/items/{id}/ - Delete item (staff only)
    """
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return available items, optionally filtered by category."""
        queryset = Item.objects.filter(available=True).select_related('item_category')
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(item_category_id=category_id)
        return queryset
    
    def perform_create(self, serializer):
        """Only staff can create items."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can create items.")
        serializer.save()
    
    def perform_update(self, serializer):
        """Only staff can update items."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can update items.")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only staff can delete items."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can delete items.")
        instance.delete()


class ItemCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ItemCategory model.
    - GET /api/item-categories/ - List all categories
    - GET /api/item-categories/{id}/ - Retrieve specific category
    - POST /api/item-categories/ - Create new category (staff only)
    - PUT /api/item-categories/{id}/ - Update category (staff only)
    - DELETE /api/item-categories/{id}/ - Delete category (staff only)
    """
    queryset = ItemCategory.objects.all()
    serializer_class = ItemCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Only staff can create categories."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can create categories.")
        serializer.save()
    
    def perform_update(self, serializer):
        """Only staff can update categories."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can update categories.")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only staff can delete categories."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can delete categories.")
        instance.delete()


class OrderTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for OrderType model.
    - GET /api/order-types/ - List all order types
    - GET /api/order-types/{id}/ - Retrieve specific order type
    - POST /api/order-types/ - Create new order type (staff only)
    - PUT /api/order-types/{id}/ - Update order type (staff only)
    - DELETE /api/order-types/{id}/ - Delete order type (staff only)
    """
    queryset = OrderType.objects.all().prefetch_related('item_categories')
    serializer_class = OrderTypeSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Only staff can create order types."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can create order types.")
        serializer.save()
    
    def perform_update(self, serializer):
        """Only staff can update order types."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can update order types.")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only staff can delete order types."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can delete order types.")
        instance.delete()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_items_for_order_type(request, order_type_id):
    """
    Get available items for a specific order type.
    Returns items from categories associated with the order type.
    """
    try:
        order_type = OrderType.objects.get(id=order_type_id)
        items = Item.objects.filter(
            item_category__in=order_type.item_categories.all(),
            available=True
        ).select_related('item_category')
        serializer = SimpleItemSerializer(items, many=True)
        return Response(serializer.data)
    except OrderType.DoesNotExist:
        return Response({"error": "Order type not found"}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_statistics(request):
    """
    Get order statistics for the current user or all users (if staff).
    """
    user = request.user
    
    if user.is_staff:
        # Staff can see all order statistics
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(order_status='pending').count()
        completed_orders = Order.objects.filter(order_status='completed').count()
        cancelled_orders = Order.objects.filter(order_status='cancelled').count()
    else:
        # Regular users see their own statistics
        total_orders = Order.objects.filter(user=user).count()
        pending_orders = Order.objects.filter(user=user, order_status='pending').count()
        completed_orders = Order.objects.filter(user=user, order_status='completed').count()
        cancelled_orders = Order.objects.filter(user=user, order_status='cancelled').count()
    
    return Response({
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
    })
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_user_bunks(request):
    """Temporary debug endpoint to check user-bunk relationships"""
    from bunks.models import Bunk
    user_data = {
        "email": request.user.email,
        "id": request.user.id,
        "role": request.user.role,
        "is_staff": request.user.is_staff,
    }
    # Check direct assigned bunks - only get the id field,
    bunks_query = Bunk.objects.filter(counselors__id=request.user.id)
    assigned_bunks = []
    for bunk in bunks_query:
        assigned_bunks.append({
            "id": bunk.id,
            "name": str(bunk),  # Use the string representation, which should use the name property
            "cabin": str(bunk.cabin) if bunk.cabin else None,
            "session": str(bunk.session) if bunk.session else None
        })
    user_data["assigned_bunks"] = assigned_bunks
    return JsonResponse(user_data)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def fix_social_apps(request):
    """Diagnostic endpoint to fix MultipleObjectsReturned error with Google OAuth.
    GET: List all SocialApp entries for Google
    POST: Keep only the most recent app and delete duplicates
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Staff access required'}, status=403)
    # Get all Google social apps:
    google_apps = SocialApp.objects.filter(provider='google')
    if request.method == 'GET':
        apps_data = [{
            'id': app.id,
            'name': app.name,
            'client_id': app.client_id[:10] + '...',  # Partial ID for security
            'created': app.date_added.isoformat() if hasattr(app, 'date_added') else 'unknown',
        } for app in google_apps]
        return JsonResponse({
            'count': google_apps.count(),
            'google_apps': apps_data,
            'message': 'To fix, make a POST request to this endpoint to keep only the latest app',
        })
    elif request.method == 'POST':
        count = google_apps.count()
        if count <= 1:
            return JsonResponse({'message': 'No duplicates to fix'})
        # Keep the most recently created app - usually has the highest ID
        latest_app = google_apps.order_by('-id').first()
        # Delete all other apps
        google_apps.exclude(id=latest_app.id).delete()
        return JsonResponse({
            'message': f'Fixed! Kept app ID {latest_app.id} and deleted {count-1} duplicate(s)',
            'remaining_app': {
                'id': latest_app.id, 
                'name': latest_app.name,
            }
        })

@login_required
def auth_debug_view(request):
    """View for debugging authentication status"""
    social_accounts = []
    # Get social accounts for current user
    for account in SocialAccount.objects.filter(user=request.user):
        social_accounts.append({
            'provider': account.provider,
            'uid': account.uid,
            'last_login': account.last_login,
            'date_joined': account.date_joined,
        })
    return JsonResponse({
        'uid': request.user.id,
        'email': request.user.email,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'role': request.user.role,
        'is_staff': request.user.is_staff,
        'social_accounts': social_accounts,
        'session_keys': list(request.session.keys()),
    })

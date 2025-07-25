from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from datetime import datetime
from django.db.models import Q

from rest_framework import generics
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser

from bunk_logs.campers.models import Camper
from bunk_logs.campers.models import CamperBunkAssignment

from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Unit
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.bunklogs.models import BunkLog, CounselorLog
from bunk_logs.orders.models import Order, OrderItem, Item, ItemCategory, OrderType

from .serializers import BunkLogSerializer, CounselorLogSerializer
from .serializers import BunkSerializer
from .serializers import CamperBunkAssignmentSerializer
from .serializers import CamperSerializer
from .serializers import UnitSerializer, UnitStaffAssignmentSerializer, SimpleBunkSerializer
from .serializers import CamperBunkLogSerializer
from .serializers import ApiUserSerializer
from .serializers import (
    OrderSerializer, OrderCreateSerializer, ItemSerializer, 
    ItemCategorySerializer, OrderTypeSerializer, SimpleOrderTypeSerializer,
    SimpleItemSerializer
)

from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken

import json
import logging
import csv
from io import TextIOWrapper

#from .permissions import BunkAccessPermission
#from .permissions import IsCounselorForBunk
#from .permissions import DebugPermission

User = get_user_model()

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class UserCreate(generics.CreateAPIView):
    """
    User registration view.
    """
    serializer_class = ApiUserSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication for user creation

class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = ApiUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    
def get_user_by_id(request, user_id):
    """
    Endpoint to get user details by ID.
    """
    try:
        user = User.objects.get(id=user_id)
        serializer = ApiUserSerializer(user)
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

class UserDetailsView(viewsets.ReadOnlyModelViewSet):
    """
    Custom User Details View to ensure JSON response
    """
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated]
    serializer_class = ApiUserSerializer
    
    def get_queryset(self):
        # Return queryset with just the current user
        User = get_user_model()
        return User.objects.filter(id=self.request.user.id)
    
    def list(self, request):
        user = request.user
        serializer = ApiUserSerializer(user)
        data = serializer.data
        
        # If you want to add groups as a special case (since it's a many-to-many field)
        data['groups'] = [group.name for group in user.groups.all()]
        
        # Manually add bunk data to avoid circular references
        from bunk_logs.bunks.models import CounselorBunkAssignment
        from django.utils import timezone
        from django.db import models
        
        assigned_bunks = []
        today = timezone.now().date()
        
        # Get active counselor assignments
        active_assignments = CounselorBunkAssignment.objects.filter(
            counselor=user,
            start_date__lte=today
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
        ).select_related('bunk', 'bunk__cabin', 'bunk__session')
        
        for assignment in active_assignments:
            bunk = assignment.bunk
            assigned_bunks.append({
                "id": str(bunk.id),
                "name": bunk.name,
                "cabin": str(bunk.cabin) if hasattr(bunk, 'cabin') and bunk.cabin else None,
                "session": str(bunk.session) if hasattr(bunk, 'session') and bunk.session else None,
                # Add any other basic bunk fields needed but avoid nesting counselors here
            })
        data['assigned_bunks'] = assigned_bunks

        return Response(data)

# Remove the existing retrieve method as we'll use a dedicated function-based view instead

@extend_schema(
    summary="Get user by email",
    description="Endpoint to get user details by email.",
    parameters=[
        OpenApiParameter(
            name='email',
            description='User email address',
            required=True,
            type=OpenApiTypes.STR,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ApiUserSerializer,
            description="User details retrieved successfully",
        ),
        404: OpenApiResponse(
            description="User not found",
        ),
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny
def get_user_by_email(request, email):
    """
    Endpoint to get user details by email.
    PERFORMANCE OPTIMIZED: Uses select_related and prefetch_related to minimize database queries.
    """
    try:
        # Optimize user query with select_related for groups
        user = User.objects.select_related().prefetch_related('groups').get(email=email)
        
        # Adjust security check to handle unauthenticated requests
        if request.user.is_authenticated:
            # For authenticated users, check permissions
            if not request.user.is_staff and request.user.email != email:
                # Special case for Unit Heads - they should see full details for users in their units
                if request.user.role == 'Unit Head':
                    # FIXED: Get units through UnitStaffAssignment instead of direct unit attribute
                    from bunk_logs.bunks.models import CounselorBunkAssignment, UnitStaffAssignment
                    from django.utils import timezone
                    from django.db import models
                    
                    today = timezone.now().date()
                    
                    # Get the requesting user's assigned units
                    user_units = UnitStaffAssignment.objects.filter(
                        staff_member=request.user,
                        role='unit_head',
                        start_date__lte=today
                    ).filter(
                        models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
                    ).values_list('unit_id', flat=True)
                    
                    if not user_units:
                        raise PermissionDenied("You do not have permission to view this user's details")
                    
                    # Use exists() for better performance - check if target user has assignments in any of the requesting user's units
                    has_counselor_assignment = CounselorBunkAssignment.objects.filter(
                        counselor=user,
                        bunk__unit_id__in=user_units,
                        start_date__lte=today
                    ).filter(
                        models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
                    ).exists()
                    
                    if not has_counselor_assignment:
                        raise PermissionDenied("You do not have permission to view this user's details")
                else:
                    raise PermissionDenied("You do not have permission to view this user's details")
        
        # PERFORMANCE FIX: Use optimized serializer that doesn't repeat queries
        # Instead of using the serializer, build the response directly to avoid duplicate queries
        from django.utils import timezone
        from django.db import models
        today = timezone.now().date()
        
        # PERFORMANCE FIX: Build response data that matches ApiUserSerializer format exactly
        # This ensures API compatibility while avoiding the performance issues
        data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "profile_complete": user.profile_complete,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "date_joined": user.date_joined,
            # Initialize fields that will be populated below to match serializer
            "bunks": [],
            "unit": None,
            "unit_bunks": [],
        }

        # PERFORMANCE OPTIMIZED: Single query with all necessary joins for counselor bunks
        # Populate the 'bunks' field to match ApiUserSerializer.get_bunks() format
        if user.role == 'Counselor':
            from bunk_logs.bunks.models import CounselorBunkAssignment
            active_assignments = CounselorBunkAssignment.objects.filter(
                counselor=user,
                start_date__lte=today
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
            ).select_related('bunk', 'bunk__cabin', 'bunk__session', 'bunk__unit')
            
            # Build bunks data in the same format as SimpleBunkSerializer
            bunks_data = []
            for assignment in active_assignments:
                bunk = assignment.bunk
                bunks_data.append({
                    "id": str(bunk.id),  # Convert to string for consistency
                    "counselors": [],  # Could be populated if needed, but expensive
                    "session": {
                        "id": bunk.session.id if bunk.session else None,
                        "name": bunk.session.name if bunk.session else None,
                    } if bunk.session else None,
                    "unit": {
                        "id": bunk.unit.id if bunk.unit else None,
                        "name": bunk.unit.name if bunk.unit else None,
                    } if bunk.unit else None,
                    "cabin": {
                        "id": bunk.cabin.id if bunk.cabin else None,
                        "name": bunk.cabin.name if bunk.cabin else None,
                    } if bunk.cabin else None,
                })
            data['bunks'] = bunks_data
        
        # Also maintain the 'assigned_bunks' field for backward compatibility
        assigned_bunks = []
        if user.role == 'Counselor':
            # Simplified version for the assigned_bunks field  
            for assignment in active_assignments:
                bunk = assignment.bunk
                assigned_bunks.append({
                    "id": str(bunk.id),
                    "bunk_id": str(bunk.id),
                    "name": bunk.name,
                    "cabin": str(bunk.cabin) if hasattr(bunk, 'cabin') and bunk.cabin else None,
                    "session": str(bunk.session) if hasattr(bunk, 'session') and bunk.session else None,
                })
        data['assigned_bunks'] = assigned_bunks
        
        # PERFORMANCE OPTIMIZED: Unit Head data with single optimized query
        if user.role == 'Unit Head':
            from bunk_logs.bunks.models import UnitStaffAssignment
            
            # Single query with select_related for units
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
                start_date__lte=today,
                end_date__isnull=True
            ).select_related('unit')
            
            units = []
            first_unit = None
            
            for assignment in unit_assignments:
                unit = assignment.unit
                units.append({
                    "id": str(unit.id),
                    "name": unit.name,
                })
                if first_unit is None:
                    first_unit = unit
            
            data['units'] = units
            
            # Populate 'unit' field to match ApiUserSerializer.get_unit() format
            if first_unit:
                # Build unit data in UnitSerializer format (simplified)
                data['unit'] = {
                    "id": first_unit.id,
                    "name": first_unit.name,
                    "created_at": first_unit.created_at,
                    "updated_at": first_unit.updated_at,
                    # Note: Skipping complex nested data for performance
                    "unit_head_details": None,
                    "camper_care_details": None,
                    "staff_assignments": [],
                    "unit_heads": [],
                    "camper_care_staff": [],
                }
                data['unit_name'] = first_unit.name
                
                # Populate 'unit_bunks' field to match ApiUserSerializer.get_unit_bunks() format
                unit_bunks = Bunk.objects.filter(unit=first_unit).select_related('cabin', 'session', 'unit')
                unit_bunks_data = []
                for bunk in unit_bunks:                unit_bunks_data.append({
                    "id": str(bunk.id),  # Convert to string for consistency
                    "name": bunk.name,   # Add missing name field - CRITICAL FIX
                    "counselors": [],  # Simplified for performance
                    "session": {
                        "id": bunk.session.id if bunk.session else None,
                        "name": bunk.session.name if bunk.session else None,
                    } if bunk.session else None,
                    "unit": {
                        "id": bunk.unit.id if bunk.unit else None,
                        "name": bunk.unit.name if bunk.unit else None,
                    } if bunk.unit else None,
                    "cabin": {
                        "id": bunk.cabin.id if bunk.cabin else None,
                        "name": bunk.cabin.name if bunk.cabin else None,
                    } if bunk.cabin else None,
                })
                data['unit_bunks'] = unit_bunks_data
        
        # If the user is not authenticated, only return basic non-sensitive information
        if not request.user.is_authenticated:
            # Filter data to only include safe fields - maintain consistent naming
            safe_data = {
                "id": data.get("id"),
                "email": data.get("email"),
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "role": data.get("role"),
                "bunks": data.get("bunks", []),  # Use 'bunks' for consistency with serializer
                "assigned_bunks": data.get("assigned_bunks", []),  # Keep for backward compatibility
                "units": data.get("units", []),
                "unit_name": data.get("unit_name"),
                "unit_bunks": data.get("unit_bunks", []),
            }
            return Response(safe_data)
            
        # For authenticated users, add groups (already prefetched) and return all data
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

@extend_schema(
    summary="Get bunk logs by date",
    description="API view to get bunk logs info by date. The endpoint searches for all of the bunk assignments for the bunk on that date, then searches for all of the bunk logs for those assignments.",
    parameters=[
        OpenApiParameter(
            name='bunk_id',
            description='Bunk ID',
            required=True,
            type=OpenApiTypes.STR,
        ),
        OpenApiParameter(
            name='date',
            description='Date in YYYY-MM-DD format',
            required=True,
            type=OpenApiTypes.DATE,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Bunk logs data retrieved successfully",
        ),
        403: OpenApiResponse(
            description="Permission denied",
        ),
        404: OpenApiResponse(
            description="Bunk not found",
        ),
    },
)
class BunkLogsInfoByDateViewSet(APIView):
    """         
    API view to get bunk logs info by date.
    The endpoint will be '/api/v1/bunklogs/<str:bunk_id>/logs/<str:date>/''
    where 'bunk_id' is the ID of the bunk and 'date' is the date in YYYY-MM-DD format.
    The response will first search for all of the bunk_assignemnts for the bunk on that date.
    Then, it will search for all of the bunk logs for those assignments.
    The response will include the bunk assignment ID and the bunk log ID.
    If no bunk logs are found, the response will return an empty list.
    """
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, bunk_id, date):
        # Import Bunk at the beginning
        from bunk_logs.bunks.models import Bunk
        
        # Check permissions first
        user = request.user
        
        # Admin/staff can access all bunks
        if not (user.is_staff or user.role == 'Admin'):
            from bunk_logs.bunks.models import UnitStaffAssignment
            from django.utils import timezone
            from datetime import datetime
            
            # Parse the date for permission checks
            try:
                query_date = datetime.strptime(date, "%Y-%m-%d").date()
            except Exception:
                return Response({"error": "Invalid date format"}, status=400)
            
            # Unit heads can access bunks in their units (via UnitStaffAssignment)
            if user.role == 'Unit Head':
                # Check if user has unit head assignment for this bunk's unit on the given date
                unit_head_assignments = UnitStaffAssignment.objects.filter(
                    staff_member=user,
                    role='unit_head',
                    start_date__lte=query_date,
                ).filter(Q(end_date__isnull=True) | Q(end_date__gte=query_date))
                
                # Check if any of these assignments are for units containing this bunk
                has_access = False
                for assignment in unit_head_assignments:
                    if Bunk.objects.filter(id=bunk_id, unit=assignment.unit).exists():
                        has_access = True
                        break
                
                if not has_access:
                    logger.warning(
                        f"403 Forbidden: User {user.id} ({user.role}) attempted to access bunk {bunk_id} on {query_date}, but lacks permissions."
                    )
                    return Response({"error": "You are not authorized to access this bunk's data"}, status=403)
                    
            # Camper care can access bunks in their assigned units (via UnitStaffAssignment)
            elif user.role == 'Camper Care':
                # Check if user has camper care assignment for this bunk's unit on the given date
                camper_care_assignments = UnitStaffAssignment.objects.filter(
                    staff_member=user,
                    role='camper_care',
                    start_date__lte=query_date,
                ).filter(Q(end_date__isnull=True) | Q(end_date__gte=query_date))
                
                # Check if any of these assignments are for units containing this bunk
                has_access = False
                for assignment in camper_care_assignments:
                    if Bunk.objects.filter(id=bunk_id, unit=assignment.unit).exists():
                        has_access = True
                        break
                
                # Fallback to legacy camper_care field if no staff assignments found
                if not has_access:
                    has_access = Bunk.objects.filter(id=bunk_id, unit__camper_care=user).exists()
                
                if not has_access:
                    logger.warning(
                        f"403 Forbidden: User {user.id} ({user.role}) attempted to access bunk {bunk_id} on {query_date}, but lacks permissions."
                    )
                    return Response({"error": "You are not authorized to access this bunk's data"}, status=403)
                    
            # Counselors can only access their assigned bunks
            elif user.role == 'Counselor':
                if not Bunk.objects.filter(id=bunk_id, counselor_assignments__counselor__id=user.id).exists():
                    logger.warning(
                        f"403 Forbidden: User {user.id} ({user.role}) attempted to access bunk {bunk_id} on {query_date}, but lacks permissions."
                    )
                    return Response({"error": "You are not authorized to access this bunk's data"}, status=403)
            else:
                logger.warning(
                    f"403 Forbidden: User {user.id} ({user.role}) attempted to access bunk {bunk_id} on {query_date}, but lacks permissions."
                )
                return Response({"error": "You are not authorized to access this bunk's data"}, status=403)
        
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
            counselors_data = []
            current_counselors = bunk.get_current_counselors()
            for counselor in current_counselors:
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
            logger.error(f"Error in BunkLogsInfoByDateViewSet for bunk {bunk_id}, date {date}, user {user.email}: {str(e)}")
            return Response({"error": f"Internal server error: {str(e)}"}, status=500)

class UnitViewSet(viewsets.ModelViewSet):
    renderer_classes = [JSONRenderer]
    permission_classes = [AllowAny]
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer

    @action(detail=True, methods=['post'])
    def assign_staff(self, request, pk=None):
        """Assign staff member to unit with specific role."""
        unit = self.get_object()
        staff_member_id = request.data.get('staff_member_id')
        role = request.data.get('role')
        is_primary = request.data.get('is_primary', False)

        if role not in ['unit_head', 'camper_care']:
            return Response({'error': 'Invalid role'}, status=400)

        try:
            from bunk_logs.users.models import User
            staff_member = User.objects.get(id=staff_member_id)
        except User.DoesNotExist:
            return Response({'error': 'Staff member not found'}, status=404)

        # If setting as primary, unset other primary assignments for this role
        if is_primary:
            UnitStaffAssignment.objects.filter(
                unit=unit, 
                role=role, 
                is_primary=True
            ).update(is_primary=False)

        assignment, created = UnitStaffAssignment.objects.get_or_create(
            unit=unit,
            staff_member=staff_member,
            role=role,
            defaults={'is_primary': is_primary}
        )

        if not created:
            assignment.is_primary = is_primary
            assignment.save()

        return Response(UnitStaffAssignmentSerializer(assignment).data)

    @action(detail=True, methods=['delete'])
    def remove_staff(self, request, pk=None):
        """Remove staff assignment from unit."""
        unit = self.get_object()
        assignment_id = request.data.get('assignment_id')
        
        try:
            assignment = UnitStaffAssignment.objects.get(
                id=assignment_id, 
                unit=unit
            )
            assignment.delete()
            return Response(status=204)
        except UnitStaffAssignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)


class UnitStaffAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for UnitStaffAssignment model.
    - GET /api/unit-staff-assignments/ - List all assignments
    - POST /api/unit-staff-assignments/ - Create new assignment
    - GET /api/unit-staff-assignments/{id}/ - Retrieve specific assignment by staff_member's user_id
    - PUT /api/unit-staff-assignments/{id}/ - Update assignment
    - DELETE /api/unit-staff-assignments/{id}/ - Delete assignment
    """
    queryset = UnitStaffAssignment.objects.all().select_related('unit', 'staff_member')
    serializer_class = UnitStaffAssignmentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'staff_member__id'  # Use staff_member's user_id as the lookup field

    def get_queryset(self):
        """Filter assignments based on query parameters."""
        queryset = super().get_queryset()

        # Filter by unit
        unit_id = self.request.query_params.get('unit', None)
        if unit_id:
            queryset = queryset.filter(unit_id=unit_id)

        # Filter by role
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)

        # Filter by active assignments (no end date)
        active_only = self.request.query_params.get('active_only', None)
        if active_only == 'true':
            queryset = queryset.filter(end_date__isnull=True)

        return queryset

    def get_object(self):
        """Retrieve a specific assignment by staff_member's user_id."""
        user_id = self.kwargs.get(self.lookup_field)
        try:
            return self.queryset.get(staff_member__id=user_id)
        except UnitStaffAssignment.DoesNotExist:
            raise Http404("UnitStaffAssignment matching query does not exist.")
        except UnitStaffAssignment.MultipleObjectsReturned:
            # Handle multiple assignments by returning the latest one
            return self.queryset.filter(staff_member__id=user_id).order_by('-start_date').first()

    def perform_create(self, serializer):
        """Handle assignment creation with business logic."""
        is_primary = serializer.validated_data.get('is_primary', False)
        unit = serializer.validated_data.get('unit')
        role = serializer.validated_data.get('role')

        # If setting as primary, unset other primary assignments for this role
        if is_primary:
            UnitStaffAssignment.objects.filter(
                unit=unit, 
                role=role, 
                is_primary=True
            ).update(is_primary=False)

        serializer.save()

    def perform_update(self, serializer):
        """Handle assignment updates with business logic."""
        is_primary = serializer.validated_data.get('is_primary', False)
        instance = self.get_object()

        # If setting as primary, unset other primary assignments for this role
        if is_primary:
            UnitStaffAssignment.objects.filter(
                unit=instance.unit, 
                role=instance.role, 
                is_primary=True
            ).exclude(id=instance.id).update(is_primary=False)

        serializer.save()

class CamperViewSet(viewsets.ModelViewSet):
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated]
    queryset = Camper.objects.all()
    serializer_class = CamperSerializer
    
    def get_queryset(self):
        """Filter campers based on user role and permissions."""
        user = self.request.user
        
        # Admin/staff can see all campers
        if user.is_staff or user.role == 'Admin':
            return Camper.objects.all()
        
        # Unit heads can see campers in their units
        if user.role == 'Unit Head':
            from django.utils import timezone
            unit_ids = []
            # Get units via UnitStaffAssignment - get units where user is assigned as unit_head
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            return Camper.objects.filter(
                bunk_assignments__bunk__unit_id__in=unit_assignments,
                bunk_assignments__is_active=True
            ).distinct()
        
        # Camper care can see campers in their assigned units
        if user.role == 'Camper Care':
            from django.utils import timezone
            unit_ids = []
            # Get units via UnitStaffAssignment - get units where user is assigned as camper_care
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='camper_care',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            return Camper.objects.filter(
                bunk_assignments__bunk__unit_id__in=unit_assignments,
                bunk_assignments__is_active=True
            ).distinct()
        
        # Counselors can see campers in their bunks
        if user.role == 'Counselor':
            # Get bunks from counselor assignments
            from bunk_logs.bunks.models import CounselorBunkAssignment
            from django.utils import timezone
            from django.db import models
            
            today = timezone.now().date()
            active_assignments = CounselorBunkAssignment.objects.filter(
                counselor=user,
                start_date__lte=today
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
            )
            assigned_bunks = [assignment.bunk for assignment in active_assignments]
            
            return Camper.objects.filter(
                bunk_assignments__bunk__in=assigned_bunks,
                bunk_assignments__is_active=True
            ).distinct()
        
        # Default: see nothing
        return Camper.objects.none()
    
    def perform_create(self, serializer):
        """Only staff can create campers."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can create campers.")
        serializer.save()
    
    def perform_update(self, serializer):
        """Only staff can update campers."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can update campers.")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only staff can delete campers."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can delete campers.")
        instance.delete()


class CamperBunkAssignmentViewSet(viewsets.ModelViewSet):
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated]
    queryset = CamperBunkAssignment.objects.all()
    serializer_class = CamperBunkAssignmentSerializer
    
    def get_queryset(self):
        """Filter assignments based on user role and permissions."""
        user = self.request.user
        
        # Admin/staff can see all assignments
        if user.is_staff or user.role == 'Admin':
            return CamperBunkAssignment.objects.all()
        
        # Unit heads can see assignments in their units
        if user.role == 'Unit Head':
            from django.utils import timezone
            unit_ids = []
            # Get units via UnitStaffAssignment - get units where user is assigned as unit_head
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            return CamperBunkAssignment.objects.filter(
                bunk__unit_id__in=unit_assignments
            )
        
        # Camper care can see assignments in their assigned units
        if user.role == 'Camper Care':
            from django.utils import timezone
            unit_ids = []
            # Get units via UnitStaffAssignment - get units where user is assigned as camper_care
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='camper_care',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            return CamperBunkAssignment.objects.filter(
                bunk__unit_id__in=unit_assignments
            )
        
        # Counselors can see assignments in their bunks
        if user.role == 'Counselor':
            # Get bunks from counselor assignments
            from bunk_logs.bunks.models import CounselorBunkAssignment
            from django.utils import timezone
            from django.db import models
            
            today = timezone.now().date()
            active_assignments = CounselorBunkAssignment.objects.filter(
                counselor=user,
                start_date__lte=today
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
            )
            assigned_bunks = [assignment.bunk for assignment in active_assignments]
            
            return CamperBunkAssignment.objects.filter(
                bunk__in=assigned_bunks
            )
        
        # Default: see nothing
        return CamperBunkAssignment.objects.none()
    
    def perform_create(self, serializer):
        """Only staff can create assignments."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can create camper bunk assignments.")
        serializer.save()
    
    def perform_update(self, serializer):
        """Only staff can update assignments."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can update camper bunk assignments.")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only staff can delete assignments."""
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff members can delete camper bunk assignments.")
        instance.delete()

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
            # Get units where user is assigned as unit_head via UnitStaffAssignment
            from django.utils import timezone
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            
            return BunkLog.objects.filter(
                bunk_assignment__bunk__unit_id__in=unit_assignments
            )
        # Camper care can see logs for bunks in their assigned units
        if user.role == 'Camper Care':
            # Check staff assignments
            unit_ids = []
            # Get units via UnitStaffAssignment - get units where user is assigned as camper_care
            from django.utils import timezone
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='camper_care',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            return BunkLog.objects.filter(
                bunk_assignment__bunk__unit_id__in=unit_assignments
            )
        # Counselors can only see logs for their bunks
        if user.role == 'Counselor':
            # Get bunks from counselor assignments
            from bunk_logs.bunks.models import CounselorBunkAssignment
            from django.utils import timezone
            from django.db import models
            
            today = timezone.now().date()
            active_assignments = CounselorBunkAssignment.objects.filter(
                counselor=user,
                start_date__lte=today
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
            )
            assigned_bunks = [assignment.bunk for assignment in active_assignments]
            
            return BunkLog.objects.filter(
                bunk_assignment__bunk__in=assigned_bunks
            )
        # Default: see nothing
        return BunkLog.objects.none()

    def perform_create(self, serializer):
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError
        from rest_framework import serializers as drf_serializers
        
        # Verify the user is allowed to create a log for this bunk assignment
        bunk_assignment = serializer.validated_data.get('bunk_assignment')
        if self.request.user.role == 'Counselor':
            # Check if user is a counselor for this bunk using new assignment system
            from bunk_logs.bunks.models import CounselorBunkAssignment
            from django.utils import timezone
            from django.db import models
            
            today = timezone.now().date()
            has_assignment = CounselorBunkAssignment.objects.filter(
                counselor=self.request.user,
                bunk=bunk_assignment.bunk,
                start_date__lte=today
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
            ).exists()
            
            if not has_assignment:
                raise PermissionDenied("You are not authorized to create logs for this bunk.")
        
        # Remove any date from validated_data to let the model's save method handle it
        if 'date' in serializer.validated_data:
            del serializer.validated_data['date']
        
        # Set the counselor automatically to the current user
        try:
            serializer.save(counselor=self.request.user)
        except (ValidationError, IntegrityError) as exc:
            # Handle duplicate entry and other validation errors
            error_messages = []
            
            if isinstance(exc, ValidationError):
                if hasattr(exc, 'message_dict'):
                    # Handle field-specific errors
                    for field, messages in exc.message_dict.items():
                        if isinstance(messages, list):
                            error_messages.extend(messages)
                        else:
                            error_messages.append(str(messages))
                elif hasattr(exc, 'messages'):
                    # Handle non-field errors
                    error_messages.extend(exc.messages)
                else:
                    error_messages.append(str(exc))
            elif isinstance(exc, IntegrityError):
                # Handle database integrity errors (like unique constraint violations)
                error_messages.append(str(exc))
            
            # Check if this is a duplicate entry error
            error_text = ' '.join(error_messages).lower()
            if ('unique' in error_text or 'duplicate' in error_text or 
                'already exists' in error_text or 'constraint' in error_text):
                # Check if it's specifically about bunk_assignment + date uniqueness
                if 'bunk_assignment' in error_text and 'date' in error_text:
                    raise drf_serializers.ValidationError({
                        'non_field_errors': ['A bunk log already exists for this camper on this date.']
                    })
                else:
                    raise drf_serializers.ValidationError({
                        'non_field_errors': ['A bunk log already exists for this camper on this date.']
                    })
            else:
                # Re-raise as DRF validation error
                raise drf_serializers.ValidationError({
                    'non_field_errors': error_messages
                })

    def perform_update(self, serializer):
        # Verify the user is allowed to update this bunk log
        instance = self.get_object()
        user = self.request.user
        
        # Admin/staff can update any log
        if user.is_staff or user.role == 'Admin':
            serializer.save()
            return
            
        # Unit heads can update logs for bunks in their units
        if user.role == 'Unit Head':
            # Check staff assignments via UnitStaffAssignment
            from django.utils import timezone
            has_access = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
                unit__bunks=instance.bunk_assignment.bunk,
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).exists()
            
            if has_access:
                serializer.save()
                return
            else:
                raise PermissionDenied("You are not authorized to update logs for this bunk.")
        
        # Camper care can update logs for bunks in their assigned units
        if user.role == 'Camper Care':
            # Check staff assignments
            has_access = False
            # Legacy approach
            from bunk_logs.bunks.models import Bunk
            if Bunk.objects.filter(id=instance.bunk_assignment.bunk.id, unit__camper_care=user).exists():
                has_access = True
            # New approach - check staff assignments
            from django.utils import timezone
            if UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='camper_care',
                unit__bunks=instance.bunk_assignment.bunk,
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).exists():
                has_access = True
            
            if has_access:
                serializer.save()
                return
            else:
                raise PermissionDenied("You are not authorized to update logs for this bunk.")
        
        # Counselors have specific restrictions
        if user.role == 'Counselor':
            # Check if user is a counselor for this bunk using new assignment system
            from bunk_logs.bunks.models import CounselorBunkAssignment
            from django.utils import timezone
            from django.db import models
            
            today = timezone.now().date()
            has_assignment = CounselorBunkAssignment.objects.filter(
                counselor=user,
                bunk=instance.bunk_assignment.bunk,
                start_date__lte=today
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
            ).exists()
            
            if not has_assignment:
                raise PermissionDenied("You are not authorized to update logs for this bunk.")
            
            # Check if user is the original counselor who created the log
            if instance.counselor.id != user.id:
                raise PermissionDenied("You can only update logs you created.")
            
            # Check if the update is happening on the same day the log was created
            from django.utils import timezone
            today = timezone.now().date()
            log_created_date = instance.created_at.date() if instance.created_at else instance.date
            
            if today != log_created_date:
                raise PermissionDenied("You can only update logs on the day they were created.")
            
            # Don't allow changing the counselor field during update
            if 'counselor' in serializer.validated_data:
                serializer.validated_data['counselor'] = instance.counselor
            
            serializer.save()
            return
        
        # Default: deny access
        raise PermissionDenied("You are not authorized to update this bunk log.")


class CounselorLogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = CounselorLog.objects.all()
    serializer_class = CounselorLogSerializer
    
    def get_queryset(self):
        user = self.request.user
        # Admin/staff can see all counselor logs
        if user.is_staff or user.role == 'Admin':
            return CounselorLog.objects.all()
        # Unit heads can see logs for counselors in their units
        if user.role == 'Unit Head':
            # Get units where user is assigned as unit_head
            from django.utils import timezone
            unit_ids = []
            # Get units via UnitStaffAssignment - get units where user is assigned as unit_head
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            # Get counselors assigned to bunks in these units
            counselor_ids = Bunk.objects.filter(
                unit_id__in=unit_assignments
            ).values_list('counselor_assignments__counselor', flat=True).distinct()
            
            return CounselorLog.objects.filter(counselor_id__in=counselor_ids)
        # Camper care can see logs for counselors in their assigned units
        if user.role == 'Camper Care':
            # Get units where user is assigned as camper_care
            from django.utils import timezone
            unit_ids = []
            # Get units via UnitStaffAssignment - get units where user is assigned as camper_care
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='camper_care',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            # Get counselors assigned to bunks in these units
            counselor_ids = Bunk.objects.filter(
                unit_id__in=unit_assignments
            ).values_list('counselor_assignments__counselor', flat=True).distinct()
            
            return CounselorLog.objects.filter(counselor_id__in=counselor_ids)
        # Counselors can only see their own logs
        if user.role == 'Counselor':
            return CounselorLog.objects.filter(counselor=user)
        # Default: see nothing
        return CounselorLog.objects.none()
    
    def perform_create(self, serializer):
        # Remove any date from validated_data to let the model's save method handle it
        if 'date' in serializer.validated_data:
            del serializer.validated_data['date']
            
        if self.request.user.role != 'Counselor':
            serializer.save()
        else:
            # Set the counselor automatically to the current user
            serializer.save(counselor=self.request.user)
    
    def perform_update(self, serializer):
        instance = serializer.instance
        user = self.request.user
        
        # Admin/staff can update any log
        if user.is_staff or user.role == 'Admin':
            serializer.save()
            return
        
        # Unit heads and camper care cannot update counselor logs (view-only)
        if user.role in ['Unit Head', 'Camper Care']:
            raise PermissionDenied("You can view but not edit counselor logs.")
        
        # Counselors have specific restrictions
        if user.role == 'Counselor':
            # Check if user is the counselor who created the log
            if instance.counselor.id != user.id:
                raise PermissionDenied("You can only update your own counselor logs.")
            
            # Check if the update is happening on the same day the log was created
            from django.utils import timezone
            today = timezone.now().date()
            log_created_date = instance.created_at.date() if instance.created_at else instance.date
            
            if today != log_created_date:
                raise PermissionDenied("You can only update counselor logs on the day they were created.")
            
            # Don't allow changing the counselor field during update
            if 'counselor' in serializer.validated_data:
                serializer.validated_data['counselor'] = instance.counselor
            
            serializer.save()
            return
        
        # Default: deny access
        raise PermissionDenied("You are not authorized to update this counselor log.")

    def perform_create(self, serializer):
        # Ensure the date is always a date object in the server's timezone
        from django.utils import timezone
        import datetime
        validated_data = serializer.validated_data
        log_date = validated_data.get('date')
        if isinstance(log_date, datetime.datetime):
            # Convert to local date
            log_date = timezone.localtime(log_date).date()
            serializer.validated_data['date'] = log_date
        elif isinstance(log_date, str):
            # Parse string to date
            try:
                log_date = datetime.datetime.strptime(log_date, '%Y-%m-%d').date()
                serializer.validated_data['date'] = log_date
            except Exception:
                pass
        if self.request.user.role != 'Counselor':
            serializer.save()
        else:
            # Set the counselor automatically to the current user
            serializer.save(counselor=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Filter by date if provided
        date_param = request.query_params.get('date', None)
        if date_param:
            try:
                # Parse the date parameter and filter the queryset
                from datetime import datetime
                parsed_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                queryset = queryset.filter(date=parsed_date)
            except ValueError:
                # Invalid date format, ignore the filter
                pass
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({'results': serializer.data})
    
    def perform_update(self, serializer):
        instance = serializer.instance
        user = self.request.user
        
        # Admin and staff can update any log
        if user.is_staff or user.role == 'Admin':
            serializer.save()
            return
            
        # Unit heads and camper care can view but not edit
        if user.role in ['Unit Head', 'Camper Care']:
            raise PermissionDenied("You can view but not edit counselor logs.")
        
        # Counselors can only update their own logs
        if user.role == 'Counselor':
            if instance.counselor.id != user.id:
                raise PermissionDenied("You can only update your own counselor logs.")
            
            # Check if the update is happening on the same day the log was created
            from django.utils import timezone
            today = timezone.now().date()
            log_created_date = instance.created_at.date() if instance.created_at else instance.date
            
            if today != log_created_date:
                raise PermissionDenied("You can only update counselor logs on the day they were created.")
            
            # Don't allow changing the counselor field during update
            if 'counselor' in serializer.validated_data:
                serializer.validated_data['counselor'] = instance.counselor
            
            serializer.save()
            return
        
        # Default: deny access
        raise PermissionDenied("You are not authorized to update this counselor log.")
    
    @action(detail=False, methods=['get'], url_path=r'(?P<date>\d{4}-\d{2}-\d{2})')
    def by_date(self, request, date=None):
        """
        Custom action to get counselor logs by date with timezone support.
        URL: /api/v1/counselorlogs/2025-06-25/?timezone=America/New_York
        """
        # Validate date format
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            from django.utils import timezone as django_timezone
            
            query_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD format."}, status=400)
        
        # Get timezone from query parameter, default to UTC
        timezone_str = request.query_params.get('timezone', 'UTC')
        
        try:
            # Validate timezone
            user_timezone = ZoneInfo(timezone_str)
        except Exception:
            return Response({"error": f"Invalid timezone: {timezone_str}"}, status=400)
        
        # Create start and end of the local day in the user's timezone
        local_start = datetime.combine(query_date, datetime.min.time()).replace(tzinfo=user_timezone)
        local_end = datetime.combine(query_date, datetime.max.time()).replace(tzinfo=user_timezone)
        
        # Convert to UTC for database filtering
        utc_start = local_start.astimezone(ZoneInfo('UTC'))
        utc_end = local_end.astimezone(ZoneInfo('UTC'))
        
        # Get the filtered queryset based on user permissions
        queryset = self.get_queryset()
        
        # Filter by created_at timestamp within the local day boundaries
        queryset = queryset.filter(
            created_at__gte=utc_start,
            created_at__lte=utc_end
        )
        
        # Order logs by counselor name for consistent output
        queryset = queryset.select_related('counselor').order_by(
            'counselor__first_name', 
            'counselor__last_name'
        )
        
        # Serialize the logs
        serializer = self.get_serializer(queryset, many=True)
        
        # Return response in the same format as the list view but with date info
        response_data = {
            "date": date,
            "timezone": timezone_str,
            "local_day_start": local_start.isoformat(),
            "local_day_end": local_end.isoformat(),
            "total_logs": queryset.count(),
            "results": serializer.data
        }
        
        return Response(response_data)

class CamperBunkLogViewSet(APIView):
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated]
    queryset = BunkLog.objects.all()
    serializer_class = BunkLogSerializer
    
    def get(self, request, camper_id):
        user = request.user
        
        try:
            # Get the camper
            camper = Camper.objects.get(id=camper_id)
            
            # Check permissions
            # Admin/staff can see all camper logs
            if not (user.is_staff or user.role == 'Admin'):
                # Get camper's current bunk assignments
                current_assignments = CamperBunkAssignment.objects.filter(
                    camper=camper, 
                    is_active=True
                )
                
                has_access = False
                
                # Unit heads can see logs for campers in their units
                if user.role == 'Unit Head':
                    from django.utils import timezone
                    unit_ids = []
                    # Get units via UnitStaffAssignment - get units where user is assigned as unit_head
                    unit_assignments = UnitStaffAssignment.objects.filter(
                        staff_member=user,
                        role='unit_head',
                        start_date__lte=timezone.now().date(),
                    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.now().date())).values_list('unit_id', flat=True)
                    unit_ids.extend(unit_assignments)
                    
                    # Check if camper has ANY assignments (past or present) in the assigned units
                    all_assignments = CamperBunkAssignment.objects.filter(
                        camper=camper
                    )
                    has_access = all_assignments.filter(
                        bunk__unit_id__in=unit_assignments
                    ).exists()
                
                # Camper care can see logs for campers in their assigned units
                elif user.role == 'Camper Care':
                    from django.utils import timezone
                    unit_ids = []
                    # Get units via UnitStaffAssignment - get units where user is assigned as camper_care
                    unit_assignments = UnitStaffAssignment.objects.filter(
                        staff_member=user,
                        role='camper_care',
                        start_date__lte=timezone.now().date(),
                    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.now().date())).values_list('unit_id', flat=True)
                    unit_ids.extend(unit_assignments)
                    
                    # Check if camper has ANY assignments (past or present) in the assigned units
                    all_assignments = CamperBunkAssignment.objects.filter(
                        camper=camper
                    )
                    has_access = all_assignments.filter(
                        bunk__unit_id__in=unit_assignments
                    ).exists()
                
                # Counselors can see logs for campers in their bunks
                elif user.role == 'Counselor':
                    # Get bunks from counselor assignments
                    from bunk_logs.bunks.models import CounselorBunkAssignment
                    from django.utils import timezone
                    from django.db import models
                    
                    today = timezone.now().date()
                    active_assignments = CounselorBunkAssignment.objects.filter(
                        counselor=user,
                        start_date__lte=today
                    ).filter(
                        models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
                    )
                    assigned_bunks = [assignment.bunk for assignment in active_assignments]
                    
                    has_access = current_assignments.filter(
                        bunk__in=assigned_bunks
                    ).exists()
                
                if not has_access:
                    return Response({"error": "You are not authorized to access this camper's data"}, status=403)
            
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
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# Order-related API Views

@extend_schema(
    parameters=[
        OpenApiParameter(
            name='id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Order ID'
        ),
    ]
)
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
        """Filter orders based on user role and optional filter parameters."""
        user = self.request.user
        
        # Start with base queryset based on user role
        if user.is_staff or user.role in ['Counselor', 'Admin', 'Camper Care']:
            # Staff, counselors, and camper care can see all orders
            queryset = Order.objects.all().select_related('user', 'order_bunk', 'order_type').prefetch_related('order_items__item')
        else:
            # Regular users can only see their own orders
            queryset = Order.objects.filter(user=user).select_related('user', 'order_bunk', 'order_type').prefetch_related('order_items__item')
        
        # Apply bunk filter if provided
        bunk_id = self.request.query_params.get('bunk', None)
        if bunk_id is not None:
            queryset = queryset.filter(order_bunk_id=bunk_id)
        
        # Apply status filter if provided
        status = self.request.query_params.get('status', None)
        if status is not None:
            queryset = queryset.filter(order_status=status)
        
        # Apply order type filter if provided
        order_type_id = self.request.query_params.get('order_type', None)
        if order_type_id is not None:
            queryset = queryset.filter(order_type_id=order_type_id)
            
        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for create vs read operations."""
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def perform_create(self, serializer):
        """Set the user to the current authenticated user."""
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        """Handle order updates with permission checks."""
        user = self.request.user
        order = self.get_object()
        
        # Check if user can update orders
        if not (user.is_staff or user.role in ['Admin', 'Camper Care']):
            # Regular users can only update their own pending orders
            if order.user != user:
                raise PermissionDenied("You can only update your own orders.")
            if order.order_status != 'submitted':
                raise PermissionDenied("You can only update orders that are in 'Submitted' status.")
        
        # For status updates, check if user has permission to change from submitted
        if 'order_status' in serializer.validated_data:
            new_status = serializer.validated_data['order_status']
            if order.order_status == 'submitted' and new_status != 'submitted':
                # Only Camper Care and Admin can change status from 'submitted'
                if not (user.is_staff or user.role in ['Admin', 'Camper Care']):
                    raise PermissionDenied("Only Camper Care and Admin users can update order status from 'Submitted'.")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Handle order deletion with permission checks."""
        user = self.request.user
        
        # Check if user can delete orders
        if not (user.is_staff or user.role in ['Admin', 'Camper Care']):
            # Regular users can only delete their own submitted orders
            if instance.user != user:
                raise PermissionDenied("You can only delete your own orders.")
            if instance.order_status != 'submitted':
                raise PermissionDenied("You can only delete orders that are in 'Submitted' status.")
        
        instance.delete()


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


@extend_schema(
    summary="Get items for order type",
    description="Get available items for a specific order type. Returns items from categories associated with the order type.",
    parameters=[
        OpenApiParameter(
            name='order_type_id',
            description='Order type ID',
            required=True,
            type=OpenApiTypes.INT,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Items retrieved successfully",
        ),
        404: OpenApiResponse(
            description="Order type not found",
        ),
    },
)
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


@extend_schema(
    summary="Get order statistics",
    description="Get statistics about orders.",
    responses={
        200: OpenApiResponse(
            description="Order statistics retrieved successfully",
        ),
    },
)
@extend_schema(
    summary="Get order statistics",
    description="Get statistics about orders.",
    responses={
        200: OpenApiResponse(
            description="Order statistics retrieved successfully",
        ),
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_statistics(request):
    """Get statistics about orders."""
    try:
        from bunk_logs.orders.models import Order
        
        total_orders = Order.objects.filter(user=request.user).count()
        pending_orders = Order.objects.filter(user=request.user, order_status='pending').count()
        completed_orders = Order.objects.filter(user=request.user, order_status='completed').count()
        
        return Response({
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@extend_schema(
    summary="Debug user bunks",
    description="Temporary debug endpoint to check user-bunk relationships",
    responses={
        200: OpenApiResponse(
            description="User-bunk relationship data retrieved successfully",
        ),
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_user_bunks(request):
    """Temporary debug endpoint to check user-bunk relationships"""
    from bunk_logs.bunks.models import Bunk
    user_data = {
        "email": request.user.email,
        "id": request.user.id,
        "role": request.user.role,
        "is_staff": request.user.is_staff,
    }
    # Check direct assigned bunks - only get the id field,
    bunks_query = Bunk.objects.filter(counselor_assignments__counselor__id=request.user.id)
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

from .serializers import SocialAppDiagnosticResponseSerializer

class FixSocialAppsView(APIView):
    """Diagnostic endpoint to fix MultipleObjectsReturned error with Google OAuth."""
    permission_classes = [IsAuthenticated]
    serializer_class = SocialAppDiagnosticResponseSerializer

    @extend_schema(
        summary="Fix social authentication apps",
        description="Diagnostic endpoint to fix MultipleObjectsReturned error with Google OAuth. GET: List all SocialApp entries for Google. POST: Keep only the most recent app and delete duplicates",
        methods=['GET', 'POST'],
        responses={
            200: OpenApiResponse(
                response=SocialAppDiagnosticResponseSerializer,
                description="Social apps diagnostic information or fix completed",
            ),
            403: OpenApiResponse(description="Forbidden - Staff access required"),
        }
    )
    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': 'Staff access required'}, status=403)
        google_apps = SocialApp.objects.filter(provider='google')
        apps_data = [
            {
                'id': app.id,
                'name': app.name,
                'client_id': app.client_id[:10] + '...',
                'created': app.date_added.isoformat() if hasattr(app, 'date_added') else 'unknown',
            }
            for app in google_apps
        ]
        response_data = {
            'count': google_apps.count(),
            'google_apps': apps_data,
            'message': 'To fix, make a POST request to this endpoint to keep only the latest app',
        }
        serializer = self.serializer_class(response_data)
        return Response(serializer.data)

    @extend_schema(
        summary="Fix social authentication apps",
        description="Diagnostic endpoint to fix MultipleObjectsReturned error with Google OAuth. POST: Keep only the most recent app and delete duplicates",
        responses={
            200: OpenApiResponse(
                response=SocialAppDiagnosticResponseSerializer,
                description="Social apps diagnostic information or fix completed",
            ),
            403: OpenApiResponse(description="Forbidden - Staff access required"),
        }
    )
    def post(self, request):
        if not request.user.is_staff:
            return Response({'error': 'Staff access required'}, status=403)
        google_apps = SocialApp.objects.filter(provider='google')
        count = google_apps.count()
        if count <= 1:
            response_data = {
                'count': count,
                'google_apps': [
                    {
                        'id': app.id,
                        'name': app.name,
                        'client_id': app.client_id[:10] + '...',
                        'created': app.date_added.isoformat() if hasattr(app, 'date_added') else 'unknown',
                    }
                    for app in google_apps
                ],
                'message': 'No duplicates to fix',
            }
            serializer = self.serializer_class(response_data)
            return Response(serializer.data)
        latest_app = google_apps.order_by('-id').first()
        google_apps.exclude(id=latest_app.id).delete()
        response_data = {
            'count': 1,
            'google_apps': [
                {
                    'id': latest_app.id,
                    'name': latest_app.name,
                    'client_id': latest_app.client_id[:10] + '...',
                    'created': latest_app.date_added.isoformat() if hasattr(latest_app, 'date_added') else 'unknown',
                }
            ],
            'message': f'Fixed! Kept app ID {latest_app.id} and deleted {count-1} duplicate(s)',
        }
        serializer = self.serializer_class(response_data)
        return Response(serializer.data)

@extend_schema(
    summary="Authentication debug view",
    description="View for debugging authentication status",
    responses={
        200: OpenApiResponse(
            description="Authentication debug information",
        ),
    },
)
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

@extend_schema(
    summary="Get unit head bunks",
    description="Get all bunks managed by a specific unit head (via UnitStaffAssignment) with counselors and campers.",
    parameters=[
        OpenApiParameter(
            name='unithead_id',
            description='Unit head user ID',
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
        ),
        OpenApiParameter(
            name='date',
            description='Date in YYYY-MM-DD format',
            required=True,
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.PATH,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Unit head bunks data retrieved successfully",
        ),
        403: OpenApiResponse(
            description="Permission denied",
        ),
        404: OpenApiResponse(
            description="No unit found for this unit head",
        ),
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unit_head_bunks(request, unithead_id, date):
    """
    Get all bunks managed by a specific unit head (via UnitStaffAssignment) with counselors and campers.
    Endpoint: /api/unithead/<unithead_id>/<date>/
    """
    try:
        from bunk_logs.bunks.models import Unit, UnitStaffAssignment
        from .serializers import UnitHeadBunksSerializer

        user = request.user
        if not (user.is_staff or user.role == 'Admin' or (user.role == 'Unit Head' and str(user.id) == str(unithead_id))):
            return Response({'error': 'You do not have permission to access this data.'}, status=403)

        # Parse the date
        try:
            query_date = datetime.strptime(date, "%Y-%m-%d").date()
        except Exception:
            return Response({'error': 'Invalid date format.'}, status=400)

        assignments = UnitStaffAssignment.objects.filter(
            staff_member_id=unithead_id,
            role='unit_head',
            start_date__lte=query_date,
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=query_date))

        units = Unit.objects.filter(staff_assignments__in=assignments).distinct()
        if not units.exists():
            return Response({'error': 'No unit found for this unit head.'}, status=404)

        context = {'date': date}
        data = [UnitHeadBunksSerializer(unit, context=context).data for unit in units]
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@extend_schema(
    summary="Get camper care bunks",
    description="Get all bunks managed by a specific camper care team member with filtering options.",
    parameters=[
        OpenApiParameter(
            name='camper_care_id',
            description='ID of the camper care team member',
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
        ),
        OpenApiParameter(
            name='date',
            description='Date in YYYY-MM-DD format',
            required=True,
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.PATH,
        ),
        OpenApiParameter(
            name='bunk_id',
            description='Filter by specific bunk ID',
            required=False,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='unit_head_help',
            description='Filter by unit head help requested (true/false)',
            required=False,
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='camper_care_help',
            description='Filter by camper care help requested (true/false)',
            required=False,
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='social_score_min',
            description='Minimum social score (1-5)',
            required=False,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='social_score_max',
            description='Maximum social score (1-5)',
            required=False,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='behavior_score_min',
            description='Minimum behavior score (1-5)',
            required=False,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='behavior_score_max',
            description='Maximum behavior score (1-5)',
            required=False,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='participation_score_min',
            description='Minimum participation score (1-5)',
            required=False,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='participation_score_max',
            description='Maximum participation score (1-5)',
            required=False,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
        ),
    ],
    responses={
        200: OpenApiResponse(description="Camper care bunks data retrieved successfully"),
        403: OpenApiResponse(description="Permission denied"),
        404: OpenApiResponse(description="No unit found for this camper care team member"),
        500: OpenApiResponse(description="Server error"),
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_camper_care_bunks(request, camper_care_id, date):
    """
    Get all bunks managed by a specific camper care team member (via UnitStaffAssignment) with counselors and campers.
    Endpoint: /api/campercare/<camper_care_id>/<date>/
    
    Supports filtering by:
    - bunk_id: Filter by specific bunk
    - unit_head_help: Filter by unit head help requested
    - camper_care_help: Filter by camper care help requested
    - social_score_min/max: Filter by social score range
    - behavior_score_min/max: Filter by behavior score range
    - participation_score_min/max: Filter by participation score range
    """
    try:
        from bunk_logs.bunks.models import Unit, UnitStaffAssignment
        from .serializers import CamperCareBunksSerializer

        user = request.user
        if not (user.is_staff or user.role == 'Admin' or (user.role == 'Camper Care' and str(user.id) == str(camper_care_id))):
            return Response({'error': 'You do not have permission to access this data.'}, status=403)

        # Parse the date
        try:
            query_date = datetime.strptime(date, "%Y-%m-%d").date()
        except Exception:
            return Response({'error': 'Invalid date format.'}, status=400)

        # Get filter parameters
        filters = {
            'bunk_id': request.query_params.get('bunk_id'),
            'unit_head_help': request.query_params.get('unit_head_help'),
            'camper_care_help': request.query_params.get('camper_care_help'),
            'social_score_min': request.query_params.get('social_score_min'),
            'social_score_max': request.query_params.get('social_score_max'),
            'behavior_score_min': request.query_params.get('behavior_score_min'),
            'behavior_score_max': request.query_params.get('behavior_score_max'),
            'participation_score_min': request.query_params.get('participation_score_min'),
            'participation_score_max': request.query_params.get('participation_score_max'),
        }

        assignments = UnitStaffAssignment.objects.filter(
            staff_member_id=camper_care_id,
            role='camper_care',
            start_date__lte=query_date,
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=query_date))

        units = Unit.objects.filter(staff_assignments__in=assignments).distinct()
        if not units.exists():
            # Fallback for legacy data - this should be removed eventually
            return Response({'error': 'No unit found for this camper care team member.'}, status=404)

        # Pass filters through context
        context = {'date': date, 'filters': filters}
        data = [CamperCareBunksSerializer(unit, context=context).data for unit in units]
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@extend_schema(
    summary="Get all bunk logs by date",
    description="API view to get all bunk logs for a specific date with comprehensive camper information.",
    parameters=[
        OpenApiParameter(
            name='date',
            description='Date in YYYY-MM-DD format',
            required=True,
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.PATH,
        ),
    ],
    responses={
        200: OpenApiResponse(description="Bunk logs data retrieved successfully"),
        403: OpenApiResponse(description="Permission denied"),
        400: OpenApiResponse(description="Invalid date format"),
    },
)
class BunkLogsAllByDateViewSet(APIView):
    """
    API view to get all bunk logs for a specific date.
    Returns comprehensive information including camper details, bunk assignment, 
    scores, reporting counselor, and support requests.
    """
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, date):
        user = request.user
        
        # Parse and validate date
        try:
            query_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD format."}, status=400)
        
        # Get queryset based on user permissions
        if user.is_staff or user.role == 'Admin':
            queryset = BunkLog.objects.filter(date=query_date)
        elif user.role == 'Unit Head':
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
                start_date__lte=query_date,
            ).filter(Q(end_date__isnull=True) | Q(end_date__gte=query_date))
            
            queryset = BunkLog.objects.filter(
                date=query_date,
                bunk_assignment__bunk__unit_id__in=unit_assignments
            )
        elif user.role == 'Camper Care':
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='camper_care',
                start_date__lte=query_date,
            ).filter(Q(end_date__isnull=True) | Q(end_date__gte=query_date))
            
            queryset = BunkLog.objects.filter(
                date=query_date,
                bunk_assignment__bunk__unit_id__in=unit_assignments
            )
        elif user.role == 'Counselor':
            queryset = BunkLog.objects.filter(
                date=query_date,
                bunk_assignment__bunk__in=user.assigned_bunks.all()
            )
        else:
            return Response({"error": "You are not authorized to access bunk logs data"}, status=403)
        
        # Optimize queries
        queryset = queryset.select_related(
            'bunk_assignment__camper',
            'bunk_assignment__bunk',
            'bunk_assignment__bunk__unit',
            'counselor'
        ).order_by(
            'bunk_assignment__bunk__unit__name',
            'bunk_assignment__bunk__cabin__name',
            'bunk_assignment__camper__last_name'
        )
        
        # Build response data
        logs_data = []
        for log in queryset:
            log_data = {
                "id": str(log.id),
                "date": log.date.strftime("%Y-%m-%d"),
                "camper_first_name": log.bunk_assignment.camper.first_name,
                "camper_last_name": log.bunk_assignment.camper.last_name,
                "camper_id": str(log.bunk_assignment.camper.id),
                "bunk_assignment_id": str(log.bunk_assignment.id),
                "bunk_name": log.bunk_assignment.bunk.name,
                "bunk_cabin_name": log.bunk_assignment.bunk.cabin.name if log.bunk_assignment.bunk.cabin else None,
                "bunk_session": log.bunk_assignment.bunk.session.name if log.bunk_assignment.bunk.session else None,
                "unit_name": log.bunk_assignment.bunk.unit.name if log.bunk_assignment.bunk.unit else None,
                "social_score": log.social_score,
                "participation_score": log.participation_score,
                "behavioral_score": log.behavior_score,
                "description": log.description,
                "not_on_camp": log.not_on_camp,
                "reporting_counselor_first_name": log.counselor.first_name if log.counselor else None,
                "reporting_counselor_last_name": log.counselor.last_name if log.counselor else None,
                "reporting_counselor_email": log.counselor.email if log.counselor else None,
                "unit_head_help_requested": log.request_unit_head_help,
                "camper_care_help_requested": log.request_camper_care_help,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "updated_at": log.updated_at.isoformat() if log.updated_at else None,
            }
            logs_data.append(log_data)
        
        return Response({
            "date": date,
            "total_logs": len(logs_data),
            "logs": logs_data
        })

@extend_schema(
    summary="Get all bunk logs by date",
    description="API view to get all bunk logs for a specific date. Returns comprehensive information including camper details, bunk assignment, scores, reporting counselor, and support requests.",
    parameters=[
        OpenApiParameter(
            name='date',
            description='Date in YYYY-MM-DD format',
            required=True,
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.PATH,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Bunk logs data retrieved successfully",
        ),
        403: OpenApiResponse(
            description="Permission denied",
        ),
        400: OpenApiResponse(
            description="Invalid date format",
        ),
    },
)
class BunkLogsAllByDateViewSet(APIView):
    """
    API view to get all bunk logs for a specific date.
    The endpoint will be '/api/v1/bunklogs/all/<str:date>/''
    where 'date' is the date in YYYY-MM-DD format.
    
    Response includes:
    - Camper first and last names
    - Bunk assignment information  
    - Date
    - Social score
    - Participation score
    - Behavioral score
    - Description
    - Reporting counselor information
    - Unit head help requested
    - Camper care help requested
    - Not on camp status
    """
    renderer_classes = [JSONRenderer]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, date):
        user = request.user
        
        # Parse and validate date
        try:
            query_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD format."}, status=400)
        
        # Get queryset based on user permissions
        if user.is_staff or user.role == 'Admin':
            # Admin/staff can see all bunk logs
            queryset = BunkLog.objects.filter(date=query_date)
        elif user.role == 'Unit Head':
            # Unit heads can see logs for bunks in their units
            from django.utils import timezone
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
                start_date__lte=query_date,
            ).filter(Q(end_date__isnull=True) | Q(end_date__gte=query_date))
            
            queryset = BunkLog.objects.filter(
                date=query_date,
                bunk_assignment__bunk__unit_id__in=unit_assignments
            )
        elif user.role == 'Camper Care':
            # Camper care can see logs for bunks in their assigned units
            from django.utils import timezone
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='camper_care',
                start_date__lte=query_date,
            ).filter(Q(end_date__isnull=True) | Q(end_date__gte=query_date))
            
            queryset = BunkLog.objects.filter(
                date=query_date,
                bunk_assignment__bunk__unit_id__in=unit_assignments
            )
        elif user.role == 'Counselor':
            # Counselors can see logs for their bunks only
            queryset = BunkLog.objects.filter(
                date=query_date,
                bunk_assignment__bunk__in=user.assigned_bunks.all()
            )
        else:
            # Default: no access
            logger.warning(
                f"403 Forbidden: User {user.id} ({user.role}) attempted to access bunk logs for {query_date}, but lacks permissions."
            )
            return Response({"error": "You are not authorized to access bunk logs data"}, status=403)
        
        # Select related fields to optimize database queries
        queryset = queryset.select_related(
            'bunk_assignment__camper',
            'bunk_assignment__bunk',
            'bunk_assignment__bunk__unit',
            'counselor'
        ).order_by(
            'bunk_assignment__bunk__unit__name',
            'bunk_assignment__bunk__cabin__name',
            'bunk_assignment__camper__last_name',
            'bunk_assignment__camper__first_name'
        )
        
        # Build response data
        logs_data = []
        for log in queryset:
            log_data = {
                "id": str(log.id),
                "date": log.date.strftime("%Y-%m-%d"),
                
                # Camper information
                "camper_first_name": log.bunk_assignment.camper.first_name,
                "camper_last_name": log.bunk_assignment.camper.last_name,
                "camper_id": str(log.bunk_assignment.camper.id),
                
                # Bunk assignment information
                "bunk_assignment_id": str(log.bunk_assignment.id),
                "bunk_id": str(log.bunk_assignment.bunk.id),
                "bunk_name": log.bunk_assignment.bunk.name,
                "bunk_cabin_name": log.bunk_assignment.bunk.cabin.name if log.bunk_assignment.bunk.cabin else None,
                "bunk_session": log.bunk_assignment.bunk.session.name if log.bunk_assignment.bunk.session else None,
                "unit_name": log.bunk_assignment.bunk.unit.name if log.bunk_assignment.bunk.unit else None,
                "social_score": log.social_score,
                "participation_score": log.participation_score,
                "behavioral_score": log.behavior_score,
                "description": log.description,
                "not_on_camp": log.not_on_camp,
                "reporting_counselor_first_name": log.counselor.first_name if log.counselor else None,
                "reporting_counselor_last_name": log.counselor.last_name if log.counselor else None,
                "reporting_counselor_email": log.counselor.email if log.counselor else None,
                "unit_head_help_requested": log.request_unit_head_help,
                "camper_care_help_requested": log.request_camper_care_help,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "updated_at": log.updated_at.isoformat() if log.updated_at else None,
            }
            logs_data.append(log_data)
        
        return Response({
            "date": date,
            "total_logs": len(logs_data),
            "logs": logs_data
        })

class UnitStaffAssignmentCSVImportView(APIView):
    """
    API endpoint to import UnitStaffAssignment objects from a CSV file.
    Only staff/admin users can use this endpoint.
    CSV columns: unit_id, staff_member_id, role, start_date, end_date, is_primary
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        if not request.user.is_staff:
            return Response({'error': 'Only staff can import assignments.'}, status=403)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file uploaded.'}, status=400)
        # Parse CSV
        decoded_file = TextIOWrapper(file_obj, encoding='utf-8')
        reader = csv.DictReader(decoded_file)
        created, updated, errors = 0, 0, []
        for i, row in enumerate(reader, start=2):  # start=2 for header row
            try:
                unit_id = row.get('unit_id')
                staff_member_id = row.get('staff_member_id')
                role = row.get('role')
                start_date = row.get('start_date')
                end_date = row.get('end_date') or None
                is_primary = row.get('is_primary', 'False').lower() in ['true', '1', 'yes']
                if not (unit_id and staff_member_id and role and start_date):
                    errors.append(f"Row {i}: Missing required fields.")
                    continue
                unit = Unit.objects.get(id=unit_id)
                staff_member = User.objects.get(id=staff_member_id)
                assignment, created_flag = UnitStaffAssignment.objects.update_or_create(
                    unit=unit,
                    staff_member=staff_member,
                    role=role,
                    defaults={
                        'start_date': start_date,
                        'end_date': end_date,
                        'is_primary': is_primary
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")
        return Response({
            'created': created,
            'updated': updated,
            'errors': errors
        })

from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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

#from .permissions import BunkAccessPermission
#from .permissions import IsCounselorForBunk
#from .permissions import DebugPermission

User = get_user_model()


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
        from bunk_logs.bunks.models import Bunk
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
        serializer = ApiUserSerializer(user)
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
            # Unit heads can access bunks in their units
            if user.role == 'Unit Head':
                if not Bunk.objects.filter(id=bunk_id, unit__unit_head=user).exists():
                    return Response({"error": "You are not authorized to access this bunk's data"}, status=403)
            # Camper care can access bunks in their assigned units
            elif user.role == 'Camper Care':
                if not Bunk.objects.filter(id=bunk_id, unit__camper_care=user).exists():
                    return Response({"error": "You are not authorized to access this bunk's data"}, status=403)
            # Counselors can only access their assigned bunks
            elif user.role == 'Counselor':
                if not Bunk.objects.filter(id=bunk_id, counselors__id=user.id).exists():
                    return Response({"error": "You are not authorized to access this bunk's data"}, status=403)
            else:
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
    - GET /api/unit-staff-assignments/{id}/ - Retrieve specific assignment
    - PUT /api/unit-staff-assignments/{id}/ - Update assignment
    - DELETE /api/unit-staff-assignments/{id}/ - Delete assignment
    """
    queryset = UnitStaffAssignment.objects.all().select_related('unit', 'staff_member')
    serializer_class = UnitStaffAssignmentSerializer
    permission_classes = [IsAuthenticated]

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
            # Check both legacy unit_head field and new staff assignments
            unit_ids = []
            # Legacy approach
            unit_ids.extend(user.managed_units.values_list('id', flat=True))
            # New approach - get units where user is assigned as unit_head
            from django.utils import timezone
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            return BunkLog.objects.filter(
                bunk_assignment__bunk__unit_id__in=set(unit_ids)
            )
        # Camper care can see logs for bunks in their assigned units
        if user.role == 'Camper Care':
            # Check both legacy camper_care field and new staff assignments
            unit_ids = []
            # Legacy approach
            unit_ids.extend(user.camper_care_units.values_list('id', flat=True))
            # New approach - get units where user is assigned as camper_care
            from django.utils import timezone
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='camper_care',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            return BunkLog.objects.filter(
                bunk_assignment__bunk__unit_id__in=set(unit_ids)
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
            # Check both legacy unit_head field and new staff assignments
            has_access = False
            # Legacy approach
            if user.managed_units.filter(bunks=instance.bunk_assignment.bunk).exists():
                has_access = True
            # New approach - check staff assignments
            from django.utils import timezone
            if UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
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
        
        # Camper care can update logs for bunks in their assigned units
        if user.role == 'Camper Care':
            # Check both legacy camper_care field and new staff assignments
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
            # Check if user is a counselor for this bunk
            if not user.assigned_bunks.filter(id=instance.bunk_assignment.bunk.id).exists():
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
            # Legacy approach
            unit_ids.extend(user.managed_units.values_list('id', flat=True))
            # New approach - get units where user is assigned as unit_head
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='unit_head',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            # Get counselors assigned to bunks in these units
            counselor_ids = Bunk.objects.filter(
                unit_id__in=set(unit_ids)
            ).values_list('counselors', flat=True).distinct()
            
            return CounselorLog.objects.filter(counselor_id__in=counselor_ids)
        # Camper care can see logs for counselors in their assigned units
        if user.role == 'Camper Care':
            # Get units where user is assigned as camper_care
            from django.utils import timezone
            unit_ids = []
            # Legacy approach
            unit_ids.extend(user.camper_care_units.values_list('id', flat=True))
            # New approach - get units where user is assigned as camper_care
            unit_assignments = UnitStaffAssignment.objects.filter(
                staff_member=user,
                role='camper_care',
                start_date__lte=timezone.now().date(),
                end_date__isnull=True
            ).values_list('unit_id', flat=True)
            unit_ids.extend(unit_assignments)
            
            # Get counselors assigned to bunks in these units
            counselor_ids = Bunk.objects.filter(
                unit_id__in=set(unit_ids)
            ).values_list('counselors', flat=True).distinct()
            
            return CounselorLog.objects.filter(counselor_id__in=counselor_ids)
        # Counselors can only see their own logs
        if user.role == 'Counselor':
            return CounselorLog.objects.filter(counselor=user)
        # Default: see nothing
        return CounselorLog.objects.none()
    
    def perform_create(self, serializer):
        # Verify the user is a counselor
        if self.request.user.role != 'Counselor':
            raise PermissionDenied("Only counselors can create counselor logs.")
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
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin/staff can see all
        if user.is_staff or user.role == 'Admin':
            return CounselorLog.objects.all()
            
        # Unit heads and camper care can see logs for counselors in their units
        if user.role in ['Unit Head', 'Camper Care']:
            from django.utils import timezone
            unit_ids = []
            
            # For Unit Head role
            if user.role == 'Unit Head':
                # Get units where user is assigned as unit_head
                unit_assignments = UnitStaffAssignment.objects.filter(
                    staff_member=user,
                    role='unit_head',
                    start_date__lte=timezone.now().date(),
                    end_date__isnull=True
                ).values_list('unit_id', flat=True)
                unit_ids.extend(unit_assignments)
                # Also include legacy unit_head field
                unit_ids.extend(user.managed_units.values_list('id', flat=True))
                
            # For Camper Care role  
            if user.role == 'Camper Care':
                # Get units where user is assigned as camper_care
                unit_assignments = UnitStaffAssignment.objects.filter(
                    staff_member=user,
                    role='camper_care',
                    start_date__lte=timezone.now().date(),
                    end_date__isnull=True
                ).values_list('unit_id', flat=True)
                unit_ids.extend(unit_assignments)
                # Also include legacy camper_care field
                unit_ids.extend(user.camper_care_units.values_list('id', flat=True))
            
            # Get counselors assigned to bunks in these units
            counselor_ids = User.objects.filter(
                role='Counselor',
                assigned_bunks__unit_id__in=set(unit_ids)
            ).values_list('id', flat=True)
            
            return CounselorLog.objects.filter(counselor_id__in=counselor_ids)
            
        # Counselors can only see their own logs
        if user.role == 'Counselor':
            return CounselorLog.objects.filter(counselor=user)
            
        # Default: see nothing
        return CounselorLog.objects.none()
    
    def perform_create(self, serializer):
        # Verify the user is a counselor
        if self.request.user.role != 'Counselor':
            raise PermissionDenied("Only counselors can create counselor logs.")
        
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
                raise PermissionDenied("You can only edit counselor logs on the day they were created.")
            
            # Don't allow changing the counselor field during update
            if 'counselor' in serializer.validated_data:
                serializer.validated_data['counselor'] = instance.counselor
            
            serializer.save()
            return
        
        # Default: deny access
        raise PermissionDenied("You are not authorized to update this counselor log.")

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
            legacy_unit = Unit.objects.filter(unit_head_id=unithead_id).first()
            if legacy_unit:
                units = [legacy_unit]
            else:
                return Response({'error': 'No unit found for this unit head.'}, status=404)

        context = {'date': date}
        data = [UnitHeadBunksSerializer(unit, context=context).data for unit in units]
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@extend_schema(
    summary="Get camper care bunks",
    description="Get all bunks managed by a specific camper care team member (via UnitStaffAssignment) with counselors and campers.",
    parameters=[
        OpenApiParameter(
            name='camper_care_id',
            description='Camper care user ID',
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
            description="Camper care bunks data retrieved successfully",
        ),
        403: OpenApiResponse(
            description="Permission denied",
        ),
        404: OpenApiResponse(
            description="No unit found for this camper care team member",
        ),
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_camper_care_bunks(request, camper_care_id, date):
    """
    Get all bunks managed by a specific camper care team member (via UnitStaffAssignment) with counselors and campers.
    Endpoint: /api/campercare/<camper_care_id>/<date>/
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

        assignments = UnitStaffAssignment.objects.filter(
            staff_member_id=camper_care_id,
            role='camper_care',
            start_date__lte=query_date,
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=query_date))

        units = Unit.objects.filter(staff_assignments__in=assignments).distinct()
        if not units.exists():
            legacy_unit = Unit.objects.filter(camper_care_id=camper_care_id).first()
            if legacy_unit:
                units = [legacy_unit]
            else:
                return Response({'error': 'No unit found for this camper care team member.'}, status=404)

        context = {'date': date}
        data = [CamperCareBunksSerializer(unit, context=context).data for unit in units]
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

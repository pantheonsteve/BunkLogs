from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    def validate(self, attrs):
        # Strip whitespace from email
        if self.username_field in attrs:
            attrs[self.username_field] = attrs[self.username_field].strip()
            
        # Add custom claims to the token
        data = super().validate(attrs)
        refresh = self.get_token(self.user)
        
        # Add extra claims to the token
        refresh['email'] = self.user.email
        refresh['user_id'] = str(self.user.id)
        if hasattr(self.user, 'role'):
            refresh['role'] = getattr(self.user, 'role', 'User')
            
        # Return the token data
        data['access'] = str(refresh.access_token)
        data['refresh'] = str(refresh)
        
        # Add basic user details
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'first_name': getattr(self.user, 'first_name', ''),
            'last_name': getattr(self.user, 'last_name', ''),
            'role': getattr(self.user, 'role', 'User'),
        }
        
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@ensure_csrf_cookie
def get_csrf_token(request):
    """
    Return CSRF token for JavaScript clients
    """
    token = get_token(request)
    return JsonResponse({'detail': 'CSRF cookie set', 'csrfToken': token})

def get_auth_status(request):
    """
    Return authentication status and user info
    """
    if request.user.is_authenticated:
        response_data = {
            'isAuthenticated': True,
            'user': {
                'id': request.user.id,
                'email': request.user.email,
                'firstName': request.user.first_name,
                'lastName': request.user.last_name,
                'name': request.user.name,
                'role': request.user.role,
                'profileComplete': request.user.profile_complete,
            }
        }
        
        # Add bunk information for counselors
        if request.user.role == 'Counselor':
            # Get assigned bunks for the counselor
            bunks = list(request.user.assigned_bunks.filter(is_active=True).values(
                'id', 'cabin__name', 'session__name'
            ))
            
            # Format the bunks for the response
            formatted_bunks = []
            for bunk in bunks:
                formatted_bunks.append({
                    'id': bunk['id'],
                    'name': f"{bunk['cabin__name']} - {bunk['session__name']}"
                })
                
            response_data['user']['bunks'] = formatted_bunks
            
        # For Unit Heads, include their managed units
        elif request.user.role == 'Unit Head':
            units = list(request.user.managed_units.all().values('id', 'name'))
            response_data['user']['units'] = units
            
        return JsonResponse(response_data)
    else:
        return JsonResponse({
            'isAuthenticated': False,
        })
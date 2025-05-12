from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import RedirectView
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView, VerifyEmailView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import UserSerializer
from allauth.socialaccount.models import SocialApp
from rest_framework.renderers import JSONRenderer
import logging
logger = logging.getLogger(__name__)
from django.http import HttpResponseRedirect

class UserRedirectView(LoginRequiredMixin, RedirectView):
    """
    This view is needed by the dj-rest-auth-library in order to work the google login. It's a bug.
    """
    permanent = False

    def get_redirect_url(self):
        return "redirect-url"


class CustomEmailVerificationSentView(APIView):
    """
    Custom view for the email verification sent page.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        return Response({
            'detail': 'Verification email sent.',
            'redirectUrl': settings.FRONTEND_URL + '/verify-email-sent'
        })

# Google OAuth2 login view
class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = f"{settings.FRONTEND_URL}/auth/callback"
    client_class = OAuth2Client

    def get_response(self):
        # Add some logging
        logger.info("GoogleLoginView.get_response() called")
        return super().get_response()

# Google callback view
class GoogleCallbackView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    
    def get(self, request, *args, **kwargs):
        logger.info("GoogleCallbackView.get() called")
        logger.info(f"Query params: {request.GET}")
        
        # Get tokens from the OAuth process
        if request.user.is_authenticated:
            logger.info(f"User authenticated: {request.user.email}")
            
            # Generate tokens
            refresh = RefreshToken.for_user(request.user)
            
            # Build redirect URL
            redirect_url = (
                f"{settings.FRONTEND_URL}/auth/callback"
                f"#access_token={str(refresh.access_token)}"
                f"&refresh_token={str(refresh)}"
            )
            
            logger.info(f"Redirecting to: {redirect_url}")
            return HttpResponseRedirect(redirect_url)
        else:
            logger.warning("User not authenticated in callback view")
            return HttpResponseRedirect(f"{settings.FRONTEND_URL}/signin?error=auth_failed")

@ensure_csrf_cookie
@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """Return CSRF token for JavaScript clients"""
    token = get_token(request)
    return JsonResponse({'detail': 'CSRF cookie set', 'csrfToken': token})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_auth_status(request):
    """Return authentication status and user info"""
    renderer_classes = [JSONRenderer]
    serializer = UserSerializer(request.user)
    return Response({
        'isAuthenticated': True,
        'user': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout view that clears auth cookies"""
    response = Response({"detail": "Successfully logged out."})
    response.delete_cookie(settings.REST_AUTH['JWT_AUTH_COOKIE'])
    response.delete_cookie(settings.REST_AUTH['JWT_AUTH_REFRESH_COOKIE'])
    return response

@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
@csrf_exempt
def token_refresh(request):
    """Custom token refresh that works with frontend sending token in request body"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Log request details for debugging
    logger.info(f"Cookies in refresh request: {request.COOKIES.keys()}")
    logger.info(f"Headers: {list(request.headers.keys())}")
    logger.info(f"Data keys: {list(request.data.keys()) if hasattr(request.data, 'keys') else 'No data'}")
    
    # Get refresh token from request body first
    refresh_token = None
    
    # Check request body for refresh token
    if hasattr(request.data, 'get'):
        refresh_token = request.data.get('refresh_token') or request.data.get('refresh')
        if refresh_token:
            logger.info("Found refresh token in request body")
    
    # If not in body, check cookies as fallback
    if not refresh_token:
        refresh_token = request.COOKIES.get(settings.REST_AUTH['JWT_AUTH_REFRESH_COOKIE'])
        if refresh_token:
            logger.info(f"Found refresh token in cookies")
    
    # Also try to get from Authorization header as last resort
    if not refresh_token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            refresh_token = auth_header.split(' ')[1]
            logger.info("Found refresh token in Authorization header")
    
    if not refresh_token:
        # Return a special response to signal the frontend to stop trying
        logger.warning("Refresh token not found anywhere - signaling frontend to stop retries")
        return Response({
            "detail": "No valid refresh token found.",
            "stop_retrying": True
        }, status=401)
    
    try:
        # Create data for the token refresh
        data = {'refresh': refresh_token}
        
        # Use the TokenRefreshView directly 
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        
        serializer = TokenRefreshSerializer(data=data)
        
        try:
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data, status=200)
        except TokenError as e:
            logger.warning(f"Token refresh error: {str(e)}")
            return Response({
                "detail": str(e),
                "stop_retrying": True  # Signal frontend to stop retrying
            }, status=401)
            
    except Exception as e:
        logger.error(f"Error during token refresh: {str(e)}")
        return Response({
            "detail": "Server error during token refresh.",
            "stop_retrying": True  # Signal frontend to stop retrying
        }, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def token_authenticate(request):
    """Accept tokens in request body and return user info"""
    import logging
    logger = logging.getLogger(__name__)
    
    access_token = request.data.get('access_token')
    
    if not access_token:
        return Response({"detail": "No access token provided."}, status=401)
    
    try:
        # Validate the token
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get user from token
        token_obj = AccessToken(access_token)
        user_id = token_obj['user_id']
        user = User.objects.get(id=user_id)
        
        # Return user info
        serializer = UserSerializer(user)
        return Response(
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true'
            },
            data={
            'isAuthenticated': True,
            'user': serializer.data
            }
        )
    except TokenError as e:
        logger.warning(f"Token validation error: {str(e)}")
        return Response({"detail": str(e)}, status=401)
    except User.DoesNotExist:
        return Response({"detail": "User not found."}, status=401)
    except Exception as e:
        logger.error(f"Error authenticating with token: {str(e)}")
        return Response({"detail": "Authentication error."}, status=500)
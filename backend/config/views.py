import json
import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.http import HttpResponseRedirect, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.views.generic import RedirectView, TemplateView

from allauth.socialaccount.models import SocialApp, SocialAccount, SocialLogin
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.helpers import render_authentication_error, complete_social_login
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView, OAuth2LoginView

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from urllib.parse import urlencode

User = get_user_model()

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connections
from django.core.cache import cache

@csrf_exempt
def test_cors(request):
    return JsonResponse({"message": "CORS is working!"})


@csrf_exempt
def health_check(request):
    """
    Health check endpoint for Render.com and other monitoring services.
    Returns 200 if the service is healthy, 503 if there are issues.
    """
    health_status = {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "checks": {}
    }
    
    is_healthy = True
    
    # Check database connectivity
    try:
        db_conn = connections['default']
        db_conn.cursor()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        is_healthy = False
    
    # Check cache connectivity (if configured)
    try:
        cache.set('health_check', 'ok', 30)
        if cache.get('health_check') == 'ok':
            health_status["checks"]["cache"] = "ok"
        else:
            health_status["checks"]["cache"] = "warning: cache not working"
    except Exception as e:
        health_status["checks"]["cache"] = f"error: {str(e)}"
        # Don't mark as unhealthy for cache issues
    
    if not is_healthy:
        health_status["status"] = "unhealthy"
        return JsonResponse(health_status, status=503)
    
    return JsonResponse(health_status, status=200)


class CustomEmailVerificationSentView(TemplateView):
    template_name = "account/verification_sent.html"


class UserRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("user_detail")


@require_GET
def get_csrf_token(request):
    token = get_token(request)
    return JsonResponse({'csrfToken': token})


@require_GET
def get_auth_status(request):
    if request.user.is_authenticated:
        return JsonResponse({
            "isAuthenticated": True,
            "user": {
                "id": request.user.id,
                "email": request.user.email,
                "name": request.user.get_full_name(),
            }
        })
    return JsonResponse({"isAuthenticated": False})


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"success": True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def token_refresh(request):
    refresh = RefreshToken.for_user(request.user)
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def token_authenticate(request):
    """Authenticate using JWT tokens"""
    # This endpoint would be used to exchange JWT for session authentication
    # Useful when transitioning from token to session auth
    return Response({"message": "Authentication successful"})

@extend_schema(
    summary="Google OAuth Login",
    description="Initiate Google OAuth flow",
    responses={
        200: OpenApiResponse(
            description="Authorization URL generated",
            examples={
                "application/json": {
                    "authorization_url": "https://accounts.google.com/o/oauth2/auth?..."
                }
            }
        ),
        500: OpenApiResponse(description="Server error or Google authentication not configured"),
    },
)
@csrf_exempt
class GoogleLoginView(APIView):
    """
    View for initiating Google OAuth login
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Handle GET request to initiate OAuth flow
        This returns the URL where the user should be redirected for Google login
        """
        try:
            # Get the Google SocialApp configuration
            try:
                app = SocialApp.objects.get(provider="google")
            except SocialApp.DoesNotExist:
                return Response({'error': 'Google authentication is not configured'}, status=500)
            
            # Callback URL where Google will redirect after authentication
            callback_url = request.build_absolute_uri(reverse('google_callback'))
            
            # Create OAuth adapter and client
            adapter = GoogleOAuth2Adapter(request)
            client = OAuth2Client(
                request,
                app.client_id,
                app.secret,
                adapter.access_token_url,
                callback_url
            )
            
            # Get the authorization URL
            auth_url, state = client.get_redirect_url()
            
            # Store the state in the session for later verification
            request.session['socialaccount_state'] = state
            
            return Response({
                'authorization_url': auth_url
            })
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"Error generating Google auth URL: {e}")
            print(error_traceback)
            return Response({
                'error': str(e),
                'detail': error_traceback if settings.DEBUG else None
            }, status=500)
@extend_schema(
    summary="Google OAuth Callback",
    description="Handle callback from Google OAuth",
    parameters=[
        OpenApiParameter(
            name='code',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Authorization code from Google',
        ),
        OpenApiParameter(
            name='error',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Error message from Google (if any)',
        ),
    ],
    responses={
        302: OpenApiResponse(description="Redirect to frontend with tokens"),
        400: OpenApiResponse(description="Bad request or authentication error"),
    },
)
class GoogleCallbackView(APIView):
    """
    Handles the callback from Google OAuth
    This would be used with the redirect flow (not popup)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # This is the OAuth2 callback that Google redirects to
        code = request.GET.get('code')
        error = request.GET.get('error')
        
        if error:
            return render_authentication_error(
                request,
                GoogleOAuth2Adapter.provider_id,
                error=error
            )
        
        try:
            adapter = GoogleOAuth2Adapter(request)
            app = SocialApp.objects.get(provider="google")
            callback_url = request.build_absolute_uri(reverse('google_callback'))
            
            client = OAuth2Client(
                request,
                app.client_id,
                app.secret,
                adapter.access_token_url,
                callback_url
            )
            
            # Get the access token
            token = client.get_access_token(code)
            
            # Complete the login
            login_data = adapter.parse_token(token)
            token_data = {"access_token": token["access_token"]}
            
            # Get user info
            userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            headers = {'Authorization': f'Bearer {token["access_token"]}'}
            userinfo_response = requests.get(userinfo_url, headers=headers)
            userinfo = userinfo_response.json()
            login_data.update(userinfo)
            
            social_login = adapter.complete_login(request, login_data)
            social_login.token = token_data
            
            # Complete the login process
            login_completion = complete_social_login(request, social_login)
            
            # Redirect to the frontend with tokens
            user = social_login.account.user
            refresh = RefreshToken.for_user(user)
            
            # In a real scenario, you might want to create a JWT and redirect to frontend with it
            redirect_url = f"{settings.FRONTEND_URL}?token={refresh.access_token}"
            return redirect(redirect_url)
            
        except Exception as e:
            return render_authentication_error(
                request,
                GoogleOAuth2Adapter.provider_id,
                exception=e
            )


@extend_schema(
    summary="Validate Google ID Token",
    description="Validate Google ID token from frontend",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'credential': {
                    'type': 'string',
                    'description': 'Google ID token'
                }
            },
            'required': ['credential']
        }
    },
    responses={
        200: OpenApiResponse(
            description="Token validated and user authenticated",
            examples={
                "application/json": {
                    "user": {"id": 1, "email": "user@example.com", "name": "User Name"},
                    "tokens": {"refresh": "...", "access": "..."}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid token or validation error"),
        500: OpenApiResponse(description="Google authentication not configured"),
    },
)
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def validate_google_token(request):
    """
    Validate Google ID token from the frontend
    This is used with the GoogleLogin component from @react-oauth/google
    """

     # Print request information for debugging
    print(f"Request method: {request.method}")
    print(f"Request headers: {request.headers}")
    print(f"Request data: {request.data}")

    credential = request.data.get('credential')
    
    if not credential:
        return Response({'error': 'ID token is required'}, status=400)
    
    try:
        # Get the Google SocialApp configuration
        try:
            social_app = SocialApp.objects.get(provider="google")
        except SocialApp.DoesNotExist:
            return Response({'error': 'Google authentication is not configured'}, status=500)
        
        # Verify the token with Google
        response = requests.get(
            f'https://oauth2.googleapis.com/tokeninfo?id_token={credential}'
        )
        
        id_info = response.json()
        
        if 'error' in id_info:
            return Response({'error': id_info['error']}, status=400)
        
        # Verify the audience
        if id_info['aud'] != social_app.client_id:
            return Response({'error': 'Invalid client ID'}, status=400)
        
        # Check if the user exists
        try:
            social_account = SocialAccount.objects.get(
                provider='google',
                uid=id_info['sub']
            )
            user = social_account.user
        except SocialAccount.DoesNotExist:
            # Create a new user
            email = id_info.get('email')
            
            # Check if a user with this email already exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create new user
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    first_name=id_info.get('given_name', ''),
                    last_name=id_info.get('family_name', ''),
                    is_active=True,
                )
                
                # Set email verification based on Google's verification
                user.emailaddress_set.create(
                    email=email,
                    verified=id_info.get('email_verified', False),
                    primary=True
                )
            
            # Create social account
            social_account = SocialAccount.objects.create(
                user=user,
                provider='google',
                uid=id_info['sub'],
                extra_data=id_info
            )
        
        # Log the user in
        login(request, user, backend='allauth.account.auth_backends.AuthenticationBackend')
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.get_full_name(),
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@extend_schema(
    summary="Google Login (OAuth Flow)",
    description="Initiate Google OAuth flow",
    responses={
        200: OpenApiResponse(
            description="Authorization URL returned",
            examples={
                "application/json": {
                    "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
                }
            }
        ),
        500: OpenApiResponse(description="Server error"),
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])
def google_login(request):
    """Initiate Google OAuth flow"""
    try:
        # Get Google provider configuration
        social_app = SocialApp.objects.get(provider="google")
        
        # Define redirect URL back to backend
        redirect_uri = request.build_absolute_uri(reverse('google_callback'))
        
        # Build Google OAuth URL
        auth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={social_app.client_id}&redirect_uri={redirect_uri}&response_type=code&scope=email%20profile"
        
        return Response({"auth_url": auth_url})
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@extend_schema(
    summary="Google OAuth Callback Handler",
    description="Handle Google OAuth callback with authorization code",
    parameters=[
        OpenApiParameter(
            name='code',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Authorization code from Google',
        ),
        OpenApiParameter(
            name='error',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Error message from Google (if any)',
        ),
    ],
    responses={
        302: OpenApiResponse(description="Redirect to frontend with tokens"),
        400: OpenApiResponse(description="Bad request or missing authorization code"),
        500: OpenApiResponse(description="Server error or Google authentication not configured"),
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])
def google_callback(request):
    """Handle Google OAuth callback"""
    error = request.GET.get('error')
    code = request.GET.get('code')
    
    if error:
        # Log the error for debugging
        print(f"Google OAuth error: {error}")
        # Redirect to frontend with error message - use environment FRONTEND_URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://clc.bunklogs.net')
        return HttpResponseRedirect(
            f"{frontend_url}/signin?auth_error={error}"
        )
    
    if not code:
        return Response({"error": "No authorization code received"}, status=400)
    
    try:
        # Get Google app config
        social_app = SocialApp.objects.get(provider="google")
        
        # Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"
        redirect_uri = request.build_absolute_uri(reverse('google_callback'))
        
        payload = {
            'code': code,
            'client_id': social_app.client_id,
            'client_secret': social_app.secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        # Get token from Google
        response = requests.post(token_url, data=payload)
        token_data = response.json()
        
        # Get user info from Google
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {'Authorization': f'Bearer {token_data["access_token"]}'}
        userinfo = requests.get(userinfo_url, headers=headers).json()
        
        # Get or create user
        try:
            social_account = SocialAccount.objects.get(provider='google', uid=userinfo['sub'])
            user = social_account.user
        except SocialAccount.DoesNotExist:
            # Find or create user by email
            email = userinfo.get('email')
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email=email,
                    first_name=userinfo.get('given_name', ''),
                    last_name=userinfo.get('family_name', ''),
                    role='Counselor'  # Default role
                )
                
                # Create social account
                SocialAccount.objects.create(
                    user=user,
                    provider='google',
                    uid=userinfo['sub'],
                    extra_data=userinfo
                )
        
        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        # Debug: Log the tokens and redirect URL
        print(f"Generated tokens - Access: {access_token[:20]}..., Refresh: {refresh_token[:20]}...")
        
        # Build redirect URL manually (don't use urlencode which might cause issues)
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://clc.bunklogs.net')
        
        # FIXED: Manual URL construction instead of urlencode
        redirect_url = f"{frontend_url}/auth/callback#access_token={access_token}&refresh_token={refresh_token}"
        
        print(f"Redirecting to: {redirect_url[:100]}...")  # Log first 100 chars
        
        return HttpResponseRedirect(redirect_url)
    except Exception as e:
        print(f"Google callback error: {str(e)}")
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        
        # Redirect to frontend with error - use environment FRONTEND_URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://clc.bunklogs.net')
        return HttpResponseRedirect(f"{frontend_url}/signin?auth_error=callback_failed")


@extend_schema(
    summary="Google Login Callback (POST)",
    description="Handle callback during redirect auth flow",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'code': {
                    'type': 'string',
                    'description': 'Authorization code from Google'
                }
            },
            'required': ['code']
        }
    },
    responses={
        200: OpenApiResponse(
            description="Login successful",
            examples={
                "application/json": {
                    "user": {"id": 1, "email": "user@example.com", "name": "User Name"},
                    "tokens": {"refresh": "...", "access": "..."}
                }
            }
        ),
        400: OpenApiResponse(description="Bad request or login failed"),
        500: OpenApiResponse(description="Google authentication not configured"),
    },
)
@api_view(['POST'])
@permission_classes([AllowAny])
def google_login_callback(request):
    """
    Handle callback during redirect auth flow
    """
    code = request.data.get('code')
    
    if not code:
        return Response({'error': 'Authorization code is required'}, status=400)
    
    try:
        # Generate full callback URL
        callback_url = request.build_absolute_uri(reverse('google_login_callback'))
        
        # Get the Google SocialApp
        social_app = SocialApp.objects.get(provider="google")
        
        # Exchange code for token
        token_url = 'https://oauth2.googleapis.com/token'
        payload = {
            'code': code,
            'client_id': social_app.client_id,
            'client_secret': social_app.secret,
            'redirect_uri': callback_url,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=payload)
        token_data = response.json()
        
        if 'error' in token_data:
            return Response({
                'error': token_data.get('error'),
                'error_description': token_data.get('error_description')
            }, status=400)
        
        # Verify token and get user info
        adapter = GoogleOAuth2Adapter(request)
        login_data = adapter.parse_token({
            'access_token': token_data['access_token'],
            'id_token': token_data.get('id_token'),
            'expires_in': token_data.get('expires_in')
        })
        
        # Get user info
        userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        headers = {'Authorization': f'Bearer {token_data["access_token"]}'}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo = userinfo_response.json()
        login_data.update(userinfo)
        
        # Complete login
        social_login = adapter.complete_login(request, login_data)
        social_login.token = token_data
        
        login_completion = complete_social_login(request, social_login)
        
        if isinstance(login_completion, HttpResponseRedirect):
            user = social_login.account.user
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.get_full_name(),
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        else:
            return Response({'error': 'Login failed'}, status=400)
            
    except SocialApp.DoesNotExist:
        return Response({'error': 'Google authentication is not configured'}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@extend_schema(
    summary="Password Reset Redirect",
    description="Redirect password reset confirmation links to the frontend",
    parameters=[
        OpenApiParameter(
            name='key',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Password reset key',
        ),
    ],
    responses={
        302: OpenApiResponse(description="Redirect to frontend with reset key"),
    },
)
def password_reset_redirect(request, key):
    """
    Redirect password reset confirmation links to the frontend.
    This handles the case where users click password reset links from emails
    and redirects them to the frontend with the reset key.
    """
    # Use dynamic FRONTEND_URL instead of hardcoded localhost
    frontend_url = f"{settings.FRONTEND_URL}/accounts/password/reset/key/{key}"
    return HttpResponseRedirect(frontend_url)
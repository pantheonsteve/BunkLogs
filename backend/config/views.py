import json
import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.http import HttpResponseRedirect, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.urls import reverse
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

User = get_user_model()


class CustomEmailVerificationSentView(TemplateView):
    template_name = "account/verification_sent.html"


class UserRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("user_detail")


@require_GET
def get_csrf_token(request):
    token = get_token(request)
    return JsonResponse({"csrfToken": token})


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


class GoogleLoginView(APIView):
    """
    Custom view for initiating Google OAuth login using AllAuth
    This handles the backend exchange for auth code flow
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Used for redirecting to Google's auth page directly
        adapter = GoogleOAuth2Adapter(request)
        app = SocialApp.objects.get(provider="google")
        client = OAuth2Client(
            request,
            app.client_id,
            app.secret,
            adapter.access_token_url,
            adapter.callback_url,
        )
        authorization_url = adapter.authorize_url
        auth_url, state = client.get_redirect_url()
        request.session["socialaccount_state"] = state
        return Response({"authorization_url": auth_url})
    
    def post(self, request):
        """
        Handle the 'auth-code' flow from @react-oauth/google
        Uses the code to authenticate with Google and get user info
        """
        code = request.data.get('code')
        
        try:
            # Get the Google SocialApp configuration
            social_app = SocialApp.objects.get(provider="google")
            
            # Exchange the authorization code for tokens
            token_url = 'https://oauth2.googleapis.com/token'
            payload = {
                'code': code,
                'client_id': social_app.client_id,
                'client_secret': social_app.secret,
                'redirect_uri': 'postmessage',  # Special value for popup flow
                'grant_type': 'authorization_code'
            }
            
            # Exchange code for tokens
            response = requests.post(token_url, data=payload)
            token_data = response.json()
            
            if 'error' in token_data:
                return Response({
                    'error': token_data.get('error'),
                    'error_description': token_data.get('error_description')
                }, status=400)
            
            # Get user info with access token
            userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            headers = {'Authorization': f'Bearer {token_data["access_token"]}'}
            userinfo_response = requests.get(userinfo_url, headers=headers)
            userinfo = userinfo_response.json()
            
            # Create a login using AllAuth
            adapter = GoogleOAuth2Adapter(request)
            login_data = adapter.parse_token({
                'access_token': token_data['access_token'],
                'id_token': token_data.get('id_token'),
                'expires_in': token_data.get('expires_in')
            })
            login_data.update(userinfo)
            
            # Create the social account
            social_login = adapter.complete_login(request, login_data)
            social_login.token = token_data
            
            # Complete the login process
            login_completion = complete_social_login(request, social_login)
            
            if isinstance(login_completion, HttpResponseRedirect):
                # If login was successful and redirected
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
                # If there was an error during login completion
                return Response({'error': 'Login failed'}, status=400)
                
        except SocialApp.DoesNotExist:
            return Response({'error': 'Google authentication is not configured'}, status=500)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


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
        callback_url = request.build_absolute_uri(reverse('callback'))
        
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
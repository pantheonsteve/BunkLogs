import logging
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import redirect
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.models import SocialApp

logger = logging.getLogger(__name__)

def custom_google_login(request):
    """Custom view to initiate Google OAuth flow"""
    try:
        # Get client ID from database instead of settings
        google_app = SocialApp.objects.get(provider='google')
        client_id = google_app.client_id
        
        # Use a callback URL that exists in your URL patterns
        redirect_uri = request.build_absolute_uri('/api/auth/google/callback/')
        
        # Build the authorization URL
        auth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=email%20profile"
        
        return redirect(auth_url)
    except Exception as e:
        return HttpResponse(f"Error initiating Google login: {str(e)}")

def auth_success(request):
    """
    After successful authentication, redirect to frontend with tokens
    """
    logger.info("auth_success view called")
    
    if request.user.is_authenticated:
        logger.info(f"User authenticated: {request.user.email}")
        
        # Generate tokens
        try:
            refresh = RefreshToken.for_user(request.user)
            logger.info("Tokens generated successfully")
            
            # Build redirect URL with tokens as fragments
            redirect_url = (
                f"{settings.FRONTEND_URL}/auth/callback"
                f"#access_token={str(refresh.access_token)}"
                f"&refresh_token={str(refresh)}"
                f"&token_type=Bearer"
            )
            
            logger.info(f"Redirecting to: {redirect_url}")
            return HttpResponseRedirect(redirect_url)
        
        except Exception as e:
            logger.error(f"Error generating tokens: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    else:
        logger.warning("User not authenticated in auth_success view")
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/signin?error=not_authenticated")
    
def test_google_auth(request):
    """Simple view to test google auth flow"""
    
    callback_url = request.build_absolute_uri('/api/auth/google/callback/')
    
    return HttpResponse(f"""
    <html>
        <head>
            <title>Google Auth Test</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; overflow: auto; }}
                .url {{ word-break: break-all; }}
            </style>
        </head>
        <body>
            <h1>Google Auth Test</h1>
            
            <h2>Current User</h2>
            <p>{request.user.email if request.user.is_authenticated else 'Not logged in'}</p>
            
            <h2>Google OAuth Settings</h2>
            <pre>
Client ID: {getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}).get('google', {}).get('APP', {}).get('client_id', 'Not configured')}
Callback URL: {callback_url}
            </pre>
            
            <h2>Test Login</h2>
            <p>Click the link below to test Google login:</p>
            <a href="/api/auth/google/">Login with Google</a>
            
            <h2>Test AllAuth URL</h2>
            <p>Click the link below to test standard AllAuth URL:</p>
            <a href="/accounts/google/login/">Standard AllAuth Login</a>
            
            <h2>Frontend Callback</h2>
            <p class="url">The frontend callback should be: {getattr(settings, 'FRONTEND_URL', 'Not configured')}/auth/callback</p>
            <p>Make sure this URL is added to your Google OAuth consent screen's authorized redirect URIs.</p>
        </body>
    </html>
    """)
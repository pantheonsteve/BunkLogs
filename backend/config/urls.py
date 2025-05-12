from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Import your views
from bunk_logs.views import auth_success, test_google_auth, custom_google_login
from bunk_logs.users.views import (
    GoogleLoginView,
    GoogleCallbackView,
    token_refresh,
    token_authenticate,
    get_csrf_token,
    get_auth_status,
    logout_view,
    UserRedirectView,
)


# For debugging URLs
from django.http import HttpResponse
from django.urls import get_resolver

def show_urls(request):
    urls = get_resolver().url_patterns
    return HttpResponse("<br>".join([str(url) for url in urls]))

# API Router
router = DefaultRouter()

urlpatterns = [
    # Admin
    path(settings.ADMIN_URL, admin.site.urls),
    
    # Debug
    path('debug/show-urls/', show_urls),

    path('custom-google-login/', custom_google_login, name='custom_google_login'),
    
    # Django AllAuth - standard Django views
    path('accounts/', include('allauth.urls')),

    path('account/provider/callback', GoogleLoginView.as_view(), name='provider_callback'),
    
    # Authentication success redirect
    path('auth/success/', auth_success, name='auth_success'),
    
    # REST API Authentication (dj-rest-auth)
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    
    # Token handling
    path('api/token/refresh/', token_refresh, name='token_refresh'),
    path('api/token/authenticate/', token_authenticate, name='token_authenticate'),
    path('api/csrf-token/', get_csrf_token, name='csrf_token'),
    path('api/auth/status/', get_auth_status, name='auth_status'),
    path('api/auth/logout/', logout_view, name='logout'),
    
    # Google OAuth endpoints
    path('api/auth/google/', GoogleLoginView.as_view(), name='google_login'),
    path('api/auth/google/callback/', GoogleCallbackView.as_view(), name='google_callback'),
    path('test-google-auth/', test_google_auth, name='test_google_auth'),
    
    # Auth callback template for frontend
    path('auth/callback/', 
        TemplateView.as_view(template_name="socialaccount/callback.html"), 
        name="auth_callback"),
    
    # Your API URLs
    path("api/v1/", include("bunk_logs.api.urls")),
    
    # DRF API browser login
    path('api-auth/', include('rest_framework.urls')),
]

# Debug toolbar for development
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
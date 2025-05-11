from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from bunk_logs.api.views import *
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from rest_framework.routers import DefaultRouter
from django.views.generic import TemplateView
from bunk_logs.users.views import (
    GoogleLoginView,
    GoogleCallbackView,
    CustomEmailVerificationSentView,
    UserRedirectView,
    get_csrf_token,
    get_auth_status,
    logout_view,
    token_refresh,
    token_authenticate,
)
from .views import (
    google_login_callback,
    validate_google_token,
)

router = DefaultRouter()

urlpatterns = [
    # Admin URL
    path(settings.ADMIN_URL, admin.site.urls),

    # path('api/user/register/', UserCreate.as_view(), name='user_create'),
    # path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('api-auth/', include('rest_framework.urls')),
    path('accounts/', include('allauth.urls')),
    # Include the API endpoints:
    path("_allauth/", include("allauth.headless.urls")),
    path('', include(router.urls)),
    # path('callback/', google_login_callback, name='callback'),
    # path('api/auth/user/', UserDetailView.as_view(), name='user_detail'),
    path('api/google/validate_token/', validate_google_token, name='validate_token'),
    
    # User management
    path("_allauth/", include("allauth.urls")),
    
    # API Auth endpoints 
    # path('auth/token/refresh/', token_refresh),
    # path('auth/token/authenticate/', token_authenticate),  # New endpoint for token-based auth
    # path('auth/token/verify/', token_refresh, name='token_verification'),  # Add token verification endpoint
    # path('auth/csrf-token/', get_csrf_token, name='csrf_token'),
    # path('auth/status/', get_auth_status, name='auth_status'),
    # path('auth/logout/', logout_view),
    path("~redirect/", view=UserRedirectView.as_view(), name="redirect"),
    
    # Social auth
    #path('auth/google/', GoogleLoginView.as_view(), name='google_login'),
    #path('auth/callback/', GoogleCallbackView.as_view(), name='google_callback'),

    # Allauth headless URLs
    #path("_allauth/", include("allauth.headless.urls")),
    
    # Custom email verification view
    # path('auth/registration/account-email-verification-sent/', 
    #      CustomEmailVerificationSentView.as_view(), 
    #      name='account_email_verification_sent'),
    
    # Django Rest Auth URLs
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    
    # Auth callback page for frontend
    re_path(r'^auth/callback/?$', 
        TemplateView.as_view(template_name="socialaccount/callback.html"), 
        name="google_callback_redirect"),
    
    # Your app-specific API URLs
    path("api/v1/", include("bunk_logs.api.urls")),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
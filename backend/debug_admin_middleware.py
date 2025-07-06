"""
Debug middleware to track admin login requests
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import authenticate, login
from django.contrib.admin.forms import AdminAuthenticationForm
from django.http import HttpResponse

logger = logging.getLogger(__name__)

class AdminLoginDebugMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/admin/login/') and request.method == 'POST':
            logger.info("=== ADMIN LOGIN POST REQUEST DEBUG ===")
            logger.info(f"Path: {request.path}")
            logger.info(f"Method: {request.method}")
            logger.info(f"POST data: {dict(request.POST)}")
            logger.info(f"User authenticated: {getattr(request, 'user', 'NO USER ATTR').is_authenticated if hasattr(request, 'user') else 'NO USER ATTR'}")
            logger.info(f"Session key: {request.session.session_key}")
            logger.info(f"CSRF token: {request.META.get('HTTP_X_CSRFTOKEN', 'Not found')}")
            logger.info(f"Content type: {request.content_type}")
            logger.info(f"Cookies: {dict(request.COOKIES)}")
            
            # Try to authenticate manually
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            if username and password:
                logger.info(f"Attempting authentication for username: {username}")
                user = authenticate(request, username=username, password=password)
                logger.info(f"Authentication result: {user}")
                
                if user:
                    logger.info(f"User is active: {user.is_active}")
                    logger.info(f"User is staff: {user.is_staff}")
                    logger.info(f"User is superuser: {user.is_superuser}")
                
                # Test the admin form directly
                form = AdminAuthenticationForm(request, data=request.POST)
                logger.info(f"Form is valid: {form.is_valid()}")
                if not form.is_valid():
                    logger.info(f"Form errors: {form.errors}")
                    logger.info(f"Form non-field errors: {form.non_field_errors()}")
            
            logger.info("=== END ADMIN LOGIN DEBUG ===")
        
        return None  # Continue with normal request processing
    
    def process_response(self, request, response):
        if request.path.startswith('/admin/login/') and request.method == 'POST':
            logger.info("=== ADMIN LOGIN POST RESPONSE DEBUG ===")
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.items())}")
            if hasattr(response, 'url'):
                logger.info(f"Redirect URL: {response.url}")
            logger.info(f"User authenticated after: {getattr(request, 'user', 'NO USER ATTR').is_authenticated if hasattr(request, 'user') else 'NO USER ATTR'}")
            logger.info("=== END RESPONSE DEBUG ===")
        
        return response

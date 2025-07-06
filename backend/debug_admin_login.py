"""
Debug admin login view to understand what's happening
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import authenticate, login, REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import FormView
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@sensitive_post_parameters()
@csrf_protect
@never_cache
def debug_admin_login(request, template_name='admin/login.html',
                     redirect_field_name=REDIRECT_FIELD_NAME,
                     authentication_form=AdminAuthenticationForm,
                     extra_context=None):
    """
    Debug version of admin login view
    """
    logger.info("=== DEBUG ADMIN LOGIN VIEW ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"User: {request.user}")
    logger.info(f"Is authenticated: {request.user.is_authenticated}")
    
    if request.method == 'GET':
        logger.info("GET request - showing login form")
        return original_admin_login(request, template_name, redirect_field_name, authentication_form, extra_context)
    
    # POST request
    logger.info("POST request - processing login")
    logger.info(f"POST data: {dict(request.POST)}")
    
    redirect_to = request.POST.get(redirect_field_name, request.GET.get(redirect_field_name, ''))
    logger.info(f"Redirect to: {redirect_to}")
    
    form = authentication_form(request, data=request.POST)
    logger.info(f"Form created: {form}")
    logger.info(f"Form is bound: {form.is_bound}")
    logger.info(f"Form data: {form.data}")
    
    if form.is_valid():
        logger.info("Form is VALID")
        user = form.get_user()
        logger.info(f"Authenticated user: {user}")
        logger.info(f"User is active: {user.is_active}")
        logger.info(f"User is staff: {user.is_staff}")
        
        # Check if user can access admin
        if user.is_active and user.is_staff:
            logger.info("User can access admin - logging in")
            login(request, user)
            logger.info(f"User logged in: {request.user}")
            logger.info(f"Session key: {request.session.session_key}")
            
            # Redirect to admin
            redirect_url = resolve_url(redirect_to or settings.LOGIN_REDIRECT_URL or '/admin/')
            logger.info(f"Redirecting to: {redirect_url}")
            return HttpResponseRedirect(redirect_url)
        else:
            logger.error(f"User cannot access admin - active: {user.is_active}, staff: {user.is_staff}")
    else:
        logger.error("Form is INVALID")
        logger.error(f"Form errors: {form.errors}")
        logger.error(f"Non-field errors: {form.non_field_errors()}")
    
    logger.info("=== END DEBUG ADMIN LOGIN ===")
    
    # Fall back to original view
    return original_admin_login(request, template_name, redirect_field_name, authentication_form, extra_context)


# Import the original admin login
from django.contrib.admin.sites import AdminSite
original_admin_login = AdminSite().login

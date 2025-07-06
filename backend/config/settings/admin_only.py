"""
Minimal admin-only settings for local development
This bypasses AllAuth entirely for admin access
"""

from .base import *  # noqa: F403

# Override problematic AllAuth settings completely
INSTALLED_APPS = [app for app in INSTALLED_APPS if not app.startswith('allauth')]

# Add back only essential apps
INSTALLED_APPS += [
    "debug_toolbar",  # Re-add debug toolbar for development
]

# Use only Django's basic authentication
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# Remove AllAuth middleware
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# Simple session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'

# Simple CSRF settings
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Force Django admin login
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"

# Debug settings
DEBUG = True
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "testserver", "django"]

# Use local database and other settings from base
# (DATABASE_URL, etc. will be inherited from base.py)

# Minimal local settings for admin debugging
# This file bypasses AllAuth to test basic admin authentication

# Import minimal base settings
import os
from pathlib import Path

# Basic Django settings
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

DEBUG = True
SECRET_KEY = "UwQ4Bqm56JIeEszbx3merf4E5Pcl5Ih9IVOdDjeOsZEDWJ52uovXQTmOuNApPyIm"

ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "testserver", "django"]

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "bunk_logs_local",
        "USER": "postgres", 
        "PASSWORD": "postgres",
        "HOST": "postgres",
        "PORT": "5432",
    }
}

# Essential Django apps only
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bunk_logs.users",  # Your custom user app
]

# Essential middleware only
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# Authentication
AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

# Disable AllAuth admin integration
DJANGO_ADMIN_FORCE_ALLAUTH = False

# CSRF settings for local development
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://0.0.0.0:8000',
]

# Session settings
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = str(BASE_DIR / "staticfiles")

# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Root URL configuration
ROOT_URLCONF = "config.urls"

# WSGI application
WSGI_APPLICATION = "config.wsgi.application"

# Time zone
TIME_ZONE = "UTC"
USE_TZ = True

# Cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    },
}

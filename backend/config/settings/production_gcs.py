# Production settings with Google Cloud Storage instead of AWS S3
import os
import environ

env = environ.Env()

# Import base production settings
from .base import *  # noqa: F403, F401

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

# Essential settings - Updated for Cloud Run
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    "*.run.app",
    "bunklogs.net", 
    "bunk-logs-backend-koumwfa74a-uc.a.run.app",
    "bunk-logs-backend-461994890254.us-central1.run.app",
    "localhost",
]

# DATABASES
# ------------------------------------------------------------------------------
# Updated for explicit Cloud SQL configuration
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"), 
        "HOST": os.environ.get("POSTGRES_HOST"),
        "PORT": os.environ.get("POSTGRES_PORT"),
        "CONN_MAX_AGE": env.int("CONN_MAX_AGE", default=60),
    }
}

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
            "IGNORE_EXCEPTIONS": True,
        },
    },
}

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=True,
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF",
    default=True,
)

# GOOGLE CLOUD STORAGE CONFIGURATION
# ------------------------------------------------------------------------------
# https://django-storages.readthedocs.io/en/latest/backends/gcloud.html
GS_BUCKET_NAME = env("GS_BUCKET_NAME", default="bunk-logs-static")
GS_DEFAULT_ACL = None  # Use bucket's default permissions
GS_QUERYSTRING_AUTH = False
GS_FILE_OVERWRITE = False
GS_MAX_MEMORY_SIZE = 100_000_000  # 100MB

# Static and media files configuration
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": GS_BUCKET_NAME,
            "location": "media",
            "file_overwrite": False,
            "default_acl": None,  # Use bucket's default permissions
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": GS_BUCKET_NAME,
            "location": "static",
            "default_acl": None,  # Use bucket's default permissions
        },
    },
}

# Static and Media URLs
STATIC_URL = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/static/"
MEDIA_URL = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/media/"

# For collectfasta compatibility
COLLECTFASTA_STRATEGY = "collectfasta.strategies.gcloud.GoogleCloudStrategy"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="Bunk Logs <noreply@bunklogs.net>",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[Bunk Logs] ",
)
ACCOUNT_EMAIL_SUBJECT_PREFIX = EMAIL_SUBJECT_PREFIX

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL")

# Anymail
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
INSTALLED_APPS += ["anymail"]  # noqa: F405
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
# https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
# https://anymail.readthedocs.io/en/stable/esps/mailgun/
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
ANYMAIL = {
    "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),
    "MAILGUN_SENDER_DOMAIN": env("MAILGUN_DOMAIN"),
    "MAILGUN_API_URL": env("MAILGUN_API_URL", default="https://api.mailgun.net/v3"),
}

# LOGGING
# ------------------------------------------------------------------------------
# Updated for better Cloud Run debugging
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        # Errors logged by the SDK itself
        'sentry_sdk': {'level': 'ERROR', 'handlers': ['console'], 'propagate': False},
        'django.security.DisallowedHost': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

# Add this to the end of backend/config/settings/production_gcs.py

# Frontend URLs - Production overrides
# ------------------------------------------------------------------------------
FRONTEND_URL = env("FRONTEND_URL", default="https://clc.bunklogs.net")
SPA_URL = FRONTEND_URL

# Override redirect URLs for production
LOGIN_REDIRECT_URL = env('LOGIN_REDIRECT_URL', default=f"{FRONTEND_URL}/dashboard")
ACCOUNT_LOGOUT_REDIRECT_URL = env('ACCOUNT_LOGOUT_REDIRECT_URL', default=f"{FRONTEND_URL}/signin")

# Update CORS settings for production
CORS_ALLOWED_ORIGINS = [
    "https://*.bunklogs.net",
    "https://www.bunklogs.net",
    "https://clc.bunklogs.net",  # Your actual frontend URL
]

# Update CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    'https://clc.bunklogs.net', 
    'https://www.bunklogs.net',
]

# Update allowed hosts for production (remove localhost)
ALLOWED_HOSTS = [
    "*.run.app",
    "bunklogs.net", 
    "bunk-logs-backend-koumwfa74a-uc.a.run.app",
    "bunk-logs-backend-461994890254.us-central1.run.app",
    "localhost",
]

"""
Render.com production settings for BunkLogs backend.

This file contains settings specifically for deployment on Render.com.
"""

from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS", 
    default=[
        "bunklogs.net",
        "www.bunklogs.net",
        "*.onrender.com",  # Render.com domain pattern
    ]
)

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"] = env.db("DATABASE_URL")  # noqa F405
DATABASES["default"]["ATOMIC_REQUESTS"] = True  # noqa F405
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)  # noqa F405

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
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
# CRITICAL: Enable cross-origin sessions for production - share across subdomains
SESSION_COOKIE_NAME = "__Secure-sessionid"
SESSION_COOKIE_SAMESITE = 'Lax'  # Better subdomain sharing than 'None'
SESSION_COOKIE_DOMAIN = '.bunklogs.net'  # Share sessions across all bunklogs.net subdomains
SESSION_COOKIE_HTTPONLY = False  # Allow JavaScript access for AllAuth headless mode
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# CRITICAL: Enable cross-origin cookies for production - match session settings  
CSRF_COOKIE_NAME = "__Secure-csrftoken"
CSRF_COOKIE_SAMESITE = 'Lax'  # Match session cookie setting
CSRF_COOKIE_DOMAIN = '.bunklogs.net'  # Share CSRF tokens across all bunklogs.net subdomains
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript access to CSRF token for AllAuth headless mode
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool("DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True)

# STATIC FILES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-storage
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# MEDIA
# ------------------------------------------------------------------------------
# region http://stackoverflow.com/questions/26890816/how-to-upload-image-to-s3-using-boto3-when-the-image-is-uploaded-via-html-for
# Determine if using S3 for media files
USE_S3 = env.bool("USE_S3", default=False)

if USE_S3:
    # AWS Settings
    AWS_ACCESS_KEY_ID = env("DJANGO_AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("DJANGO_AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("DJANGO_AWS_STORAGE_BUCKET_NAME")
    AWS_QUERYSTRING_AUTH = False
    # DO NOT change these unless you know what you're doing.
    _AWS_EXPIRY = 60 * 60 * 24 * 7
    # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": f"max-age={_AWS_EXPIRY}, s-maxage={_AWS_EXPIRY}, must-revalidate"
    }
    # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
    AWS_S3_REGION_NAME = env("DJANGO_AWS_S3_REGION_NAME", default=None)
    # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#cloudfront
    AWS_S3_CUSTOM_DOMAIN = env("DJANGO_AWS_S3_CUSTOM_DOMAIN", default=None)
    aws_s3_domain = AWS_S3_CUSTOM_DOMAIN or f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    # Media files
    DEFAULT_FILE_STORAGE = "bunk_logs.utils.storages.MediaRootS3Boto3Storage"
    MEDIA_URL = f"https://{aws_s3_domain}/media/"
else:
    # Local file storage (default)
    MEDIA_URL = "/media/"
    MEDIA_ROOT = str(APPS_DIR / "media")

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="BunkLogs <noreply@bunklogs.net>",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[BunkLogs] ",
)

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# CORS and Frontend Settings
# ------------------------------------------------------------------------------
# Frontend URL for CORS and redirects
FRONTEND_URL = env("FRONTEND_URL", default="https://clc.bunklogs.net")

# CORS settings for Render.com deployment with GCS frontend
CORS_ALLOWED_ORIGINS = [
    "https://clc.bunklogs.net",  # Your actual frontend URL
    "https://bunklogs.net",
    "https://www.bunklogs.net",
    "https://storage.googleapis.com",  # Direct bucket access (no path)
    "https://storage.cloud.google.com",  # Alternative bucket URL (no path)
]

CSRF_TRUSTED_ORIGINS = [
    "https://clc.bunklogs.net",  # Your actual frontend URL
    "https://bunklogs.net",
    "https://www.bunklogs.net",
    "https://storage.googleapis.com",
    "https://storage.cloud.google.com",
]

# JWT Settings for dj-rest-auth
REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'bunklogs-auth',
    'JWT_AUTH_REFRESH_COOKIE': 'bunklogs-refresh',
    'JWT_AUTH_SECURE': True,  # Always True in production
    'JWT_AUTH_HTTPONLY': True,
    'JWT_AUTH_SAMESITE': 'Lax',
    'USER_DETAILS_SERIALIZER': 'bunk_logs.users.serializers.UserSerializer',
}

# Update redirect URLs to use the correct frontend URL
LOGIN_REDIRECT_URL = f"{FRONTEND_URL}/dashboard"
ACCOUNT_LOGOUT_REDIRECT_URL = f"{FRONTEND_URL}/signin"

# Django AllAuth settings for production
ACCOUNT_EMAIL_VERIFICATION = 'none'  # Consider 'mandatory' for production
ACCOUNT_LOGOUT_ON_GET = True

# Social authentication
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# django-rest-framework
# -------------------------------------------------------------------------------
# Tools that generate code samples can use SERVERS to point to the correct domain
SPECTACULAR_SETTINGS["SERVERS"] = [
    {"url": "https://bunklogs.onrender.com", "description": "Render.com API server"},
]

# Datadog APM Configuration for Render
# ------------------------------------------------------------------------------
if os.getenv('DD_TRACE_ENABLED', 'false').lower() == 'true':
    # Datadog APM settings
    DD_TRACE_AGENT_URL = os.getenv('DD_TRACE_AGENT_URL', 'http://datadog-agent:8126')
    
    # Ensure ddtrace patches Django components
    INSTALLED_APPS += ['ddtrace.contrib.django']
    
    # Enhanced logging for Datadog
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
            'datadog': {
                'format': '[dd.service=%(dd.service)s dd.env=%(dd.env)s dd.version=%(dd.version)s dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] %(levelname)s %(asctime)s %(module)s %(message)s',
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'datadog' if os.getenv('DD_LOGS_INJECTION') == 'true' else 'verbose',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
            'ddtrace': {
                'handlers': ['console'],
                'level': 'WARNING',
            },
            'bunk_logs': {  # Your app-specific logging
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    }

# Database instrumentation settings
DATABASES['default']['OPTIONS'] = DATABASES['default'].get('OPTIONS', {})
DATABASES['default']['OPTIONS'].update({
    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
    'charset': 'utf8mb4',
}) if 'mysql' in DATABASES['default'].get('ENGINE', '') else None

# Cache instrumentation
if 'django_redis' in CACHES.get('default', {}).get('BACKEND', ''):
    CACHES['default']['OPTIONS'] = CACHES['default'].get('OPTIONS', {})

# Custom middleware for additional tracing (optional)
MIDDLEWARE = [
    'ddtrace.contrib.django.TraceMiddleware',
] + MIDDLEWARE

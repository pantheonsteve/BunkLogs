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
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
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
    "https://storage.googleapis.com/bunk-logs-frontend-prod",  # Direct bucket access
    "https://storage.cloud.google.com/bunk-logs-frontend-prod",  # Alternative bucket URL
]

CSRF_TRUSTED_ORIGINS = [
    "https://clc.bunklogs.net",  # Your actual frontend URL
    "https://bunklogs.net",
    "https://www.bunklogs.net",
    "https://storage.googleapis.com/bunk-logs-frontend-prod",
    "https://storage.cloud.google.com/bunk-logs-frontend-prod",
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

# config/settings/production.py
# Add these database configurations for Elastic Beanstalk

import os

# DataDog APM configuration
# ------------------------------------------------------------------------------
if os.getenv('DD_TRACE_ENABLED', 'false').lower() == 'true':
    INSTALLED_APPS += ['ddtrace.contrib.django']

    # Datadog APM settings
    DATADOG_TRACE = {
        'DEFAULT_SERVICE': 'bunk-logs-django',
        'TAGS': {'env': 'production'},
    }

# Set DATABASE_URL from RDS environment variables if available
# This ensures base.py can import successfully
if 'RDS_HOSTNAME' in os.environ and 'DATABASE_URL' not in os.environ:
    # Construct DATABASE_URL from RDS environment variables
    rds_user = os.environ.get('RDS_USERNAME', 'postgres')
    rds_password = os.environ.get('RDS_PASSWORD', '')
    rds_host = os.environ.get('RDS_HOSTNAME', 'localhost')
    rds_port = os.environ.get('RDS_PORT', '5432')
    rds_db = os.environ.get('RDS_DB_NAME', 'ebdb')
    
    os.environ['DATABASE_URL'] = f"postgresql://{rds_user}:{rds_password}@{rds_host}:{rds_port}/{rds_db}"

# Set a dummy DATABASE_URL if none exists (for build time)
elif 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

# Set a dummy SECRET_KEY if none exists (for build time)
if 'DJANGO_SECRET_KEY' not in os.environ:
    os.environ['DJANGO_SECRET_KEY'] = 'build-time-secret-key-not-for-production'

from .base import *  # noqa

# GENERAL
# ------------------------------------------------------------------------------
def get_database_config():
    """
    Get database configuration from EB RDS environment variables
    Falls back to local/docker configuration if RDS vars not available
    """
    # Check if we're running on Elastic Beanstalk (RDS variables present)
    if 'RDS_HOSTNAME' in os.environ:
        return {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ.get('RDS_DB_NAME', 'ebdb'),
                'USER': os.environ.get('RDS_USERNAME', 'postgres'),
                'PASSWORD': os.environ.get('RDS_PASSWORD', ''),
                'HOST': os.environ.get('RDS_HOSTNAME', 'localhost'),
                'PORT': os.environ.get('RDS_PORT', '5432'),
                'OPTIONS': {
                    'connect_timeout': 60,
                },
                'CONN_MAX_AGE': 600,
            }
        }
    
    # Fallback to Docker/Local PostgreSQL environment variables
    elif 'POSTGRES_HOST' in os.environ:
        return {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ.get('POSTGRES_DB', 'bunk_logs'),
                'USER': os.environ.get('POSTGRES_USER', 'postgres'),
                'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
                'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
                'PORT': os.environ.get('POSTGRES_PORT', '5432'),
                'OPTIONS': {
                    'connect_timeout': 60,
                },
                'CONN_MAX_AGE': 600,
            }
        }
    
    # Fallback to DATABASE_URL if available (Heroku-style)
    elif 'DATABASE_URL' in os.environ:
        import dj_database_url
        return {
            'default': dj_database_url.config(
                default=os.environ.get('DATABASE_URL'),
                conn_max_age=600,
                conn_health_checks=True,
            )
        }
    
    # Final fallback - should not happen in production
    else:
        raise ValueError(
            "No database configuration found. Expected RDS_HOSTNAME, "
            "POSTGRES_HOST, or DATABASE_URL environment variables."
        )

DATABASES = get_database_config()
DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["bunklogs.net", "clc.bunklogs.net", "admin.bunklogs.net"])

# Frontend URLs for production
# ------------------------------------------------------------------------------
FRONTEND_URL = env('FRONTEND_URL', default="https://clc.bunklogs.net")
LOGIN_REDIRECT_URL = env('LOGIN_REDIRECT_URL', default=f'{FRONTEND_URL}/dashboard')
ACCOUNT_LOGOUT_REDIRECT_URL = env('ACCOUNT_LOGOUT_REDIRECT_URL', default=f'{FRONTEND_URL}/signin')

# STATIC FILES CONFIGURATION FOR EB
# ------------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Media files (if you plan to use them)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# SECURITY SETTINGS
# ------------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# CORS settings (if you're using django-cors-headers)
# ------------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = os.environ.get('DJANGO_CORS_ALLOW_ALL_ORIGINS', 'False').lower() == 'true'
CORS_ALLOWED_ORIGINS = [
    origin.strip() 
    for origin in os.environ.get('DJANGO_CORS_ALLOWED_ORIGINS', 'https://clc.bunklogs.net,https://bunklogs.net').split(',') 
    if origin.strip()
]

# Update CSRF trusted origins for production
CSRF_TRUSTED_ORIGINS = ['https://bunklogs.net', 'https://clc.bunklogs.net', 'https://admin.bunklogs.net']

# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "bunk_logs": {  # Replace with your app name
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# CACHES (Optional - for better performance)
# ------------------------------------------------------------------------------
if 'REDIS_URL' in os.environ:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.environ.get('REDIS_URL'),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        }
    }
else:
    # Fallback to local memory cache
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# EMAIL CONFIGURATION (Update with your email backend)
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@bunklogs.net")
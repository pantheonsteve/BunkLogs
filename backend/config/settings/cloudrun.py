# Production settings override for Cloud Run deployment without AWS S3
import os
import environ

env = environ.Env()

# Set required environment variables before importing production settings
os.environ.setdefault('DJANGO_AWS_ACCESS_KEY_ID', 'dummy')
os.environ.setdefault('DJANGO_AWS_SECRET_ACCESS_KEY', 'dummy')
os.environ.setdefault('DJANGO_AWS_STORAGE_BUCKET_NAME', 'dummy-bucket')
os.environ.setdefault('MAILGUN_API_KEY', 'dummy')
os.environ.setdefault('MAILGUN_DOMAIN', 'dummy.mailgun.org')
os.environ.setdefault('DJANGO_ADMIN_URL', 'admin/')

from .production import *  # noqa: F403, F401

# Override allowed hosts for Cloud Run
ALLOWED_HOSTS = [
    "bunklogs.net",
    "*.run.app",
    "bunk-logs-backend-461994890254.us-central1.run.app",
    "bunk-logs-backend-koumwfa74a-uc.a.run.app",
    "localhost:5173"
]

# Override storage settings to use local storage instead of S3
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Static files configuration for Cloud Run
STATIC_URL = "/static/"
STATIC_ROOT = "/app/staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = "/app/media"

# Whitenoise configuration
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Override database configuration for Cloud Run + Cloud SQL
# Build database URL for Cloud SQL proxy
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="bunk-logs-clc"),
        "USER": env("POSTGRES_USER", default="stevebresnick"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="April221979"),
        "HOST": env("POSTGRES_HOST", default="/cloudsql/bunklogsauth:us-central1:bunk-logs"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}

# Remove collectfasta from INSTALLED_APPS to avoid conflicts
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'collectfasta']

# Disable Collectfasta by not setting any strategy
# Remove COLLECTFASTA_STRATEGY entirely so it doesn't interfere
if 'COLLECTFASTA_STRATEGY' in globals():
    del COLLECTFASTA_STRATEGY

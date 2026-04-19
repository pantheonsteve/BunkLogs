"""
With these settings, tests run faster.
"""

from .base import *
from .base import TEMPLATES
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="vTyrdWzBDBAEIBHAPtODr3Vg2iFgKhLbGa0xSpnMbVxNg0zX5a10GABEnUQVPDgN",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# DEBUGGING FOR TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore[index]

# STATIC FILES
# ------------------------------------------------------------------------------
# Use plain storage in tests — no collectstatic required.
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# ALLAUTH
# ------------------------------------------------------------------------------
# Disable headless-only mode so traditional allauth URLs (e.g. account_login)
# are registered and tests that call reverse("account_login") can resolve them.
HEADLESS_ONLY = False

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "http://media.testserver/"
# Your stuff...
# ------------------------------------------------------------------------------

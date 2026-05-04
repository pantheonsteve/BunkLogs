# Load local env before importing base: base reads DJANGO_SECRET_KEY at import time.
import os
import socket
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
_env_file = BASE_DIR / ".envs" / ".local" / ".django"
if _env_file.exists():
    environ.Env.read_env(str(_env_file))
_DEV_FALLBACK_SECRET_KEY = (
    "UwQ4Bqm56JIeEszbx3merf4E5Pcl5Ih9IVOdDjeOsZEDWJ52uovXQTmOuNApPyIm"
)
os.environ.setdefault("DJANGO_SECRET_KEY", _DEV_FALLBACK_SECRET_KEY)


def _rewrite_compose_network_hosts_for_local_shell() -> None:
    """Compose .django uses service hostnames that only resolve on the compose network.

    Podman often has no ``/.dockerenv``; resolve ``postgres``/``redis``/``mailpit`` and
    fall back to loopback when ``manage.py`` runs on the host with published ports.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url and "@postgres:" in db_url:
        try:
            socket.getaddrinfo("postgres", 5432, type=socket.SOCK_STREAM)
        except OSError:
            os.environ["DATABASE_URL"] = db_url.replace("@postgres:", "@127.0.0.1:", 1)

    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url and "://redis:" in redis_url:
        try:
            socket.getaddrinfo("redis", 6379, type=socket.SOCK_STREAM)
        except OSError:
            os.environ["REDIS_URL"] = redis_url.replace("://redis:", "://127.0.0.1:", 1)

    email_host = os.environ.get("EMAIL_HOST")
    if email_host is None or email_host == "mailpit":
        try:
            socket.getaddrinfo("mailpit", 1025, type=socket.SOCK_STREAM)
        except OSError:
            os.environ["EMAIL_HOST"] = "127.0.0.1"


_rewrite_compose_network_hosts_for_local_shell()

from .base import *
from .base import INSTALLED_APPS
from .base import MIDDLEWARE
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY", default=_DEV_FALLBACK_SECRET_KEY)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "testserver", ".bunklogs.net"]

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    },
}
# CORS HEADERS
# ------------------------------------------------------------------------------

# CSRF Configuration for Local Development
# Override base settings that require HTTPS for local HTTP development
CSRF_COOKIE_SECURE = False  # Allow CSRF cookies over HTTP for local development
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript access for AllAuth headless mode
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# CORS Configuration for Local Development
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

# CORS_ALLOW_ALL_ORIGINS = True  # Don't use this with credentials

# If you need to support older browsers:
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-organization-slug",
]


# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = env("EMAIL_HOST", default="mailpit")
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025

# django-debug-toolbar
# ------------------------------------------------------------------------------
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
INSTALLED_APPS += ["debug_toolbar"]
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
# https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": [
        "debug_toolbar.panels.redirects.RedirectsPanel",
        # Disable profiling panel due to an issue with Python 3.12:
        # https://github.com/jazzband/django-debug-toolbar/issues/1875
        "debug_toolbar.panels.profiling.ProfilingPanel",
    ],
    "SHOW_TEMPLATE_CONTEXT": True,
}
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]
if env("USE_DOCKER") == "yes":
    try:
        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
        INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]
    except socket.gaierror:
        # Fallback for containerized environments where hostname resolution fails
        pass

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]

# Your stuff...
# ------------------------------------------------------------------------------

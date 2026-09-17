"""Allowlisted SPA origins for post-OAuth redirects.

``FRONTEND_URL`` is a single default (CLC). A multi-org user who starts
on ``tbe.bunklogs.net`` must return there — membership in CLC must not
send them to Crane Lake. Only ``*.bunklogs.net`` tenant SPAs and local
Vite are accepted — never ``admin`` / ``www`` / ``api``.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.signing import BadSignature
from django.core.signing import SignatureExpired
from django.core.signing import TimestampSigner

# Keep in sync with core.middleware._SUBDOMAIN_SKIP and frontend orgSlug.js.
_RESERVED_LABELS = frozenset({"", "www", "admin", "api", "localhost"})
_STATE_SALT = "bunklogs-google-oauth-frontend"
_STATE_MAX_AGE = 600
_LOCAL_DEV_PORTS = frozenset({5173, 5174, 3000})
_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

OAUTH_ORIGIN_COOKIE = "oauth_frontend_origin"


def default_frontend_origin() -> str:
    raw = getattr(settings, "FRONTEND_URL", "https://clc.bunklogs.net")
    return normalize_origin(raw) or "https://clc.bunklogs.net"


def normalize_origin(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        return None
    if parsed.path not in {"", "/"}:
        return None
    if parsed.params or parsed.query or parsed.fragment or parsed.username or parsed.password:
        return None
    netloc = host
    if parsed.port and parsed.port not in {80, 443}:
        netloc = f"{host}:{parsed.port}"
    return f"{parsed.scheme}://{netloc}"


def tenant_label_from_origin(origin: str | None) -> str | None:
    normalized = normalize_origin(origin)
    if not normalized:
        return None
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1"}:
        return "localhost"
    labels = host.split(".")
    if len(labels) == 3 and labels[-2:] == ["bunklogs", "net"]:
        label = labels[0]
        if label not in _RESERVED_LABELS:
            return label
    return None


def origin_from_tenant_label(label: str | None) -> str | None:
    if not label or not isinstance(label, str):
        return None
    slug = label.strip().lower()
    if slug == "localhost":
        return "http://localhost:5173"
    if not _SLUG_RE.fullmatch(slug) or slug in _RESERVED_LABELS:
        return None
    return f"https://{slug}.bunklogs.net"


def coerce_origin(raw: str | None) -> str | None:
    origin = normalize_origin(raw)
    if origin:
        return origin
    if isinstance(raw, str):
        return origin_from_tenant_label(raw)
    return None


def is_allowed_frontend_origin(origin: str | None) -> bool:
    normalized = normalize_origin(origin)
    if not normalized:
        return False
    if normalized == default_frontend_origin():
        return True

    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()

    if host in {"localhost", "127.0.0.1"}:
        return parsed.scheme == "http" and parsed.port in _LOCAL_DEV_PORTS

    labels = host.split(".")
    if (
        parsed.scheme == "https"
        and parsed.port is None
        and len(labels) == 3
        and labels[-2:] == ["bunklogs", "net"]
    ):
        return labels[0] not in _RESERVED_LABELS
    return False


def origin_from_referer(referer: str | None) -> str | None:
    parsed = urlparse(referer or "")
    if not parsed.scheme or not parsed.hostname:
        return None
    return normalize_origin(f"{parsed.scheme}://{parsed.netloc}")


def resolve_frontend_url(request=None, candidate: str | None = None) -> str:
    """Return the SPA origin the user started on, else ``FRONTEND_URL``."""
    extras: list[str | None] = []
    if request is not None:
        extras.extend(
            [
                request.GET.get("frontend_url"),
                _cookie_frontend_origin(request),
                _session_frontend_origin(request),
                request.META.get("HTTP_ORIGIN"),
                origin_from_referer(request.META.get("HTTP_REFERER")),
            ],
        )
    for raw in (candidate, *extras):
        origin = coerce_origin(raw)
        if origin and is_allowed_frontend_origin(origin):
            return origin
    return default_frontend_origin()


def sign_frontend_origin(origin: str) -> str:
    # Short label survives Google's state echo more reliably than a full URL.
    label = tenant_label_from_origin(origin) or origin
    return TimestampSigner(salt=_STATE_SALT).sign(label)


def unsign_frontend_origin(state: str | None) -> str | None:
    if not state:
        return None
    try:
        raw = TimestampSigner(salt=_STATE_SALT).unsign(state, max_age=_STATE_MAX_AGE)
    except (BadSignature, SignatureExpired, ValueError):
        return None
    return coerce_origin(raw)


def remember_frontend_origin(request, origin: str) -> None:
    session = getattr(request, "session", None)
    if session is None:
        return
    session["oauth_frontend_url"] = origin


def attach_frontend_origin_cookie(response, origin: str) -> None:
    kwargs = {
        "key": OAUTH_ORIGIN_COOKIE,
        "value": origin,
        "max_age": _STATE_MAX_AGE,
        "path": "/",
        "samesite": "Lax",
        "secure": not getattr(settings, "DEBUG", False),
        "httponly": False,
    }
    if not getattr(settings, "DEBUG", False):
        kwargs["domain"] = ".bunklogs.net"
    response.set_cookie(**kwargs)


def _cookie_frontend_origin(request) -> str | None:
    cookies = getattr(request, "COOKIES", None)
    if not isinstance(cookies, dict):
        return None
    return cookies.get(OAUTH_ORIGIN_COOKIE)


def _session_frontend_origin(request) -> str | None:
    session = getattr(request, "session", None)
    if session is None:
        return None
    try:
        return session.get("oauth_frontend_url")
    except Exception:
        return None

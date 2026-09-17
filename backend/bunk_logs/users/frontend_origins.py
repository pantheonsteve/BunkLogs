"""Allowlisted SPA origins for post-OAuth redirects.

``FRONTEND_URL`` is a single default (CLC). Tenant hosts such as
``tbe.bunklogs.net`` must send users back to the origin they started on,
or JWTs land in the wrong localStorage. Only ``*.bunklogs.net`` tenant
SPAs and local Vite are accepted — never ``admin`` / ``www`` / ``api``.
"""

from __future__ import annotations

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
    """Return an allowlisted SPA origin, else ``FRONTEND_URL``."""
    extras: list[str | None] = []
    if request is not None:
        extras.extend(
            [
                request.GET.get("frontend_url"),
                _session_frontend_origin(request),
                request.META.get("HTTP_ORIGIN"),
                origin_from_referer(request.META.get("HTTP_REFERER")),
            ],
        )
    for raw in (candidate, *extras):
        origin = normalize_origin(raw)
        if origin and is_allowed_frontend_origin(origin):
            return origin
    return default_frontend_origin()


def sign_frontend_origin(origin: str) -> str:
    return TimestampSigner(salt=_STATE_SALT).sign(origin)


def unsign_frontend_origin(state: str | None) -> str | None:
    if not state:
        return None
    try:
        return TimestampSigner(salt=_STATE_SALT).unsign(state, max_age=_STATE_MAX_AGE)
    except (BadSignature, SignatureExpired, ValueError):
        return None


def remember_frontend_origin(request, origin: str) -> None:
    session = getattr(request, "session", None)
    if session is None:
        return
    session["oauth_frontend_url"] = origin


def _session_frontend_origin(request) -> str | None:
    session = getattr(request, "session", None)
    if session is None:
        return None
    try:
        return session.get("oauth_frontend_url")
    except Exception:
        return None

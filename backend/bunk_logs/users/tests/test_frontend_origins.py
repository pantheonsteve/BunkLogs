"""Allowlisted SPA origins for Google OAuth return redirects."""

from unittest.mock import MagicMock

import pytest
from django.test import RequestFactory
from django.test import override_settings

from bunk_logs.users.frontend_origins import is_allowed_frontend_origin
from bunk_logs.users.frontend_origins import resolve_frontend_url
from bunk_logs.users.frontend_origins import sign_frontend_origin
from bunk_logs.users.frontend_origins import unsign_frontend_origin


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        ("https://clc.bunklogs.net", True),
        ("https://tbe.bunklogs.net", True),
        ("https://tbe.bunklogs.net/", True),
        ("http://localhost:5173", True),
        ("http://127.0.0.1:5174", True),
        ("https://admin.bunklogs.net", False),
        ("https://www.bunklogs.net", False),
        ("https://api.bunklogs.net", False),
        ("https://evil.example.com", False),
        ("https://tbe.bunklogs.net/phish", False),
        ("https://tbe.bunklogs.net?next=https://evil.test", False),
        ("javascript:alert(1)", False),
        ("https://clc.bunklogs.net.evil.test", False),
    ],
)
def test_is_allowed_frontend_origin(origin, allowed):
    assert is_allowed_frontend_origin(origin) is allowed


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_resolve_prefers_signed_or_query_tenant():
    rf = RequestFactory()
    request = rf.get("/api/auth/google/", {"frontend_url": "https://tbe.bunklogs.net"})
    assert resolve_frontend_url(request) == "https://tbe.bunklogs.net"


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_resolve_uses_origin_header():
    rf = RequestFactory()
    request = rf.get("/api/auth/google/", HTTP_ORIGIN="https://tbe.bunklogs.net")
    assert resolve_frontend_url(request) == "https://tbe.bunklogs.net"


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_resolve_rejects_open_redirect():
    rf = RequestFactory()
    request = rf.get(
        "/api/auth/google/",
        {"frontend_url": "https://evil.example.com"},
        HTTP_ORIGIN="https://evil.example.com",
    )
    assert resolve_frontend_url(request) == "https://clc.bunklogs.net"


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_resolve_uses_session_backup():
    rf = RequestFactory()
    request = rf.get("/api/auth/google/callback/")
    request.session = {"oauth_frontend_url": "https://tbe.bunklogs.net"}
    assert resolve_frontend_url(request) == "https://tbe.bunklogs.net"


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_resolve_uses_cookie_for_multi_org_user():
    rf = RequestFactory()
    request = rf.get("/api/auth/google/callback/")
    request.COOKIES = {"oauth_frontend_origin": "https://tbe.bunklogs.net"}
    request.session = {}
    assert resolve_frontend_url(request) == "https://tbe.bunklogs.net"


def test_sign_unsign_roundtrip():
    origin = "https://tbe.bunklogs.net"
    assert unsign_frontend_origin(sign_frontend_origin(origin)) == origin
    assert unsign_frontend_origin("tampered") is None
    assert unsign_frontend_origin(None) is None


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_resolve_prefers_explicit_candidate():
    request = MagicMock()
    request.GET = {}
    request.META = {}
    request.session = {}
    request.COOKIES = {}
    assert (
        resolve_frontend_url(request, candidate="https://tbe.bunklogs.net")
        == "https://tbe.bunklogs.net"
    )


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_resolve_accepts_tenant_slug_candidate():
    assert resolve_frontend_url(None, candidate="tbe") == "https://tbe.bunklogs.net"

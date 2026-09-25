"""Allowlisted SPA origins for Google OAuth return redirects."""

from unittest.mock import MagicMock

import pytest
from allauth.core.context import request_context
from django.test import RequestFactory
from django.test import override_settings

from bunk_logs.users.frontend_origins import is_allowed_frontend_origin
from bunk_logs.users.frontend_origins import origin_for_account_email
from bunk_logs.users.frontend_origins import resolve_frontend_url
from bunk_logs.users.frontend_origins import sign_frontend_origin
from bunk_logs.users.frontend_origins import unsign_frontend_origin
from bunk_logs.users.headless import HeadlessAdapter
from config.views import password_reset_redirect


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
    assert resolve_frontend_url(request, candidate="https://tbe.bunklogs.net") == "https://tbe.bunklogs.net"


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_resolve_accepts_tenant_slug_candidate():
    assert resolve_frontend_url(None, candidate="tbe") == "https://tbe.bunklogs.net"


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_account_email_origin_uses_request_origin_not_oauth_cookie():
    rf = RequestFactory()
    request = rf.post(
        "/_allauth/browser/v1/auth/password/reset",
        HTTP_ORIGIN="https://tbe.bunklogs.net",
    )
    request.COOKIES = {"oauth_frontend_origin": "https://clc.bunklogs.net"}
    assert origin_for_account_email(request) == "https://tbe.bunklogs.net"


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_account_email_origin_rejects_reserved_host():
    rf = RequestFactory()
    request = rf.post(
        "/_allauth/browser/v1/auth/password/reset",
        HTTP_ORIGIN="https://admin.bunklogs.net",
        HTTP_REFERER="https://evil.example.com/reset-password",
    )
    assert origin_for_account_email(request) == "https://clc.bunklogs.net"


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_account_email_origin_uses_referer_when_origin_missing():
    rf = RequestFactory()
    request = rf.post(
        "/_allauth/browser/v1/auth/password/reset",
        HTTP_REFERER="https://tbe.bunklogs.net/reset-password",
    )
    assert origin_for_account_email(request) == "https://tbe.bunklogs.net"


@override_settings(
    FRONTEND_URL="https://clc.bunklogs.net",
    HEADLESS_FRONTEND_URLS={
        "account_reset_password_from_key": ("https://clc.bunklogs.net/accounts/password/reset/key/{key}"),
    },
)
def test_headless_reset_url_uses_requesting_tenant():
    rf = RequestFactory()
    request = rf.post(
        "/_allauth/browser/v1/auth/password/reset",
        HTTP_ORIGIN="https://tbe.bunklogs.net",
    )
    with request_context(request):
        url = HeadlessAdapter().get_frontend_url(
            "account_reset_password_from_key",
            key="reset-key",
        )
    assert url == "https://tbe.bunklogs.net/accounts/password/reset/key/reset-key"


@override_settings(FRONTEND_URL="https://clc.bunklogs.net")
def test_password_reset_redirect_follows_request_origin():
    rf = RequestFactory()
    request = rf.get(
        "/accounts/password/reset/key/reset-key",
        HTTP_ORIGIN="https://tbe.bunklogs.net",
    )
    response = password_reset_redirect(request, "reset-key")
    assert response.status_code == 302
    assert response["Location"] == ("https://tbe.bunklogs.net/accounts/password/reset/key/reset-key")

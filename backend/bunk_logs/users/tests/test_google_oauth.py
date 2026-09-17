"""Google OAuth start/callback must return users to the originating SPA."""

from unittest.mock import patch
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from rest_framework.test import APIClient

from bunk_logs.users.frontend_origins import sign_frontend_origin
from bunk_logs.users.frontend_origins import unsign_frontend_origin
from bunk_logs.users.models import User


@pytest.fixture
def google_app(db):
    site = Site.objects.get_current()
    app = SocialApp.objects.create(
        provider="google",
        name="Google",
        client_id="test-google-client",
        secret="test-google-secret",
    )
    app.sites.add(site)
    return app


@pytest.mark.django_db
def test_google_login_embeds_tbe_origin_in_state(google_app):
    client = APIClient()
    response = client.get(
        "/api/auth/google/",
        {"frontend_url": "https://tbe.bunklogs.net"},
        HTTP_ORIGIN="https://tbe.bunklogs.net",
    )
    assert response.status_code == 200
    auth_url = response.data["auth_url"]
    params = parse_qs(urlparse(auth_url).query)
    assert unsign_frontend_origin(params["state"][0]) == "https://tbe.bunklogs.net"
    assert params["client_id"] == [google_app.client_id]


@pytest.mark.django_db
def test_google_login_ignores_evil_origin(google_app, settings):
    settings.FRONTEND_URL = "https://clc.bunklogs.net"
    client = APIClient()
    response = client.get(
        "/api/auth/google/",
        {"frontend_url": "https://evil.example.com"},
    )
    params = parse_qs(urlparse(response.data["auth_url"]).query)
    assert unsign_frontend_origin(params["state"][0]) == "https://clc.bunklogs.net"


@pytest.mark.django_db
def test_google_callback_error_redirects_to_tbe(google_app, settings):
    settings.FRONTEND_URL = "https://clc.bunklogs.net"
    client = APIClient()
    state = sign_frontend_origin("https://tbe.bunklogs.net")
    response = client.get(
        "/api/auth/google/callback/",
        {"error": "access_denied", "state": state},
    )
    assert response.status_code == 302
    assert response["Location"].startswith("https://tbe.bunklogs.net/signin?")
    assert "access_denied" in response["Location"]


@pytest.mark.django_db
def test_google_callback_success_redirects_to_tbe(google_app, settings):
    settings.FRONTEND_URL = "https://clc.bunklogs.net"
    user = User.objects.create_user(email="staff@tbe.test", password="pw")
    SocialAccount.objects.create(user=user, provider="google", uid="google-sub-1")
    state = sign_frontend_origin("https://tbe.bunklogs.net")

    token_payload = {"access_token": "ya29.test"}
    userinfo = {
        "sub": "google-sub-1",
        "email": "staff@tbe.test",
        "given_name": "Staff",
        "family_name": "Member",
    }
    with patch("config.views.requests.post") as mock_post, patch(
        "config.views.requests.get",
    ) as mock_get:
        mock_post.return_value.json.return_value = token_payload
        mock_get.return_value.json.return_value = userinfo
        response = APIClient().get(
            "/api/auth/google/callback/",
            {"code": "auth-code", "state": state},
        )

    assert response.status_code == 302
    location = response["Location"]
    assert location.startswith("https://tbe.bunklogs.net/auth/callback#")
    assert "access_token=" in location
    assert "refresh_token=" in location

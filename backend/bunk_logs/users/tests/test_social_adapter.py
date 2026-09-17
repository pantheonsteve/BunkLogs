"""Tests for OAuth email case-insensitive linking."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from bunk_logs.users.adapters import SocialAccountAdapter
from bunk_logs.users.models import User


@pytest.mark.django_db
class TestSocialAccountAdapter:
    def test_pre_social_login_links_existing_user_case_insensitive(self, rf):
        user = User(email="Staff@Example.com")
        user.set_unusable_password()
        user.save()

        sociallogin = MagicMock()
        sociallogin.is_existing = False
        sociallogin.account.extra_data = {"email": "staff@example.com"}
        sociallogin.user.__class__ = User

        adapter = SocialAccountAdapter()
        request = rf.get("/")
        with patch.object(sociallogin, "connect") as mock_connect:
            adapter.pre_social_login(request, sociallogin)
            mock_connect.assert_called_once_with(request, user)

    def test_login_error_url_uses_tenant_origin(self, rf, settings):
        settings.FRONTEND_URL = "https://clc.bunklogs.net"
        request = rf.get("/accounts/google/login/callback/", HTTP_ORIGIN="https://tbe.bunklogs.net")
        adapter = SocialAccountAdapter()
        url = adapter.get_login_error_url(request, "google", error="access_denied")
        assert url.startswith("https://tbe.bunklogs.net/signin?")
        assert "access_denied" in url

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

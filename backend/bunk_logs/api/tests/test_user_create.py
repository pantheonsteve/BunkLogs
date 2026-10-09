"""Public self-registration at /api/v1/users/create/."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
pytestmark = pytest.mark.django_db

PAYLOAD = {
    "email": "new-signup@example.com",
    "first_name": "New",
    "last_name": "Signup",
    "password": "a-Strong-pw-123",
}


def test_anonymous_signup_creates_user():
    r = APIClient().post("/api/v1/users/create/", PAYLOAD, format="json")
    assert r.status_code == 201, r.content
    user = User.objects.get(email=PAYLOAD["email"])
    assert user.is_active
    assert user.check_password(PAYLOAD["password"])


def test_signup_with_stale_session_skips_csrf():
    """A leftover Django session must not trigger SessionAuthentication's CSRF check."""
    existing = User.objects.create_user(email="stale@example.com", password="pw")
    api = APIClient(enforce_csrf_checks=True)
    api.force_login(existing)
    r = api.post("/api/v1/users/create/", PAYLOAD, format="json")
    assert r.status_code == 201, r.content

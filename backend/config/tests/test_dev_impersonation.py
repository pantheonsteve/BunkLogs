"""Tests for local-only dev impersonation endpoints."""

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def counselor():
    return User.objects.create_user(
        email="counselor@dev.test",
        password="pw",
        role=User.COUNSELOR,
        first_name="Casey",
        last_name="Counselor",
    )


@override_settings(DEBUG=True, DATABASES={"default": {"HOST": "postgres"}})
def test_status_enabled_when_debug_and_local_db(api):
    response = api.get("/api/dev/impersonate/status/")
    assert response.status_code == 200
    assert response.json()["enabled"] is True


@override_settings(DEBUG=False, DATABASES={"default": {"HOST": "postgres"}})
def test_status_hidden_when_debug_false(api):
    response = api.get("/api/dev/impersonate/status/")
    assert response.status_code == 404


@override_settings(DEBUG=True, DATABASES={"default": {"HOST": "prod-db.example.com"}})
def test_status_hidden_when_remote_db(api):
    response = api.get("/api/dev/impersonate/status/")
    assert response.status_code == 404


@override_settings(DEBUG=True, DATABASES={"default": {"HOST": "postgres"}})
def test_users_search_returns_matches(api, counselor):
    User.objects.create_user(
        email="unithead@dev.test",
        password="pw",
        role=User.UNIT_HEAD,
        first_name="Uma",
        last_name="Head",
    )
    response = api.get("/api/dev/impersonate/users/", {"q": "counselor"})
    assert response.status_code == 200
    emails = [row["email"] for row in response.json()["results"]]
    assert emails == ["counselor@dev.test"]


@override_settings(DEBUG=True, DATABASES={"default": {"HOST": "postgres"}})
def test_login_mints_tokens_for_user(api, counselor):
    response = api.post(
        "/api/dev/impersonate/",
        {"email": counselor.email},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access"]
    assert body["refresh"]
    assert body["user"]["email"] == counselor.email
    assert body["user"]["role"] == User.COUNSELOR


@override_settings(DEBUG=True, DATABASES={"default": {"HOST": "postgres"}})
def test_login_rejects_inactive_user(api, counselor):
    counselor.is_active = False
    counselor.save(update_fields=["is_active"])
    response = api.post(
        "/api/dev/impersonate/",
        {"user_id": str(counselor.id)},
        format="json",
    )
    assert response.status_code == 400

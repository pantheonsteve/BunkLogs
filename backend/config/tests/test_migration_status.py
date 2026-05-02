import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_migration_status_requires_authentication():
    client = APIClient()
    response = client.get("/api/migration-status/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_migration_status_forbidden_for_non_staff():
    client = APIClient()
    user = User.objects.create_user(
        email="counselor@example.com",
        password="pass12345",
        role=User.COUNSELOR,
        is_staff=False,
    )
    client.force_authenticate(user=user)
    response = client.get("/api/migration-status/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_migration_status_ok_for_staff():
    client = APIClient()
    user = User.objects.create_user(
        email="admin@example.com",
        password="pass12345",
        role=User.ADMIN,
        is_staff=True,
    )
    client.force_authenticate(user=user)
    response = client.get("/api/migration-status/")
    assert response.status_code == 200
    body = response.json()
    assert "steps" in body
    assert isinstance(body["steps"], list)


@pytest.mark.django_db
def test_migration_status_marks_1_5_complete_via_artifact_on_main():
    """1_5 inventory landed in a 1_6 commit message; artifact-based rule still marks it completed."""
    from config.migration_views import STEP_COMPLETION_ARTIFACTS
    from config.migration_views import _artifacts_satisfied_on_main

    assert "1_5" in STEP_COMPLETION_ARTIFACTS
    assert _artifacts_satisfied_on_main("1_5") is True

    client = APIClient()
    user = User.objects.create_user(
        email="admin2@example.com",
        password="pass12345",
        role=User.ADMIN,
        is_staff=True,
    )
    client.force_authenticate(user=user)
    response = client.get("/api/migration-status/")
    assert response.status_code == 200
    steps = response.json()["steps"]
    row = next((s for s in steps if s["id"] == "1_5"), None)
    assert row is not None
    assert row["status"] == "completed"

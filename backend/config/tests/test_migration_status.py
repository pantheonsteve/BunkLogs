import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from config import migration_views
from config.migration_views import STEP_COMPLETION_ARTIFACTS
from config.migration_views import _artifacts_satisfied_on_main

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
def test_migration_status_marks_1_5_complete_via_artifact_on_main(monkeypatch, tmp_path):
    """1_5 inventory landed in a 1_6 commit message; artifact-based rule still marks it completed.

    CI checkouts often do not include every ``migration_prompts/*.md`` (many are uncommitted locally);
    the API only emits rows for files present, so supply a minimal prompt file via monkeypatch.
    """
    assert "1_5" in STEP_COMPLETION_ARTIFACTS
    assert _artifacts_satisfied_on_main("1_5") is True

    (tmp_path / "1_5_inventory_dual_api_trees.md").write_text(
        "# 1.5 Dual API inventory\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(migration_views, "_migration_prompts_dir", lambda: tmp_path)

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

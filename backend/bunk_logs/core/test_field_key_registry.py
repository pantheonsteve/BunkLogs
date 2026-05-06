"""Tests for FieldKey model, API, manager scoping, and validator hints."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import FieldKey
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.validators.template_schema import check_field_key_hints

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Org A", slug="org-a-fk")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Org B", slug="org-b-fk")


@pytest.fixture
def global_key(db):
    return FieldKey.all_objects.create(
        organization=None,
        key="punctuality",
        display_name="Punctuality",
        expected_field_type="rating_group",
        expected_dashboard_role="category_ratings",
    )


@pytest.fixture
def org_a_key(org_a):
    return FieldKey.all_objects.create(
        organization=org_a,
        key="custom_metric",
        display_name="Custom Metric",
        expected_field_type="text",
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="su@example.com", password="pw")


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(email="user@example.com", password="pw")


@pytest.fixture
def admin_user(db, org_a):
    user = User.objects.create_user(email="admin@example.com", password="pw")
    person = Person.all_objects.create(organization=org_a, first_name="Admin", last_name="User", user=user)
    Membership.all_objects.create(
        program=_make_program(org_a),
        person=person,
        role="admin",
        is_active=True,
    )
    return user


def _make_program(org, slug_suffix="fk"):
    from datetime import date

    from bunk_logs.core.models import Program

    slug = f"{org.slug}-prog-{slug_suffix}"
    return Program.all_objects.get_or_create(
        organization=org,
        slug=slug,
        defaults={
            "name": f"{org.name} - Program",
            "program_type": "summer_camp",
            "start_date": date(2026, 6, 1),
            "end_date": date(2026, 8, 1),
        },
    )[0]


# ---------------------------------------------------------------------------
# Manager / org isolation tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_org_context_field_keys_empty(global_key, org_a_key):
    assert not FieldKey.objects.exists()


@pytest.mark.django_db
def test_org_sees_own_and_global_keys(org_a, global_key, org_a_key, org_b):
    org_b_key = FieldKey.all_objects.create(
        organization=org_b, key="b_only", display_name="B Only", expected_field_type="text",
    )
    with organization_context(org_a):
        keys = set(FieldKey.objects.values_list("key", flat=True))
    assert "punctuality" in keys  # global
    assert "custom_metric" in keys  # own org
    assert "b_only" not in keys  # other org excluded
    _ = org_b_key  # referenced to avoid unused-variable warning


@pytest.mark.django_db
def test_global_key_visible_across_orgs(org_a, org_b, global_key):
    with organization_context(org_a):
        assert FieldKey.objects.filter(key="punctuality").exists()
    with organization_context(org_b):
        assert FieldKey.objects.filter(key="punctuality").exists()


@pytest.mark.django_db
def test_all_objects_bypasses_scoping(org_a, global_key, org_a_key):
    assert FieldKey.all_objects.count() >= 2


@pytest.mark.django_db
def test_unique_together_org_key(org_a, org_a_key):
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        FieldKey.all_objects.create(
            organization=org_a,
            key="custom_metric",
            display_name="Duplicate",
        )


@pytest.mark.django_db
def test_unique_together_global_key(global_key):
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        FieldKey.all_objects.create(
            organization=None,
            key="punctuality",
            display_name="Duplicate Global",
        )


# ---------------------------------------------------------------------------
# check_field_key_hints (validator warning, non-blocking)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_warnings_when_types_match(org_a, global_key):
    schema = {
        "fields": [
            {
                "key": "punctuality",
                "type": "rating_group",
                "scale": [1, 5],
                "scale_labels": {"en": ["Low", "High"]},
                "categories": [{"key": "c", "labels": {"en": "C"}}],
            },
        ],
    }
    warnings = check_field_key_hints(schema, org_a)
    assert warnings == []


@pytest.mark.django_db
def test_type_mismatch_warning_surfaces(org_a, global_key):
    schema = {
        "fields": [
            {"key": "punctuality", "type": "text", "prompts": {"en": "How punctual?"}},
        ],
    }
    warnings = check_field_key_hints(schema, org_a)
    assert len(warnings) == 1
    assert "punctuality" in warnings[0]
    assert "rating_group" in warnings[0]
    assert "text" in warnings[0]


@pytest.mark.django_db
def test_unregistered_key_produces_no_warning(org_a, global_key):
    schema = {
        "fields": [
            {"key": "totally_custom", "type": "text", "prompts": {"en": "Custom"}},
        ],
    }
    warnings = check_field_key_hints(schema, org_a)
    assert warnings == []


@pytest.mark.django_db
def test_no_expected_type_produces_no_warning(org_a):
    FieldKey.all_objects.create(
        organization=org_a,
        key="notes",
        display_name="Notes",
        expected_field_type="",  # no hint set
    )
    schema = {
        "fields": [{"key": "notes", "type": "textarea", "prompts": {"en": "Notes"}}],
    }
    warnings = check_field_key_hints(schema, org_a)
    assert warnings == []


# ---------------------------------------------------------------------------
# API: FieldKeyViewSet
# ---------------------------------------------------------------------------


def _api_factory():
    return APIRequestFactory()


def _attach_org(request, org):
    request.organization = org
    return request


@pytest.mark.django_db
def test_list_authenticated_returns_own_and_global(org_a, global_key, org_a_key, regular_user):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    rf = APIRequestFactory()
    request = rf.get("/api/v1/field-keys/")
    force_authenticate(request, user=regular_user)
    _attach_org(request, org_a)

    view = FieldKeyViewSet.as_view({"get": "list"})
    response = view(request)
    assert response.status_code == 200
    keys = {item["key"] for item in response.data}
    assert "punctuality" in keys
    assert "custom_metric" in keys


@pytest.mark.django_db
def test_list_unauthenticated_returns_403(org_a, global_key):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    rf = APIRequestFactory()
    request = rf.get("/api/v1/field-keys/")
    request.organization = org_a

    view = FieldKeyViewSet.as_view({"get": "list"})
    response = view(request)
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_prefix_search_q_param(org_a, global_key, org_a_key, regular_user):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    rf = APIRequestFactory()
    request = rf.get("/api/v1/field-keys/?q=punct")
    force_authenticate(request, user=regular_user)
    _attach_org(request, org_a)

    view = FieldKeyViewSet.as_view({"get": "list"})
    response = view(request)
    assert response.status_code == 200
    keys = [item["key"] for item in response.data]
    assert keys == ["punctuality"]


@pytest.mark.django_db
def test_prefix_search_no_match_returns_empty(org_a, global_key, regular_user):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    rf = APIRequestFactory()
    request = rf.get("/api/v1/field-keys/?q=zzz")
    force_authenticate(request, user=regular_user)
    _attach_org(request, org_a)

    view = FieldKeyViewSet.as_view({"get": "list"})
    response = view(request)
    assert response.status_code == 200
    assert response.data == []


@pytest.mark.django_db
def test_org_admin_can_create_org_key(org_a, admin_user):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    rf = APIRequestFactory()
    request = rf.post(
        "/api/v1/field-keys/",
        {"key": "new_metric", "display_name": "New Metric", "expected_field_type": "text"},
        format="json",
    )
    force_authenticate(request, user=admin_user)
    _attach_org(request, org_a)

    view = FieldKeyViewSet.as_view({"post": "create"})
    with organization_context(org_a):
        response = view(request)
    assert response.status_code == 201
    assert response.data["key"] == "new_metric"
    assert response.data["is_global"] is False
    assert FieldKey.all_objects.filter(organization=org_a, key="new_metric").exists()


@pytest.mark.django_db
def test_regular_user_cannot_create_key(org_a, regular_user):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    rf = APIRequestFactory()
    request = rf.post(
        "/api/v1/field-keys/",
        {"key": "should_fail", "display_name": "Should Fail"},
        format="json",
    )
    force_authenticate(request, user=regular_user)
    _attach_org(request, org_a)

    view = FieldKeyViewSet.as_view({"post": "create"})
    with organization_context(org_a):
        response = view(request)
    assert response.status_code in (403, 404)


@pytest.mark.django_db
def test_superuser_can_patch_global_key(org_a, global_key, superuser):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    rf = APIRequestFactory()
    request = rf.patch(
        f"/api/v1/field-keys/{global_key.pk}/",
        {"display_name": "Updated Name"},
        format="json",
    )
    force_authenticate(request, user=superuser)
    _attach_org(request, org_a)

    view = FieldKeyViewSet.as_view({"patch": "partial_update"})
    with organization_context(org_a):
        response = view(request, pk=global_key.pk)
    assert response.status_code == 200
    global_key.refresh_from_db()
    assert global_key.display_name == "Updated Name"


@pytest.mark.django_db
def test_org_admin_cannot_patch_global_key(org_a, global_key, admin_user):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    rf = APIRequestFactory()
    request = rf.patch(
        f"/api/v1/field-keys/{global_key.pk}/",
        {"display_name": "Sneaky"},
        format="json",
    )
    force_authenticate(request, user=admin_user)
    _attach_org(request, org_a)

    view = FieldKeyViewSet.as_view({"patch": "partial_update"})
    with organization_context(org_a):
        response = view(request, pk=global_key.pk)
    assert response.status_code == 403


@pytest.mark.django_db
def test_delete_blocked_when_key_in_use(org_a, admin_user):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    fk = FieldKey.all_objects.create(
        organization=org_a, key="in_use_key", display_name="In Use",
    )
    ReflectionTemplate.all_objects.create(
        organization=org_a,
        name="Tpl with key",
        slug="tpl-inuse-fk",
        cadence="daily",
        schema={"fields": [{"key": "in_use_key", "type": "text", "prompts": {"en": "Q"}}]},
    )

    rf = APIRequestFactory()
    request = rf.delete(f"/api/v1/field-keys/{fk.pk}/")
    force_authenticate(request, user=admin_user)
    _attach_org(request, org_a)

    view = FieldKeyViewSet.as_view({"delete": "destroy"})
    with organization_context(org_a):
        response = view(request, pk=fk.pk)
    assert response.status_code == 409
    assert FieldKey.all_objects.filter(pk=fk.pk).exists()


@pytest.mark.django_db
def test_delete_allowed_when_key_not_in_use(org_a, admin_user):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    fk = FieldKey.all_objects.create(
        organization=org_a, key="unused_key", display_name="Unused",
    )

    rf = APIRequestFactory()
    request = rf.delete(f"/api/v1/field-keys/{fk.pk}/")
    force_authenticate(request, user=admin_user)
    _attach_org(request, org_a)

    view = FieldKeyViewSet.as_view({"delete": "destroy"})
    with organization_context(org_a):
        response = view(request, pk=fk.pk)
    assert response.status_code == 204
    assert not FieldKey.all_objects.filter(pk=fk.pk).exists()


@pytest.mark.django_db
def test_org_a_key_not_visible_to_org_b(org_a, org_b, org_a_key, regular_user):
    from bunk_logs.api.field_keys import FieldKeyViewSet

    rf = APIRequestFactory()
    request = rf.get("/api/v1/field-keys/")
    force_authenticate(request, user=regular_user)
    _attach_org(request, org_b)

    view = FieldKeyViewSet.as_view({"get": "list"})
    response = view(request)
    assert response.status_code == 200
    keys = {item["key"] for item in response.data}
    assert "custom_metric" not in keys


# ---------------------------------------------------------------------------
# Seed command
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_field_keys_command_idempotent():
    from django.core.management import call_command

    call_command("seed_field_keys", verbosity=0)
    count_after_first = FieldKey.all_objects.filter(organization__isnull=True).count()

    call_command("seed_field_keys", verbosity=0)
    count_after_second = FieldKey.all_objects.filter(organization__isnull=True).count()

    assert count_after_first == count_after_second
    assert count_after_first == 9  # 6 rating_group + wins + improvements + open_concern


@pytest.mark.django_db
def test_seed_field_keys_all_global():
    from django.core.management import call_command

    call_command("seed_field_keys", verbosity=0)
    global_keys = set(
        FieldKey.all_objects.filter(organization__isnull=True).values_list("key", flat=True),
    )
    expected = {
        "punctuality", "reliability", "communication",
        "problem_solving", "interpersonal", "initiative",
        "wins", "improvements", "open_concern",
    }
    assert expected == global_keys

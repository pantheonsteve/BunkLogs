"""Tests for the ReflectionTemplate CRUD API (/api/v1/templates/)."""
from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()

LIST_URL = "/api/v1/templates/"


def detail_url(pk):
    return f"/api/v1/templates/{pk}/"


def clone_url(pk):
    return f"/api/v1/templates/{pk}/clone/"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org():
    return Organization.objects.create(name="Crane Lake", slug="crane-lake")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="Other Camp", slug="other-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Crane Lake - Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 15),
        end_date=date(2026, 8, 15),
    )


def _make_user(email="user@example.com", superuser=False):
    if superuser:
        return User.objects.create_superuser(email=email, password="pass")
    return User.objects.create_user(email=email, password="pass")


def _make_person(org, user=None, first="Test", last="User"):
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )


def _make_membership(program, person, role="counselor"):
    return Membership.all_objects.create(program=program, person=person, role=role)


def _make_template(org, slug="tmpl", role="counselor", **kwargs):
    schema = kwargs.pop(
        "schema",
        {"fields": [{"key": "q1", "type": "text", "prompts": {"en": "Q1"}}]},
    )
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name=kwargs.pop("name", "Template"),
        slug=slug,
        cadence=kwargs.pop("cadence", "weekly"),
        role=role,
        schema=schema,
        **kwargs,
    )


def _client_for(user, org):
    """Return an APIClient pre-authenticated and pre-wired with an org header."""
    c = APIClient()
    c.force_authenticate(user=user)
    c.defaults["HTTP_HOST"] = f"{org.slug}.bunklogs.net"
    return c


# ---------------------------------------------------------------------------
# Helper: admin client
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(org, program):
    user = _make_user("admin@example.com")
    person = _make_person(org, user)
    _make_membership(program, person, role="admin")
    return user


@pytest.fixture
def admin_client(admin_user, org):
    return _client_for(admin_user, org)


@pytest.fixture
def regular_user(org, program):
    user = _make_user("regular@example.com")
    person = _make_person(org, user, first="Regular")
    _make_membership(program, person, role="counselor")
    return user


@pytest.fixture
def regular_client(regular_user, org):
    return _client_for(regular_user, org)


@pytest.fixture
def superuser():
    return _make_user("super@example.com", superuser=True)


@pytest.fixture
def superuser_client(superuser, org):
    return _client_for(superuser, org)


# ---------------------------------------------------------------------------
# List / retrieve
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplateListRetrieve:
    def test_list_requires_auth(self, org):
        c = APIClient()
        c.defaults["HTTP_HOST"] = f"{org.slug}.bunklogs.net"
        res = c.get(LIST_URL)
        assert res.status_code == 401

    def test_regular_user_can_list(self, regular_client, org):
        _make_template(org)
        res = regular_client.get(LIST_URL)
        assert res.status_code == 200
        assert len(res.data) >= 1

    def test_list_excludes_other_org_templates(self, regular_client, org, other_org):
        _make_template(org, slug="mine")
        _make_template(other_org, slug="theirs")
        res = regular_client.get(LIST_URL)
        assert res.status_code == 200
        slugs = [t["slug"] for t in res.data]
        assert "mine" in slugs
        assert "theirs" not in slugs

    def test_list_includes_global_templates_by_default(self, regular_client):
        ReflectionTemplate.all_objects.create(
            organization=None,
            name="Global T",
            slug="global-t",
            cadence="daily",
            schema={"fields": [{"key": "q", "type": "text", "prompts": {"en": "Q"}}]},
        )
        res = regular_client.get(LIST_URL)
        assert res.status_code == 200
        slugs = [t["slug"] for t in res.data]
        assert "global-t" in slugs

    def test_list_exclude_global_with_param(self, regular_client, org):
        _make_template(org, slug="local-t")
        ReflectionTemplate.all_objects.create(
            organization=None,
            name="Global T",
            slug="global-t",
            cadence="daily",
            schema={"fields": [{"key": "q", "type": "text", "prompts": {"en": "Q"}}]},
        )
        res = regular_client.get(LIST_URL + "?include_global=false")
        slugs = [t["slug"] for t in res.data]
        assert "local-t" in slugs
        assert "global-t" not in slugs

    def test_retrieve_own_org_template(self, regular_client, org):
        tpl = _make_template(org)
        res = regular_client.get(detail_url(tpl.pk))
        assert res.status_code == 200
        assert res.data["id"] == tpl.pk

    def test_retrieve_other_org_returns_404(self, regular_client, other_org):
        tpl = _make_template(other_org)
        res = regular_client.get(detail_url(tpl.pk))
        assert res.status_code == 404

    def test_is_staff_user_sees_cross_org_templates(self, org, other_org):
        """3.25: ``is_staff=True`` (no superuser) sees all orgs' templates the
        same way a Django superuser does."""
        _make_template(org, slug="mine-3-25")
        _make_template(other_org, slug="theirs-3-25")
        staff_user = User.objects.create_user(
            email="staff-tpl@example.com", password="pw", is_staff=True,
        )
        assert staff_user.is_superuser is False
        client = _client_for(staff_user, org)
        res = client.get(LIST_URL)
        assert res.status_code == 200
        slugs = [t["slug"] for t in res.data]
        assert "mine-3-25" in slugs
        assert "theirs-3-25" in slugs

    def test_filter_by_role(self, regular_client, org):
        _make_template(org, slug="counselor-t", role="counselor")
        _make_template(org, slug="kitchen-t", role="kitchen_staff")
        res = regular_client.get(LIST_URL + "?role=counselor")
        slugs = [t["slug"] for t in res.data]
        assert "counselor-t" in slugs
        assert "kitchen-t" not in slugs


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplateCreate:
    def test_regular_user_cannot_create(self, regular_client):
        payload = {
            "name": "My Template",
            "slug": "my-template",
            "cadence": "weekly",
            "schema": {"fields": [{"key": "q1", "type": "text", "prompts": {"en": "Q"}}]},
        }
        res = regular_client.post(LIST_URL, payload, format="json")
        assert res.status_code == 403

    def test_admin_can_create(self, admin_client):
        payload = {
            "name": "New Template",
            "slug": "new-template",
            "cadence": "weekly",
            "schema": {"fields": [{"key": "q1", "type": "text", "prompts": {"en": "Q"}}]},
        }
        res = admin_client.post(LIST_URL, payload, format="json")
        assert res.status_code == 201
        assert res.data["slug"] == "new-template"

    def test_create_assigns_current_org(self, admin_client, org):
        payload = {
            "name": "Org Template",
            "slug": "org-template",
            "cadence": "daily",
            "schema": {"fields": [{"key": "q1", "type": "text", "prompts": {"en": "Q"}}]},
        }
        res = admin_client.post(LIST_URL, payload, format="json")
        assert res.status_code == 201
        tpl = ReflectionTemplate.all_objects.get(pk=res.data["id"])
        assert tpl.organization_id == org.pk

    def test_empty_schema_creates_draft(self, admin_client):
        """Empty fields list is valid — creates a blank draft template."""
        payload = {
            "name": "Draft Template",
            "slug": "draft-template",
            "cadence": "daily",
            "schema": {"fields": []},
        }
        res = admin_client.post(LIST_URL, payload, format="json")
        assert res.status_code == 201

    def test_invalid_field_type_rejected(self, admin_client):
        """A schema with a populated but structurally invalid field is still rejected."""
        payload = {
            "name": "Bad Schema",
            "slug": "bad-schema",
            "cadence": "daily",
            "schema": {"fields": [{"key": "q1", "type": "not_a_real_type", "prompts": {"en": "Q"}}]},
        }
        res = admin_client.post(LIST_URL, payload, format="json")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# PATCH (versioning)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplatePatch:
    def test_patch_no_responses_edits_in_place(self, admin_client, org):
        tpl = _make_template(org, slug="edit-me")
        payload = {"name": "Updated Name"}
        res = admin_client.patch(detail_url(tpl.pk), payload, format="json")
        assert res.status_code == 200
        assert res.data["created_new_version"] is False
        assert res.data["name"] == "Updated Name"
        assert res.data["version"] == 1
        assert ReflectionTemplate.all_objects.filter(slug="edit-me").count() == 1

    def test_patch_with_responses_creates_new_version(
        self, admin_client, org, program,
    ):
        tpl = _make_template(org, slug="versioned")
        person = Person.all_objects.create(organization=org, first_name="A", last_name="B")
        Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=person,
            template=tpl,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={"q1": "hello"},
        )
        payload = {
            "schema": {
                "fields": [{"key": "q1", "type": "text", "prompts": {"en": "Updated Q"}}],
            },
        }
        res = admin_client.patch(detail_url(tpl.pk), payload, format="json")
        assert res.status_code == 201
        assert res.data["created_new_version"] is True
        assert res.data["version"] == 2
        assert res.data["parent_template"] == tpl.pk
        assert ReflectionTemplate.all_objects.filter(slug="versioned").count() == 2

    def test_patch_force_new_version_creates_version_without_responses(
        self, admin_client, org,
    ):
        tpl = _make_template(org, slug="force-version")
        payload = {"name": "Force New Version"}
        res = admin_client.patch(
            detail_url(tpl.pk) + "?force_new_version=true", payload, format="json",
        )
        assert res.status_code == 201
        assert res.data["created_new_version"] is True
        assert res.data["version"] == 2

    def test_regular_user_cannot_patch(self, regular_client, org):
        tpl = _make_template(org, slug="no-edit")
        res = regular_client.patch(detail_url(tpl.pk), {"name": "x"}, format="json")
        assert res.status_code == 403

    def test_admin_cannot_patch_other_org_template(self, admin_client, other_org):
        tpl = _make_template(other_org, slug="theirs")
        res = admin_client.patch(detail_url(tpl.pk), {"name": "x"}, format="json")
        assert res.status_code == 404

    def test_admin_cannot_patch_global_template(self, admin_client):
        tpl = ReflectionTemplate.all_objects.create(
            organization=None,
            name="Global",
            slug="global-patch-test",
            cadence="daily",
            schema={"fields": [{"key": "q", "type": "text", "prompts": {"en": "Q"}}]},
        )
        res = admin_client.patch(detail_url(tpl.pk), {"name": "x"}, format="json")
        assert res.status_code == 403

    def test_superuser_can_patch_global_template(self, superuser_client):
        tpl = ReflectionTemplate.all_objects.create(
            organization=None,
            name="Global",
            slug="global-super-patch",
            cadence="daily",
            schema={"fields": [{"key": "q", "type": "text", "prompts": {"en": "Q"}}]},
        )
        res = superuser_client.patch(detail_url(tpl.pk), {"name": "Patched"}, format="json")
        assert res.status_code == 200
        assert res.data["name"] == "Patched"


# ---------------------------------------------------------------------------
# DELETE (soft)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplateDelete:
    def test_admin_can_soft_delete_unused_template(self, admin_client, org):
        tpl = _make_template(org, slug="deletable")
        res = admin_client.delete(detail_url(tpl.pk))
        assert res.status_code == 204
        tpl.refresh_from_db()
        assert tpl.is_active is False

    def test_delete_rejected_when_reflections_exist(
        self, admin_client, org, program,
    ):
        tpl = _make_template(org, slug="in-use")
        person = Person.all_objects.create(organization=org, first_name="C", last_name="D")
        Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=person,
            template=tpl,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={"q1": "hello"},
        )
        res = admin_client.delete(detail_url(tpl.pk))
        assert res.status_code == 409

    def test_regular_user_cannot_delete(self, regular_client, org):
        tpl = _make_template(org, slug="cant-delete")
        res = regular_client.delete(detail_url(tpl.pk))
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplateClone:
    def test_admin_can_clone_global_template(self, admin_client, org):
        global_tpl = ReflectionTemplate.all_objects.create(
            organization=None,
            name="Global Clone Source",
            slug="global-clone-src",
            cadence="weekly",
            schema={"fields": [{"key": "q", "type": "text", "prompts": {"en": "Q"}}]},
        )
        res = admin_client.post(clone_url(global_tpl.pk), format="json")
        assert res.status_code == 201
        cloned = ReflectionTemplate.all_objects.get(pk=res.data["id"])
        assert cloned.organization_id == org.pk
        assert cloned.parent_template_id == global_tpl.pk
        assert cloned.is_active is False

    def test_admin_can_clone_own_org_template(self, admin_client, org):
        tpl = _make_template(org, slug="clone-base")
        res = admin_client.post(clone_url(tpl.pk), format="json")
        assert res.status_code == 201
        cloned = ReflectionTemplate.all_objects.get(pk=res.data["id"])
        assert cloned.organization_id == org.pk
        assert cloned.slug == "clone-base"
        assert cloned.version == 2

    def test_regular_user_cannot_clone(self, regular_client, org):
        tpl = _make_template(org, slug="no-clone")
        res = regular_client.post(clone_url(tpl.pk), format="json")
        assert res.status_code == 403

    def test_admin_cannot_clone_other_org_template(self, admin_client, other_org):
        tpl = _make_template(other_org, slug="other-clone")
        res = admin_client.post(clone_url(tpl.pk), format="json")
        assert res.status_code == 404

    def test_clone_carries_subject_and_assignment_settings(self, admin_client, org):
        tpl = _make_template(
            org,
            slug="clone-routing",
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
            assignment_group_types=["bunk"],
            author_role_filter=["counselor"],
            subject_role_filter=["camper"],
            subject_visible=True,
        )
        res = admin_client.post(clone_url(tpl.pk), format="json")
        assert res.status_code == 201
        cloned = ReflectionTemplate.all_objects.get(pk=res.data["id"])
        assert cloned.subject_mode == "single_subject"
        assert cloned.assignment_scope == "per_subject_in_group"
        assert cloned.assignment_group_types == ["bunk"]
        assert cloned.author_role_filter == ["counselor"]
        assert cloned.subject_role_filter == ["camper"]
        assert cloned.subject_visible is True


# ---------------------------------------------------------------------------
# Routing fields (subject_mode / assignment_scope / role filters)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplateRoutingFields:
    def test_create_with_routing_fields_round_trips(self, admin_client):
        payload = {
            "name": "Daily Camper Reflection",
            "slug": "daily-camper-reflection",
            "cadence": "daily",
            "schema": {"fields": [{"key": "q1", "type": "text", "prompts": {"en": "Q"}}]},
            "subject_mode": "single_subject",
            "assignment_scope": "per_subject_in_group",
            "assignment_group_types": ["bunk"],
            "author_role_filter": ["counselor", "junior_counselor"],
            "subject_role_filter": ["camper"],
            "subject_visible": False,
        }
        res = admin_client.post(LIST_URL, payload, format="json")
        assert res.status_code == 201, res.data
        assert res.data["subject_mode"] == "single_subject"
        assert res.data["assignment_scope"] == "per_subject_in_group"
        assert res.data["assignment_group_types"] == ["bunk"]
        assert res.data["author_role_filter"] == ["counselor", "junior_counselor"]
        assert res.data["subject_role_filter"] == ["camper"]
        assert res.data["subject_visible"] is False

    def test_create_rejects_incoherent_subject_mode(self, admin_client):
        # subject_mode='self' must have assignment_scope='none'
        payload = {
            "name": "Bad Routing",
            "slug": "bad-routing",
            "cadence": "weekly",
            "schema": {"fields": []},
            "subject_mode": "self",
            "assignment_scope": "per_subject_in_group",
            "assignment_group_types": ["bunk"],
        }
        res = admin_client.post(LIST_URL, payload, format="json")
        assert res.status_code == 400
        assert "assignment_scope" in res.data

    def test_create_rejects_unknown_role_filter(self, admin_client):
        payload = {
            "name": "Bad Role Filter",
            "slug": "bad-role-filter",
            "cadence": "weekly",
            "schema": {"fields": []},
            "author_role_filter": ["not_a_role"],
        }
        res = admin_client.post(LIST_URL, payload, format="json")
        assert res.status_code == 400
        assert "author_role_filter" in res.data

    def test_patch_routing_fields_edits_in_place(self, admin_client, org):
        tpl = _make_template(org, slug="routing-edit")
        payload = {
            "subject_mode": "single_subject",
            "assignment_scope": "per_subject_in_group",
            "assignment_group_types": ["bunk"],
            "author_role_filter": ["counselor"],
            "subject_role_filter": ["camper"],
            "subject_visible": True,
            "supports_privacy": True,
        }
        res = admin_client.patch(detail_url(tpl.pk), payload, format="json")
        assert res.status_code == 200, res.data
        tpl.refresh_from_db()
        assert tpl.subject_mode == "single_subject"
        assert tpl.assignment_scope == "per_subject_in_group"
        assert tpl.assignment_group_types == ["bunk"]
        assert tpl.author_role_filter == ["counselor"]
        assert tpl.subject_role_filter == ["camper"]
        assert tpl.subject_visible is True
        assert tpl.supports_privacy is True
        assert res.data["supports_privacy"] is True

    def test_patch_with_responses_propagates_routing_fields_to_new_version(
        self, admin_client, org, program,
    ):
        tpl = _make_template(
            org,
            slug="routing-version",
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
            assignment_group_types=["bunk"],
        )
        person = Person.all_objects.create(organization=org, first_name="A", last_name="B")
        Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=person,
            template=tpl,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={"q1": "hello"},
        )
        # Edit only the role filter; subject_mode/scope/group_types must propagate.
        res = admin_client.patch(
            detail_url(tpl.pk),
            {"author_role_filter": ["counselor", "junior_counselor"]},
            format="json",
        )
        assert res.status_code == 201, res.data
        new_tpl = ReflectionTemplate.all_objects.get(pk=res.data["id"])
        assert new_tpl.subject_mode == "single_subject"
        assert new_tpl.assignment_scope == "per_subject_in_group"
        assert new_tpl.assignment_group_types == ["bunk"]
        assert new_tpl.author_role_filter == ["counselor", "junior_counselor"]


# ---------------------------------------------------------------------------
# Cross-org isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCrossOrgIsolation:
    def test_list_does_not_leak_other_org_templates(
        self, admin_client, org, other_org,
    ):
        _make_template(org, slug="ours")
        _make_template(other_org, slug="theirs")
        res = admin_client.get(LIST_URL)
        slugs = [t["slug"] for t in res.data]
        assert "ours" in slugs
        assert "theirs" not in slugs

    def test_superuser_sees_all_templates(self, superuser_client, org, other_org):
        _make_template(org, slug="org-a-tmpl")
        _make_template(other_org, slug="org-b-tmpl")
        res = superuser_client.get(LIST_URL)
        slugs = [t["slug"] for t in res.data]
        assert "org-a-tmpl" in slugs
        assert "org-b-tmpl" in slugs

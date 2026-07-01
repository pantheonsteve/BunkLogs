"""Tests for Step 7_12 PR B — LT template builder, assignments, responses.

Lean per CLAUDE.md: one happy + one auth + one edge per endpoint.
Reuses LT auth fixtures from ``test_leadership_team_endpoints.py`` via
parameterised, file-local copies so we don't import across test modules
(pytest doesn't share fixtures across files unless they live in
``conftest.py`` — these test the same surface but at a different layer).
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="LT Templates Camp", slug="lt-templates-camp",
        settings={"rollover_hour": 0, "timezone": "UTC"},
    )


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="LT Templates Camp Summer 2026",
        slug="lt-templates-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def builder_user():
    """The user who manages templates/assignments. Admin capability (the
    builder surface is admin-only after the consolidation)."""
    return User.objects.create_user(email="builder@lt.test", password="pw")


@pytest.fixture
def builder_membership(program, org, builder_user):
    person = Person.all_objects.create(
        organization=org, first_name="Site", last_name="Admin", user=builder_user,
    )
    return Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )


@pytest.fixture
def lt_user():
    """A genuine Leadership Team user. After the consolidation LT no longer
    has builder access, so this fixture is used to assert 403s."""
    return User.objects.create_user(email="ltb@lt.test", password="pw")


@pytest.fixture
def lt_membership(program, org, lt_user):
    person = Person.all_objects.create(
        organization=org, first_name="Mira", last_name="Cohen", user=lt_user,
    )
    return Membership.all_objects.create(
        program=program, person=person, role="leadership_team", is_active=True,
    )


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


# ---------------------------------------------------------------------------
# Template builder
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_template_list_requires_lt_membership(org, program):
    """Non-LT users get 403."""
    user = User.objects.create_user(email="non-lt@lt.test", password="pw")
    Person.all_objects.create(
        organization=org, first_name="Nobody", last_name="X", user=user,
    )
    c = _client(user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/templates/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_template_create_draft_then_publish(org, builder_membership, builder_user):
    """Create -> default status=draft. Publish -> status=published + is_active."""
    c = _client(builder_user, org)
    payload = {
        "name": "Kitchen Daily Pulse",
        "slug": f"kitchen-daily-{date.today().isoformat()}",
        "cadence": "daily",
        "role": "kitchen_staff",
        "schema": {
            "fields": [
                {
                    "key": "morale",
                    "type": "single_rating",
                    "scale": [1, 5],
                    "scale_labels": {
                        "en": ["Worst", "Bad", "OK", "Good", "Great"],
                    },
                    "prompts": {"en": "How was morale?"},
                },
                {
                    "key": "notes",
                    "type": "textarea",
                    "prompts": {"en": "Anything to flag?"},
                },
            ],
        },
        "languages": ["en"],
        "subject_mode": "self",
        "author_role_filter": ["kitchen_staff"],
    }
    with organization_context(org):
        create_resp = c.post(
            "/api/v1/leadership-team/templates/", data=payload, format="json",
        )
    assert create_resp.status_code == 201, create_resp.data
    body = create_resp.json()
    assert body["status"] == "draft"
    assert body["is_active"] is False
    tpl_id = body["id"]

    with organization_context(org):
        pub_resp = c.post(
            f"/api/v1/leadership-team/templates/{tpl_id}/publish/",
            data={}, format="json",
        )
    assert pub_resp.status_code == 200, pub_resp.data
    pub_body = pub_resp.json()
    assert pub_body["status"] == "published"
    assert pub_body["is_active"] is True


@pytest.mark.django_db
def test_template_publish_missing_prompt_returns_409(org, builder_membership, builder_user):
    """Publish must reject schemas missing required-language prompts."""
    c = _client(builder_user, org)
    payload = {
        "name": "Bad Template",
        "slug": "bad-template",
        "cadence": "daily",
        "schema": {
            "fields": [
                {
                    "key": "missing",
                    "type": "single_rating",
                    "scale": [1, 5],
                    "prompts": {},
                },
            ],
        },
        "languages": ["en"],
        "subject_mode": "self",
    }
    with organization_context(org):
        create_resp = c.post(
            "/api/v1/leadership-team/templates/", data=payload, format="json",
        )
    assert create_resp.status_code in (201, 400)
    if create_resp.status_code == 400:
        return
    tpl_id = create_resp.json()["id"]
    with organization_context(org):
        pub_resp = c.post(
            f"/api/v1/leadership-team/templates/{tpl_id}/publish/",
            data={}, format="json",
        )
    assert pub_resp.status_code == 409
    warnings = pub_resp.json().get("warnings") or []
    assert any(w.get("code") in {"missing_prompt", "schema"} for w in warnings)


@pytest.mark.django_db
def test_template_patch_with_responses_creates_new_version(
    org, program, builder_membership, builder_user,
):
    """PATCH on a template that has Reflection rows bumps version + 1 (draft)."""
    tpl = ReflectionTemplate.all_objects.create(
        organization=org, name="Versioned", slug="versioned-tpl",
        cadence="daily",
        schema={"fields": [{"key": "x", "type": "textarea", "prompts": {"en": "x?"}}]},
        languages=["en"], subject_mode="self",
        status=ReflectionTemplate.Status.PUBLISHED, is_active=True, version=1,
    )
    Person.all_objects.create(
        organization=org, first_name="R", last_name="R",
    )
    Reflection.all_objects.create(
        organization=org, program=program, template=tpl,
        period_start=date.today(), period_end=date.today(),
        answers={"x": "y"}, is_complete=True,
    )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/leadership-team/templates/{tpl.id}/",
            data={"description": "edited"}, format="json",
        )
    assert resp.status_code == 201, resp.data
    body = resp.json()
    assert body["created_new_version"] is True
    assert body["version"] == 2
    assert body["status"] == "draft"


@pytest.mark.django_db
def test_template_clone_creates_new_draft(org, builder_membership, builder_user):
    """Clone produces a new draft owned by viewer's org, version bump only."""
    global_tpl = ReflectionTemplate.all_objects.create(
        organization=None, name="Global", slug="global-tpl",
        cadence="daily",
        schema={"fields": [{"key": "x", "type": "textarea", "prompts": {"en": "x?"}}]},
        languages=["en"], subject_mode="self",
        status=ReflectionTemplate.Status.PUBLISHED, is_active=True, version=1,
    )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.post(
            f"/api/v1/leadership-team/templates/{global_tpl.id}/clone/",
            data={}, format="json",
        )
    assert resp.status_code == 201, resp.data
    body = resp.json()
    assert body["status"] == "draft"
    assert body["organization"] == org.id


@pytest.mark.django_db
def test_template_archive_marks_archived(org, builder_membership, builder_user):
    """Archive transitions published -> archived (is_active=False)."""
    tpl = ReflectionTemplate.all_objects.create(
        organization=org, name="Archive Me", slug="archive-me",
        cadence="daily",
        schema={"fields": [{"key": "x", "type": "textarea", "prompts": {"en": "x?"}}]},
        languages=["en"], subject_mode="self",
        status=ReflectionTemplate.Status.PUBLISHED, is_active=True, version=1,
    )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.post(
            f"/api/v1/leadership-team/templates/{tpl.id}/archive/",
            data={}, format="json",
        )
    assert resp.status_code == 200, resp.data
    body = resp.json()
    assert body["status"] == "archived"
    assert body["is_active"] is False


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------


@pytest.fixture
def published_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Assignable", slug="assignable-tpl",
        cadence="daily", role="kitchen_staff",
        schema={"fields": [{"key": "x", "type": "textarea", "prompts": {"en": "x?"}}]},
        languages=["en"], subject_mode="self",
        author_role_filter=["kitchen_staff"],
        status=ReflectionTemplate.Status.PUBLISHED, is_active=True, version=1,
    )


@pytest.mark.django_db
def test_assignment_create_role_target(
    org, program, builder_membership, builder_user, published_template,
):
    c = _client(builder_user, org)
    today = date.today()
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": published_template.id,
                "target_type": "role",
                "target_payload": {"role": "kitchen_staff"},
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=14)).isoformat(),
            },
            format="json",
        )
    assert resp.status_code == 201, resp.data
    body = resp.json()
    assert body["target_type"] == "role"
    assert body["status"] == "scheduled"


@pytest.mark.django_db
def test_assignment_conflict_requires_resolution(
    org, program, builder_membership, builder_user, published_template,
):
    c = _client(builder_user, org)
    today = date.today()
    TemplateAssignment.all_objects.create(
        organization=org, program=program, template=published_template,
        target_type="role",
        target_payload={"role": "kitchen_staff"},
        start_date=today,
        end_date=today + timedelta(days=14),
        status=TemplateAssignment.Status.SCHEDULED,
        created_by=builder_membership,
    )
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": published_template.id,
                "target_type": "role",
                "target_payload": {"role": "kitchen_staff"},
                "start_date": (today + timedelta(days=7)).isoformat(),
                "end_date": (today + timedelta(days=21)).isoformat(),
            },
            format="json",
        )
    assert resp.status_code == 409
    body = resp.json()
    assert body["choices"]
    assert body["conflicts"]


@pytest.mark.django_db
def test_assignment_conflict_replace_ends_prior(
    org, program, builder_membership, builder_user, published_template,
):
    c = _client(builder_user, org)
    today = date.today()
    prior = TemplateAssignment.all_objects.create(
        organization=org, program=program, template=published_template,
        target_type="role",
        target_payload={"role": "kitchen_staff"},
        start_date=today,
        end_date=today + timedelta(days=14),
        status=TemplateAssignment.Status.SCHEDULED,
        created_by=builder_membership,
    )
    new_start = today + timedelta(days=7)
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": published_template.id,
                "target_type": "role",
                "target_payload": {"role": "kitchen_staff"},
                "start_date": new_start.isoformat(),
                "end_date": (today + timedelta(days=28)).isoformat(),
                "conflict_resolution": "replace",
            },
            format="json",
        )
    assert resp.status_code == 201
    prior.refresh_from_db()
    assert prior.end_date == new_start - timedelta(days=1)
    assert prior.status == "ended"


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_responses_individual_tab(
    org, program, builder_membership, builder_user, published_template,
):
    person = Person.all_objects.create(
        organization=org, first_name="Author", last_name="One",
    )
    Membership.all_objects.create(
        program=program, person=person, role="kitchen_staff", is_active=True,
    )
    Reflection.all_objects.create(
        organization=org, program=program, template=published_template,
        author=person, subject=person,
        period_start=date.today(), period_end=date.today(),
        answers={"x": "value-a"}, is_complete=True,
    )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/leadership-team/templates/{published_template.id}/responses/",
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tab"] == "individual"
    assert body["total"] == 1
    assert body["results"]
    row = body["results"][0]
    assert row["author"]["name"] == "Author One"
    assert row["subject"]["name"] == "Author One"


@pytest.mark.django_db
def test_responses_aggregate_tab(
    org, program, builder_membership, builder_user,
):
    tpl = ReflectionTemplate.all_objects.create(
        organization=org, name="Scored", slug="scored-tpl",
        cadence="daily",
        schema={
            "fields": [
                {
                    "key": "morale",
                    "type": "single_rating",
                    "scale": [1, 5],
                    "scale_labels": {
                        "en": ["Worst", "Bad", "OK", "Good", "Great"],
                    },
                    "prompts": {"en": "morale?"},
                },
            ],
        },
        languages=["en"], subject_mode="self",
        status=ReflectionTemplate.Status.PUBLISHED, is_active=True, version=1,
    )
    person = Person.all_objects.create(
        organization=org, first_name="A", last_name="B",
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    for v in (3, 4, 5):
        Reflection.all_objects.create(
            organization=org, program=program, template=tpl,
            author=person, subject=person,
            period_start=date.today(), period_end=date.today(),
            answers={"morale": v}, is_complete=True,
        )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/leadership-team/templates/{tpl.id}/responses/?tab=aggregate",
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tab"] == "aggregate"
    assert body["total_responses"] == 3
    dim = next(
        (d for d in body["avg_rating_per_dimension"] if d["key"] == "morale"), None,
    )
    assert dim is not None
    assert dim["count"] == 3
    assert dim["avg"] == pytest.approx(4.0)
    assert dim["scale_max"] == 5
    assert dim["distribution"]["3"] == 1
    assert dim["distribution"]["4"] == 1
    assert dim["distribution"]["5"] == 1
    assert body["avg_rating_over_time"]
    assert body["avg_rating_over_time"][0]["avg"] == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_template_responses_export_individual_csv(
    org, program, builder_membership, builder_user, published_template,
):
    person = Person.all_objects.create(
        organization=org, first_name="Ex", last_name="Porter",
    )
    Membership.all_objects.create(
        program=program, person=person, role="kitchen_staff", is_active=True,
    )
    Reflection.all_objects.create(
        organization=org, program=program, template=published_template,
        author=person, subject=person,
        period_start=date.today(), period_end=date.today(),
        answers={"x": "csv-row"}, is_complete=True,
    )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/leadership-team/templates/{published_template.id}/responses/export/",
        )
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    body = resp.content.decode()
    assert "reflection_id" in body
    assert "csv-row" in body


# ---------------------------------------------------------------------------
# Admin access (viewer_or_403 must accept admin capability — decision FA7)
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user():
    return User.objects.create_user(email="admin@lt.test", password="pw")


@pytest.fixture
def admin_membership(program, org, admin_user):
    person = Person.all_objects.create(
        organization=org, first_name="Site", last_name="Admin", user=admin_user,
    )
    return Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )


@pytest.mark.django_db
def test_admin_can_list_templates(org, program, admin_membership, admin_user):
    """Admin membership (capability='admin') may list LT templates."""
    c = _client(admin_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/templates/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_can_view_responses(
    org, program, admin_membership, admin_user, published_template,
):
    """Admin membership may read the responses endpoint for a template."""
    c = _client(admin_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/leadership-team/templates/{published_template.id}/responses/",
        )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_superuser_without_admin_membership_can_list_templates(org, program):
    """A Django super admin (is_staff/is_superuser) always has admin access.

    Regression: previously ``admin_only_or_403`` required an active
    ``admin``-capability Membership, so a superuser with none (or one that
    got deactivated when its session ended) hit "You do not have LT access".
    """
    user = User.objects.create_user(
        email="super@lt.test", password="pw", is_staff=True, is_superuser=True,
    )
    Person.all_objects.create(
        organization=org, first_name="Super", last_name="User", user=user,
    )
    c = _client(user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/templates/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_superuser_with_deactivated_admin_membership_can_list_templates(
    org, program,
):
    """Even when the only admin membership sits in an ended (inactive) session."""
    user = User.objects.create_user(
        email="super2@lt.test", password="pw", is_staff=True, is_superuser=True,
    )
    person = Person.all_objects.create(
        organization=org, first_name="Super", last_name="Two", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=False,
    )
    c = _client(user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/templates/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_non_lt_non_admin_still_gets_403(org, program):
    """A counselor (no admin/program_lead capability) is still blocked."""
    user = User.objects.create_user(email="counselor@lt.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Regular", last_name="Counselor", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    c = _client(user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/templates/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_lt_can_no_longer_create_templates(org, lt_membership, lt_user):
    """Consolidation: LT (program_lead) lost builder write access → 403.

    The builder surface is admin-only now; LT keeps dashboards / team views /
    self-reflection elsewhere but cannot create or edit templates.
    """
    c = _client(lt_user, org)
    payload = {
        "name": "LT Attempt",
        "slug": f"lt-attempt-{date.today().isoformat()}",
        "cadence": "daily",
        "schema": {
            "fields": [{"key": "x", "type": "textarea", "prompts": {"en": "x?"}}],
        },
        "languages": ["en"],
        "subject_mode": "self",
    }
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/templates/", data=payload, format="json",
        )
    assert resp.status_code == 403, resp.data


# ---------------------------------------------------------------------------
# Unpublish endpoint (published → draft, no responses)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unpublish_published_template_succeeds(org, builder_membership, builder_user, published_template):
    """POST /unpublish/ on a published template with no responses → draft."""
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.post(f"/api/v1/leadership-team/templates/{published_template.id}/unpublish/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "draft"
    assert body["is_active"] is False


@pytest.mark.django_db
def test_unpublish_draft_template_rejected(org, builder_membership, builder_user):
    """POST /unpublish/ on a draft returns 400."""
    tpl = ReflectionTemplate.all_objects.create(
        organization=org, name="Still Draft", slug="still-draft-unp",
        cadence="daily",
        schema={"fields": [{"key": "x", "type": "text", "prompts": {"en": "x?"}}]},
        languages=["en"], subject_mode="self",
        status=ReflectionTemplate.Status.DRAFT, is_active=False, version=1,
    )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.post(f"/api/v1/leadership-team/templates/{tpl.id}/unpublish/")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_unpublish_with_responses_rejected(org, program, builder_membership, builder_user, published_template):
    """POST /unpublish/ when responses exist returns 400 — archive instead."""
    person = Person.all_objects.create(organization=org, first_name="A", last_name="B")
    Reflection.all_objects.create(
        organization=org, program=program, template=published_template,
        author=person, subject=person,
        period_start=date.today(), period_end=date.today(),
        answers={"x": "hi"}, is_complete=True,
    )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.post(f"/api/v1/leadership-team/templates/{published_template.id}/unpublish/")
    assert resp.status_code == 400
    assert "archive" in str(resp.data).lower() or "response" in str(resp.data).lower()


# ---------------------------------------------------------------------------
# DELETE endpoint (no responses — any status)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_draft_template_succeeds(org, builder_membership, builder_user):
    """DELETE on a draft with no responses returns 204 and removes the row."""
    tpl = ReflectionTemplate.all_objects.create(
        organization=org, name="To Be Deleted", slug="to-be-deleted",
        cadence="daily",
        schema={"fields": [{"key": "x", "type": "text", "prompts": {"en": "x?"}}]},
        languages=["en"], subject_mode="self",
        status=ReflectionTemplate.Status.DRAFT, is_active=False, version=1,
    )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.delete(f"/api/v1/leadership-team/templates/{tpl.id}/")
    assert resp.status_code == 204
    assert not ReflectionTemplate.all_objects.filter(pk=tpl.id).exists()


@pytest.mark.django_db
def test_delete_published_template_succeeds_when_no_responses(
    org, builder_membership, builder_user, published_template,
):
    """DELETE on a published template with no responses permanently removes it."""
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.delete(f"/api/v1/leadership-team/templates/{published_template.id}/")
    assert resp.status_code == 204
    assert not ReflectionTemplate.all_objects.filter(pk=published_template.id).exists()


@pytest.mark.django_db
def test_delete_archived_template_succeeds_when_no_responses(org, builder_membership, builder_user):
    """DELETE on an archived template with no responses permanently removes it."""
    tpl = ReflectionTemplate.all_objects.create(
        organization=org, name="Archived Empty", slug="archived-empty",
        cadence="daily",
        schema={"fields": [{"key": "x", "type": "text", "prompts": {"en": "x?"}}]},
        languages=["en"], subject_mode="self",
        status=ReflectionTemplate.Status.ARCHIVED, is_active=False, version=1,
    )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.delete(f"/api/v1/leadership-team/templates/{tpl.id}/")
    assert resp.status_code == 204
    assert not ReflectionTemplate.all_objects.filter(pk=tpl.id).exists()


@pytest.mark.django_db
def test_delete_draft_with_responses_rejected(org, program, builder_membership, builder_user):
    """DELETE on a draft that already has responses returns 400."""
    tpl = ReflectionTemplate.all_objects.create(
        organization=org, name="Has Responses", slug="has-responses-del",
        cadence="daily",
        schema={"fields": [{"key": "x", "type": "text", "prompts": {"en": "x?"}}]},
        languages=["en"], subject_mode="self",
        status=ReflectionTemplate.Status.DRAFT, is_active=False, version=1,
    )
    person = Person.all_objects.create(organization=org, first_name="R", last_name="P")
    Reflection.all_objects.create(
        organization=org, program=program, template=tpl,
        author=person, subject=person,
        period_start=date.today(), period_end=date.today(),
        answers={"x": "hi"}, is_complete=True,
    )
    c = _client(builder_user, org)
    with organization_context(org):
        resp = c.delete(f"/api/v1/leadership-team/templates/{tpl.id}/")
    assert resp.status_code == 400

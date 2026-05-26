"""Tests for Step 7_20: TemplateAssignment extension.

Covers:
- Model persistence for new fields
- resolve_members for all target types (including regression on existing ones)
- API: POST/PATCH/GET with new fields, permission checks (LT, Admin, UH → 403)
- Conflict detection for assignment_group target type
"""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.api.leadership_team.assignments import resolve_members
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()

TODAY = date(2026, 6, 15)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


# ---------------------------------------------------------------------------
# Base fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="Assignments Camp", slug="assignments-camp",
        settings={"rollover_hour": 0, "timezone": "UTC"},
    )


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Assignments Camp Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def lt_user():
    return User.objects.create_user(email="lt@assign.test", password="pw")


@pytest.fixture
def lt_membership(program, org, lt_user):
    person = Person.all_objects.create(
        organization=org, first_name="LT", last_name="Lead", user=lt_user,
    )
    return Membership.all_objects.create(
        program=program, person=person, role="leadership_team", is_active=True,
    )


@pytest.fixture
def admin_user():
    return User.objects.create_user(email="admin@assign.test", password="pw")


@pytest.fixture
def admin_membership(program, org, admin_user):
    person = Person.all_objects.create(
        organization=org, first_name="Org", last_name="Admin", user=admin_user,
    )
    return Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )


@pytest.fixture
def uh_user():
    return User.objects.create_user(email="uh@assign.test", password="pw")


@pytest.fixture
def uh_membership(program, org, uh_user):
    person = Person.all_objects.create(
        organization=org, first_name="Unit", last_name="Head", user=uh_user,
    )
    return Membership.all_objects.create(
        program=program, person=person, role="unit_head", is_active=True,
    )


@pytest.fixture
def published_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Counselor Daily",
        slug="counselor-daily-assign",
        cadence="daily",
        role="counselor",
        schema={"fields": [{"key": "x", "type": "textarea", "prompts": {"en": "x?"}}]},
        languages=["en"],
        subject_mode="self",
        author_role_filter=["counselor"],
        status=ReflectionTemplate.Status.PUBLISHED,
        is_active=True,
        version=1,
    )


@pytest.fixture
def bunk(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Bunk A", slug="bunk-a", group_type="bunk",
    )


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_new_fields_persist(org, program, lt_membership, bunk, published_template):
    """assignment_group FK, is_required=False, and title round-trip through the ORM."""
    assignment = TemplateAssignment.all_objects.create(
        organization=org,
        program=program,
        template=published_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk,
        is_required=False,
        title="Daily Bunk Log",
        start_date=date(2026, 6, 1),
        created_by=lt_membership,
    )
    assignment.refresh_from_db()
    assert assignment.assignment_group_id == bunk.pk
    assert assignment.is_required is False
    assert assignment.title == "Daily Bunk Log"
    assert assignment.target_type == "assignment_group"


# ---------------------------------------------------------------------------
# resolve_members tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_members_assignment_group(
    org, program, lt_membership, bunk, published_template,
):
    """assignment_group target resolves to Memberships with matching role + AGM author."""
    counselor_person = Person.all_objects.create(
        organization=org, first_name="C1", last_name="Smith",
    )
    counselor_mb = Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=counselor_person, role_in_group="author", is_active=True,
    )
    # Non-author in the same bunk — should NOT appear.
    camper_person = Person.all_objects.create(
        organization=org, first_name="Camper", last_name="Jones",
    )
    Membership.all_objects.create(
        program=program, person=camper_person, role="camper", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=camper_person, role_in_group="subject", is_active=True,
    )

    assignment = TemplateAssignment.all_objects.create(
        organization=org, program=program, template=published_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk,
        start_date=date(2026, 6, 1), created_by=lt_membership,
    )
    result = list(resolve_members(assignment, as_of=TODAY))
    assert len(result) == 1
    assert result[0].pk == counselor_mb.pk


@pytest.mark.django_db
def test_resolve_members_assignment_group_empty_author_role_filter(
    org, program, lt_membership, bunk,
):
    """Empty author_role_filter → base.none() (cannot resolve without role constraint)."""
    template_no_filter = ReflectionTemplate.all_objects.create(
        organization=org, name="No Filter", slug="no-filter",
        cadence="daily",
        schema={"fields": [{"key": "x", "type": "textarea", "prompts": {"en": "x?"}}]},
        languages=["en"], subject_mode="self",
        author_role_filter=[],
        status=ReflectionTemplate.Status.PUBLISHED, is_active=True, version=1,
    )
    assignment = TemplateAssignment.all_objects.create(
        organization=org, program=program, template=template_no_filter,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk,
        start_date=date(2026, 6, 1), created_by=lt_membership,
    )
    assert resolve_members(assignment, as_of=TODAY).count() == 0


@pytest.mark.django_db
def test_resolve_members_assignment_group_no_active_authors(
    org, program, lt_membership, bunk, published_template,
):
    """No active AGM authors in the group → empty queryset."""
    person = Person.all_objects.create(
        organization=org, first_name="C", last_name="Gone",
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=person, role_in_group="author", is_active=False,
    )
    assignment = TemplateAssignment.all_objects.create(
        organization=org, program=program, template=published_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk,
        start_date=date(2026, 6, 1), created_by=lt_membership,
    )
    assert resolve_members(assignment, as_of=TODAY).count() == 0


@pytest.mark.django_db
def test_resolve_members_role_regression(
    org, program, lt_membership, published_template,
):
    """role target type still resolves correctly (regression check)."""
    person = Person.all_objects.create(
        organization=org, first_name="R", last_name="Role",
    )
    mb = Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    assignment = TemplateAssignment.all_objects.create(
        organization=org, program=program, template=published_template,
        target_type=TemplateAssignment.TargetType.ROLE,
        target_payload={"role": "counselor"},
        start_date=date(2026, 6, 1), created_by=lt_membership,
    )
    result = list(resolve_members(assignment, as_of=TODAY))
    assert any(r.pk == mb.pk for r in result)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_assignment_group_as_lt(
    org, program, lt_membership, lt_user, bunk, published_template,
):
    """LT user can POST an assignment_group assignment → 201."""
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": published_template.id,
                "target_type": "assignment_group",
                "assignment_group": bunk.id,
                "target_payload": {},
                "start_date": "2026-06-01",
                "end_date": "2026-08-31",
                "is_required": False,
                "title": "Daily Bunk Log",
            },
            format="json",
        )
    assert resp.status_code == 201, resp.data
    body = resp.json()
    assert body["target_type"] == "assignment_group"
    assert body["assignment_group"] == bunk.id
    assert body["is_required"] is False
    assert body["title"] == "Daily Bunk Log"
    assert body["display_title"] == "Daily Bunk Log"


@pytest.mark.django_db
def test_post_assignment_group_as_admin(
    org, program, admin_membership, admin_user, bunk, published_template,
):
    """Admin capability can POST assignments (FA7 widening) → 201."""
    c = _client(admin_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": published_template.id,
                "target_type": "assignment_group",
                "assignment_group": bunk.id,
                "target_payload": {},
                "start_date": "2026-06-01",
            },
            format="json",
        )
    assert resp.status_code == 201, resp.data


@pytest.mark.django_db
def test_post_assignment_group_as_uh_is_403(
    org, program, uh_membership, uh_user, bunk, published_template,
):
    """UH (supervisor capability) cannot POST assignments → 403."""
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": published_template.id,
                "target_type": "assignment_group",
                "assignment_group": bunk.id,
                "target_payload": {},
                "start_date": "2026-06-01",
            },
            format="json",
        )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_post_assignment_group_without_group_id_is_400(
    org, program, lt_membership, lt_user, published_template,
):
    """target_type='assignment_group' without assignment_group → 400."""
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": published_template.id,
                "target_type": "assignment_group",
                "target_payload": {},
                "start_date": "2026-06-01",
            },
            format="json",
        )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_post_assignment_group_with_role_target_type_is_400(
    org, program, lt_membership, lt_user, bunk, published_template,
):
    """Supplying assignment_group when target_type='role' → 400."""
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": published_template.id,
                "target_type": "role",
                "target_payload": {"role": "counselor"},
                "assignment_group": bunk.id,
                "start_date": "2026-06-01",
            },
            format="json",
        )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_patch_title_and_is_required(
    org, program, lt_membership, lt_user, bunk, published_template,
):
    """PATCH title and is_required on an assignment with no responses → 200."""
    assignment = TemplateAssignment.all_objects.create(
        organization=org, program=program, template=published_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk,
        is_required=True,
        title="",
        start_date=date(2026, 6, 1), created_by=lt_membership,
    )
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/leadership-team/assignments/{assignment.id}/",
            data={"title": "Renamed", "is_required": False},
            format="json",
        )
    assert resp.status_code == 200, resp.data
    body = resp.json()
    assert body["title"] == "Renamed"
    assert body["is_required"] is False


@pytest.mark.django_db
def test_patch_assignment_group_is_400(
    org, program, lt_membership, lt_user, bunk, published_template,
):
    """PATCH assignment_group is immutable post-creation → 400."""
    assignment = TemplateAssignment.all_objects.create(
        organization=org, program=program, template=published_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk,
        start_date=date(2026, 6, 1), created_by=lt_membership,
    )
    other_bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Bunk B", slug="bunk-b", group_type="bunk",
    )
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/leadership-team/assignments/{assignment.id}/",
            data={"assignment_group": other_bunk.id},
            format="json",
        )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_get_list_includes_new_fields(
    org, program, lt_membership, lt_user, bunk, published_template,
):
    """GET list response includes assignment_group, is_required, title, display_title."""
    TemplateAssignment.all_objects.create(
        organization=org, program=program, template=published_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk, is_required=False, title="My Title",
        start_date=date(2026, 6, 1), created_by=lt_membership,
    )
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/assignments/")
    assert resp.status_code == 200
    assignments = resp.json()["assignments"]
    assert assignments
    a = assignments[0]
    assert "assignment_group" in a
    assert "is_required" in a
    assert "title" in a
    assert "display_title" in a
    assert a["display_title"] == "My Title"
    # The LT UI uses ``assignment_group_name`` to render a human label
    # in the "Current assignments" / Unassign list without a second
    # lookup.
    assert a.get("assignment_group_name") == bunk.name


@pytest.mark.django_db
def test_display_title_falls_back_to_template_name(
    org, program, lt_membership, lt_user, bunk, published_template,
):
    """display_title falls back to template.name when title is blank."""
    TemplateAssignment.all_objects.create(
        organization=org, program=program, template=published_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk, is_required=True, title="",
        start_date=date(2026, 6, 1), created_by=lt_membership,
    )
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/assignments/")
    a = resp.json()["assignments"][0]
    assert a["display_title"] == published_template.name


@pytest.mark.django_db
def test_conflict_detection_assignment_group(
    org, program, lt_membership, lt_user, bunk, published_template,
):
    """Two overlapping assignment_group assignments on the same bunk → 409."""
    TemplateAssignment.all_objects.create(
        organization=org, program=program, template=published_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk,
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
        status=TemplateAssignment.Status.SCHEDULED,
        created_by=lt_membership,
    )
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": published_template.id,
                "target_type": "assignment_group",
                "assignment_group": bunk.id,
                "target_payload": {},
                "start_date": "2026-07-01",
                "end_date": "2026-08-31",
            },
            format="json",
        )
    assert resp.status_code == 409
    body = resp.json()
    assert body["conflicts"]
    assert body["choices"]

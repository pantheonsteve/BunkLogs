"""Org role list, group-type author access, and placement supervision."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision
from bunk_logs.core.org_config import DEFAULT_GROUP_TYPE_CONFIG
from bunk_logs.testing import SEASON_END
from bunk_logs.testing import SEASON_START

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug):
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Roles Camp", slug="roles-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Roles Camp Season",
        slug="roles-season",
        program_type="summer_camp",
        start_date=SEASON_START,
        end_date=SEASON_END,
    )


@pytest.fixture
def admin_user(org, program):
    user = User.objects.create_user(email="admin-roles@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ada", last_name="Admin", user=user, email=user.email,
    )
    Membership.all_objects.create(program=program, person=person, role="admin", is_active=True)
    return user


def test_people_payload_includes_resolved_config(api, org, program, admin_user):
    api.force_authenticate(user=admin_user)
    with organization_context(org):
        response = api.get("/api/v1/admin/people/", **_hdr(org.slug))
    assert response.status_code == 200
    body = response.json()
    assert "admin" in body["enabled_roles"]
    assert body["group_type_config"]["bunk"]["members"] == DEFAULT_GROUP_TYPE_CONFIG["bunk"]["members"]


def test_disabling_a_role_with_active_members_is_rejected(api, org, program, admin_user):
    counselor = Person.all_objects.create(
        organization=org, first_name="Cam", last_name="Counselor",
    )
    Membership.all_objects.create(
        program=program, person=counselor, role="counselor", is_active=True,
    )
    api.force_authenticate(user=admin_user)
    with organization_context(org):
        response = api.patch(
            "/api/v1/admin/settings/",
            {"settings": {"roles": ["admin"]}},
            format="json",
            **_hdr(org.slug),
        )
    assert response.status_code == 400
    assert "1 active person" in response.json()["detail"]
    org.refresh_from_db()
    assert "roles" not in (org.settings or {})


def test_explicit_role_list_rejects_a_turned_off_role(api, org, program, admin_user):
    org.settings = {"roles": ["admin", "camper"]}
    org.save(update_fields=["settings"])
    api.force_authenticate(user=admin_user)
    with organization_context(org):
        response = api.post(
            "/api/v1/admin/people/",
            {
                "first_name": "New",
                "last_name": "Counselor",
                "membership": {"program_id": program.id, "role": "counselor"},
            },
            format="json",
            **_hdr(org.slug),
        )
    assert response.status_code == 400
    assert "turned off" in response.json()["detail"]


def test_adding_a_supervising_member_creates_and_removal_end_dates(
    api, org, program, admin_user,
):
    head = Person.all_objects.create(
        organization=org, first_name="Una", last_name="Head",
    )
    Membership.all_objects.create(
        program=program, person=head, role="unit_head", is_active=True,
    )
    unit = AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Upper", slug="upper", group_type="unit", is_active=True,
    )
    api.force_authenticate(user=admin_user)
    with organization_context(org):
        created = api.post(
            f"/api/v1/assignment-groups/{unit.id}/memberships/",
            {"person_id": head.id, "role_in_group": "author"},
            format="json",
            **_hdr(org.slug),
        )
    assert created.status_code == 201, created.content
    row = Supervision.all_objects.get()
    assert row.target_type == "assignment_group"
    assert row.target_group_id == unit.id
    assert row.end_date is None

    membership_id = created.json()["id"]
    with organization_context(org):
        removed = api.delete(
            f"/api/v1/assignment-groups/{unit.id}/memberships/{membership_id}/",
            **_hdr(org.slug),
        )
    assert removed.status_code == 204
    row.refresh_from_db()
    assert row.end_date is not None


def test_configured_author_can_open_the_group_dashboard_and_others_cannot(
    api, org, program,
):
    bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program,
        name="Bunk 1", slug="bunk-1", group_type="bunk", is_active=True,
    )
    org.settings = {
        "group_types": {
            "bunk": {
                "enabled": True,
                "members": [
                    {"role": "specialist", "placed_as": "author", "supervises_group": False},
                    {"role": "camper", "placed_as": "subject", "supervises_group": False},
                ],
            },
        },
    }
    org.save(update_fields=["settings"])

    def viewer(role, email):
        user = User.objects.create_user(email=email, password="pw")
        person = Person.all_objects.create(
            organization=org, first_name=role, last_name="Viewer", user=user, email=email,
        )
        Membership.all_objects.create(
            program=program, person=person, role=role, is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=person, role_in_group="author", is_active=True,
        )
        return user

    specialist = viewer("specialist", "spec-roles@example.com")
    kitchen = viewer("kitchen_staff", "kitchen-roles@example.com")
    url = f"/api/v1/dashboards/group/{bunk.id}/"

    api.force_authenticate(user=specialist)
    with organization_context(org):
        allowed = api.get(url, **_hdr(org.slug))
    assert allowed.status_code == 200, allowed.content
    assert allowed.json()["role_context"]["role"] == "counselor"

    api.force_authenticate(user=kitchen)
    with organization_context(org):
        denied = api.get(url, **_hdr(org.slug))
    assert denied.status_code == 403

"""Tests for write endpoints on /api/v1/assignment-groups/."""
from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()


def _hdr(slug):
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Write API Org", slug="write-api-org")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Write API Org B", slug="write-api-org-b")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Write API Org Summer",
        slug="write-api-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def program_b(org_b):
    return Program.all_objects.create(
        organization=org_b,
        name="Write API Org B Summer",
        slug="write-api-summer-b",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def regular_user(org, program):
    u = User.objects.create_user(email="regular@write-api.com", password="pw")
    p = Person.all_objects.create(organization=org, first_name="Regular", last_name="User", user=u)
    Membership.all_objects.create(program=program, person=p, role="counselor", is_active=True)
    return u, p


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="admin@write-api.com", password="pw")
    p = Person.all_objects.create(organization=org, first_name="Admin", last_name="User", user=u)
    Membership.all_objects.create(program=program, person=p, role="admin", is_active=True)
    return u, p


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="super@write-api.com", password="pw")


@pytest.fixture
def group(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk Alpha",
        slug="bunk-alpha-write",
        group_type="bunk",
    )


@pytest.fixture
def person_a(org):
    return Person.all_objects.create(organization=org, first_name="Person", last_name="Alpha")


@pytest.fixture
def person_b(org_b):
    return Person.all_objects.create(organization=org_b, first_name="Person", last_name="Beta")


# ---------------------------------------------------------------------------
# CREATE group
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCreateGroup:
    def test_admin_can_create(self, client, org, program, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.post(
            "/api/v1/assignment-groups/",
            {"name": "Bunk Bravo", "group_type": "bunk", "program": program.pk, "slug": "bunk-bravo-write"},
            **_hdr(org.slug),
        )
        assert r.status_code == 201
        assert AssignmentGroup.all_objects.filter(slug="bunk-bravo-write").exists()

    def test_regular_user_denied(self, client, org, program, regular_user):
        user, _ = regular_user
        client.force_authenticate(user=user)
        r = client.post(
            "/api/v1/assignment-groups/",
            {"name": "Bunk Bravo", "group_type": "bunk", "program": program.pk, "slug": "bunk-bravo-2"},
            **_hdr(org.slug),
        )
        assert r.status_code == 403

    def test_superuser_can_create(self, client, org, program, superuser):
        client.force_authenticate(user=superuser)
        r = client.post(
            "/api/v1/assignment-groups/",
            {"name": "Bunk Charlie", "group_type": "bunk", "program": program.pk, "slug": "bunk-charlie-write"},
            **_hdr(org.slug),
        )
        assert r.status_code == 201

    def test_cross_org_program_rejected(self, client, org, program_b, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.post(
            "/api/v1/assignment-groups/",
            {"name": "Bunk X", "group_type": "bunk", "program": program_b.pk, "slug": "bunk-x"},
            **_hdr(org.slug),
        )
        assert r.status_code in (400, 403)


# ---------------------------------------------------------------------------
# UPDATE group
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUpdateGroup:
    def test_admin_can_patch(self, client, org, group, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.patch(
            f"/api/v1/assignment-groups/{group.pk}/",
            {"name": "Bunk Alpha Renamed"},
            **_hdr(org.slug),
        )
        assert r.status_code == 200
        group.refresh_from_db()
        assert group.name == "Bunk Alpha Renamed"

    def test_regular_user_denied(self, client, org, group, regular_user):
        user, _ = regular_user
        client.force_authenticate(user=user)
        r = client.patch(
            f"/api/v1/assignment-groups/{group.pk}/",
            {"name": "Sneaky Rename"},
            **_hdr(org.slug),
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# DELETE (soft) group
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDeleteGroup:
    def test_admin_soft_deletes(self, client, org, group, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.delete(f"/api/v1/assignment-groups/{group.pk}/", **_hdr(org.slug))
        assert r.status_code == 204
        group.refresh_from_db()
        assert not group.is_active

    def test_delete_blocked_when_reflections_exist(self, client, org, program, group, admin_user):
        user, _ = admin_user
        Person.all_objects.create(organization=org, first_name="Subject", last_name="Test")
        template = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Test Template",
            slug="test-tmpl-del",
            cadence="weekly",
            program_type="summer_camp",
            schema={"fields": [{"key": "q1", "type": "text", "label": {"en": "Q"}}]},
        )
        Reflection.all_objects.create(
            organization=org,
            program=program,
            template=template,
            assignment_group=group,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={"q1": "answer"},
        )
        client.force_authenticate(user=user)
        r = client.delete(f"/api/v1/assignment-groups/{group.pk}/", **_hdr(org.slug))
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# ADD membership
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAddMembership:
    def test_admin_adds_member(self, client, org, group, admin_user, person_a):
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.post(
            f"/api/v1/assignment-groups/{group.pk}/memberships/",
            {"person_id": person_a.pk, "role_in_group": "subject"},
            **_hdr(org.slug),
        )
        assert r.status_code in (200, 201)
        assert AssignmentGroupMembership.all_objects.filter(group=group, person=person_a, role_in_group="subject").exists()

    def test_cross_org_person_rejected(self, client, org, group, admin_user, person_b):
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.post(
            f"/api/v1/assignment-groups/{group.pk}/memberships/",
            {"person_id": person_b.pk, "role_in_group": "subject"},
            **_hdr(org.slug),
        )
        assert r.status_code == 400

    def test_regular_user_denied(self, client, org, group, regular_user, person_a):
        user, _ = regular_user
        client.force_authenticate(user=user)
        r = client.post(
            f"/api/v1/assignment-groups/{group.pk}/memberships/",
            {"person_id": person_a.pk, "role_in_group": "subject"},
            **_hdr(org.slug),
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# REMOVE membership
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRemoveMembership:
    def test_admin_soft_removes(self, client, org, group, admin_user, person_a):
        membership = AssignmentGroupMembership.all_objects.create(
            group=group, person=person_a, role_in_group="subject", is_active=True,
        )
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.delete(
            f"/api/v1/assignment-groups/{group.pk}/memberships/{membership.pk}/",
            **_hdr(org.slug),
        )
        assert r.status_code == 204
        membership.refresh_from_db()
        assert not membership.is_active

    def test_hard_delete_with_flag(self, client, org, group, admin_user, person_a):
        membership = AssignmentGroupMembership.all_objects.create(
            group=group, person=person_a, role_in_group="subject", is_active=True,
        )
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.delete(
            f"/api/v1/assignment-groups/{group.pk}/memberships/{membership.pk}/?hard=true",
            **_hdr(org.slug),
        )
        assert r.status_code == 204
        assert not AssignmentGroupMembership.all_objects.filter(pk=membership.pk).exists()

    def test_cross_group_membership_not_found(self, client, org, org_b, program_b, admin_user):
        group_other = AssignmentGroup.all_objects.create(
            organization=org_b, program=program_b, name="Other", slug="other-grp-remove", group_type="bunk",
        )
        person_other = Person.all_objects.create(organization=org_b, first_name="Other", last_name="Person")
        membership = AssignmentGroupMembership.all_objects.create(
            group=group_other, person=person_other, role_in_group="subject", is_active=True,
        )
        user, _ = admin_user
        client.force_authenticate(user=user)
        # Try to access a membership on a different org's group via our org's group
        my_group = AssignmentGroup.all_objects.create(
            organization=org, program=Program.all_objects.filter(organization=org).first(),
            name="My Group", slug="my-grp-remove", group_type="bunk",
        )
        r = client.delete(
            f"/api/v1/assignment-groups/{my_group.pk}/memberships/{membership.pk}/",
            **_hdr(org.slug),
        )
        assert r.status_code == 404

"""Tests for write endpoints on /api/v1/assignment-groups/."""
from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
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

    def test_admin_can_create_without_slug(self, client, org, program, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.post(
            "/api/v1/assignment-groups/",
            {"name": "Bunk Delta", "group_type": "bunk", "program": program.pk},
            **_hdr(org.slug),
        )
        assert r.status_code == 201, r.content
        created = AssignmentGroup.all_objects.get(program=program, name="Bunk Delta")
        assert created.slug == "bunk-delta"

    def test_admin_can_create_team_group(self, client, org, program, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.post(
            "/api/v1/assignment-groups/",
            {
                "name": "Kitchen Staff",
                "group_type": "team",
                "program": program.pk,
                "slug": "kitchen-staff-team",
            },
            **_hdr(org.slug),
        )
        assert r.status_code == 201, r.content
        created = AssignmentGroup.all_objects.get(slug="kitchen-staff-team")
        assert created.group_type == "team"

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

    def test_create_auto_suffixes_duplicate_slug(self, client, org, program, group, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.post(
            "/api/v1/assignment-groups/",
            {
                "name": "Bunk Maple Again",
                "group_type": "bunk",
                "program": program.pk,
                "slug": group.slug,
            },
            **_hdr(org.slug),
        )
        assert r.status_code == 201, r.content
        created = AssignmentGroup.all_objects.get(program=program, slug=f"{group.slug}-2")
        assert created.name == "Bunk Maple Again"


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

    def test_list_includes_program_name_and_filters_by_program_id(
        self, client, org, program, admin_user,
    ):
        program2 = Program.all_objects.create(
            organization=org,
            name="Write API Org Session 2",
            slug="write-api-session-2",
            program_type="summer_camp",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 31),
        )
        AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Bunk Maple",
            slug="bunk-maple-s1", group_type="bunk",
        )
        AssignmentGroup.all_objects.create(
            organization=org, program=program2, name="Bunk Maple",
            slug="bunk-maple-s2", group_type="bunk",
        )
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.get("/api/v1/assignment-groups/", **_hdr(org.slug))
        assert r.status_code == 200
        payload = r.json()
        rows = payload["results"] if isinstance(payload, dict) else payload
        names = {row["program_name"] for row in rows}
        assert "Write API Org Summer" in names
        assert "Write API Org Session 2" in names

        r2 = client.get(
            "/api/v1/assignment-groups/",
            {"program": str(program2.id)},
            **_hdr(org.slug),
        )
        assert r2.status_code == 200
        payload2 = r2.json()
        rows2 = payload2["results"] if isinstance(payload2, dict) else payload2
        assert len(rows2) == 1
        row = rows2[0]
        assert row["name"] == "Bunk Maple"
        assert row["program_name"] == "Write API Org Session 2"


# ---------------------------------------------------------------------------
# CLONE group
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCloneGroup:
    def test_admin_clones_team_with_roster_and_program_memberships(
        self, client, org, program, admin_user,
    ):
        program2 = Program.all_objects.create(
            organization=org,
            name="Write API Org Session 2",
            slug="write-api-session-2-clone",
            program_type="summer_camp",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 31),
        )
        team = AssignmentGroup.all_objects.create(
            organization=org,
            program=program,
            name="Kitchen Staff",
            slug="kitchen-staff-clone",
            group_type="team",
        )
        person1 = Person.all_objects.create(organization=org, first_name="Kit", last_name="Chen")
        person2 = Person.all_objects.create(organization=org, first_name="Sam", last_name="Lee")
        Membership.all_objects.create(
            program=program, person=person1, role="kitchen_staff", is_active=True,
        )
        Membership.all_objects.create(
            program=program, person=person2, role="kitchen_staff", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=team, person=person1, role_in_group="author", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=team, person=person2, role_in_group="author", is_active=True,
        )

        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.post(
            f"/api/v1/assignment-groups/{team.pk}/clone/",
            {"target_program": program2.pk},
            **_hdr(org.slug),
        )
        assert r.status_code == 201, r.content
        data = r.json()
        assert data["name"] == "Kitchen Staff"
        assert data["program"] == program2.pk
        assert data["clone_summary"]["memberships_copied"] == 2
        assert data["clone_summary"]["program_memberships_copied"] == 2
        assert len(data["memberships"]) == 2

        cloned = AssignmentGroup.all_objects.get(pk=data["id"])
        assert cloned.program_id == program2.pk
        assert cloned.slug == "kitchen-staff-clone"
        assert AssignmentGroupMembership.all_objects.filter(
            group=cloned, is_active=True,
        ).count() == 2
        assert Membership.all_objects.filter(
            program=program2, role="kitchen_staff", is_active=True,
        ).count() == 2

    def test_regular_user_denied(self, client, org, program, group, regular_user):
        program2 = Program.all_objects.create(
            organization=org,
            name="Write API Org Session 2",
            slug="session-2-clone-denied",
            program_type="summer_camp",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 31),
        )
        user, _ = regular_user
        client.force_authenticate(user=user)
        r = client.post(
            f"/api/v1/assignment-groups/{group.pk}/clone/",
            {"target_program": program2.pk},
            **_hdr(org.slug),
        )
        assert r.status_code == 403

    def test_same_program_and_cross_org_rejected(
        self, client, org, org_b, program, program_b, group, admin_user,
    ):
        user, _ = admin_user
        client.force_authenticate(user=user)

        r_same = client.post(
            f"/api/v1/assignment-groups/{group.pk}/clone/",
            {"target_program": program.pk},
            **_hdr(org.slug),
        )
        assert r_same.status_code == 400
        assert "target_program" in r_same.json()

        r_cross = client.post(
            f"/api/v1/assignment-groups/{group.pk}/clone/",
            {"target_program": program_b.pk},
            **_hdr(org.slug),
        )
        assert r_cross.status_code == 400
        assert "target_program" in r_cross.json()


GROUPS_CSV = """name,group_type,parent_name,parent_group_type,is_active
Upper Camp,division,,,true
Sophomores,unit,Upper Camp,division,true
Bunk Maple,bunk,Sophomores,unit,true
"""


def _groups_csv_file(content: str = GROUPS_CSV) -> SimpleUploadedFile:
    return SimpleUploadedFile("groups.csv", content.encode("utf-8"), content_type="text/csv")


class TestAssignmentGroupBulkImport:
    def test_preview_and_commit_create_hierarchy(self, client, org, program, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)

        preview = client.post(
            "/api/v1/assignment-groups/bulk-import/",
            {
                "program": program.pk,
                "mode": "preview",
                "file": _groups_csv_file(),
            },
            format="multipart",
            **_hdr(org.slug),
        )
        assert preview.status_code == 200, preview.json()
        assert preview.json()["valid"] is True
        assert preview.json()["row_count"] == 3
        assert AssignmentGroup.all_objects.filter(program=program).count() == 0

        commit = client.post(
            "/api/v1/assignment-groups/bulk-import/",
            {
                "program": program.pk,
                "mode": "commit",
                "file": _groups_csv_file(),
            },
            format="multipart",
            **_hdr(org.slug),
        )
        assert commit.status_code == 200
        summary = commit.json()["summary"]
        assert summary["groups_created"] == 3
        assert summary["parents_linked"] == 2

        bunk = AssignmentGroup.all_objects.get(program=program, slug="bunk-maple")
        unit = AssignmentGroup.all_objects.get(program=program, slug="sophomores")
        division = AssignmentGroup.all_objects.get(program=program, slug="upper-camp")
        assert bunk.parent_id == unit.pk
        assert unit.parent_id == division.pk

    def test_reimport_is_idempotent(self, client, org, program, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)
        client.post(
            "/api/v1/assignment-groups/bulk-import/",
            {
                "program": program.pk,
                "mode": "commit",
                "file": _groups_csv_file(),
            },
            format="multipart",
            **_hdr(org.slug),
        )
        second = client.post(
            "/api/v1/assignment-groups/bulk-import/",
            {
                "program": program.pk,
                "mode": "commit",
                "file": _groups_csv_file(),
            },
            format="multipart",
            **_hdr(org.slug),
        )
        assert second.status_code == 200
        assert second.json()["summary"]["groups_created"] == 0

    def test_non_admin_forbidden(self, client, org, program, regular_user):
        user, _ = regular_user
        client.force_authenticate(user=user)
        r = client.post(
            "/api/v1/assignment-groups/bulk-import/",
            {
                "program": program.pk,
                "mode": "preview",
                "file": _groups_csv_file(),
            },
            format="multipart",
            **_hdr(org.slug),
        )
        assert r.status_code == 403

    def test_import_template_download(self, client, org, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)
        r = client.get("/api/v1/assignment-groups/import-template/", **_hdr(org.slug))
        assert r.status_code == 200
        assert "text/csv" in r["Content-Type"]
        assert "name,group_type" in r.content.decode("utf-8")

    def test_invalid_csv_returns_errors(self, client, org, program, admin_user):
        user, _ = admin_user
        client.force_authenticate(user=user)
        bad_csv = "name,group_type\n,bunk\n"
        r = client.post(
            "/api/v1/assignment-groups/bulk-import/",
            {
                "program": program.pk,
                "mode": "preview",
                "file": _groups_csv_file(bad_csv),
            },
            format="multipart",
            **_hdr(org.slug),
        )
        assert r.status_code == 400
        assert r.json()["valid"] is False
        assert r.json()["errors"]


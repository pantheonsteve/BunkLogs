"""Tests for GET /api/v1/assignment-groups/ endpoint."""
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
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()


def _hdr(slug):
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def org(db):
    return Organization.objects.create(name="AG API Org", slug="ag-api-org")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="AG API Org B", slug="ag-api-org-b")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="AG API Org Summer",
        slug="ag-api-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def program_b(org_b):
    return Program.all_objects.create(
        organization=org_b,
        name="AG API Org B Summer",
        slug="ag-api-summer-b",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def staff_user(org, program):
    u = User.objects.create_user(email="staff@ag-api.com", password="pw")
    p = Person.all_objects.create(organization=org, first_name="Staff", last_name="User", user=u)
    Membership.all_objects.create(program=program, person=p, role="counselor", is_active=True)
    return u, p


@pytest.fixture
def group_maple(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Maple", slug="bunk-maple-ag",
        group_type="bunk",
    )


@pytest.fixture
def group_oak(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Oak", slug="bunk-oak-ag",
        group_type="bunk",
    )


@pytest.fixture
def group_other_org(org_b, program_b):
    return AssignmentGroup.all_objects.create(
        organization=org_b, program=program_b, name="Other Org Bunk", slug="other-bunk",
        group_type="bunk",
    )


# ---------------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_requires_auth(api, org, group_maple):
    r = api.get("/api/v1/assignment-groups/", **_hdr(org.slug))
    assert r.status_code == 401


@pytest.mark.django_db
def test_list_requires_org_header(api, org, staff_user, group_maple):
    user, _ = staff_user
    api.force_authenticate(user=user)
    r = api.get("/api/v1/assignment-groups/")
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_list_returns_org_groups(api, org, staff_user, group_maple, group_oak, group_other_org):
    user, _ = staff_user
    api.force_authenticate(user=user)
    r = api.get("/api/v1/assignment-groups/", **_hdr(org.slug))
    assert r.status_code == 200
    ids = {g["id"] for g in r.json()}
    assert group_maple.pk in ids
    assert group_oak.pk in ids
    assert group_other_org.pk not in ids


@pytest.mark.django_db
def test_list_filter_by_group_type(api, org, program, staff_user, group_maple, group_oak):
    unit = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Unit Alef", slug="unit-alef-ag", group_type="unit",
    )
    user, _ = staff_user
    api.force_authenticate(user=user)
    r = api.get("/api/v1/assignment-groups/", {"group_type": "bunk"}, **_hdr(org.slug))
    assert r.status_code == 200
    ids = {g["id"] for g in r.json()}
    assert group_maple.pk in ids
    assert group_oak.pk in ids
    assert unit.pk not in ids


@pytest.mark.django_db
def test_list_filter_by_program(api, org, org_b, program, program_b, staff_user, group_maple):
    grp_b = AssignmentGroup.all_objects.create(
        organization=org_b, program=program_b, name="Other", slug="other-prog", group_type="bunk",
    )
    user, _ = staff_user
    api.force_authenticate(user=user)
    r = api.get("/api/v1/assignment-groups/", {"program": program.slug}, **_hdr(org.slug))
    assert r.status_code == 200
    ids = {g["id"] for g in r.json()}
    assert group_maple.pk in ids
    assert grp_b.pk not in ids


@pytest.mark.django_db
def test_detail_includes_memberships(api, org, program, staff_user, group_maple):
    u2 = User.objects.create_user(email="camper@ag-api.com", password="pw")
    camper = Person.all_objects.create(organization=org, first_name="Kid", last_name="Camper", user=u2)
    AssignmentGroupMembership.all_objects.create(
        group=group_maple, person=camper, role_in_group="subject",
    )
    user, _ = staff_user
    api.force_authenticate(user=user)
    r = api.get(f"/api/v1/assignment-groups/{group_maple.pk}/", **_hdr(org.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == group_maple.pk
    assert len(body["memberships"]) == 1
    assert body["memberships"][0]["role_in_group"] == "subject"


@pytest.mark.django_db
def test_subjects_action(api, org, program, staff_user, group_maple):
    u_c = User.objects.create_user(email="cns-ag@ag-api.com", password="pw")
    counselor = Person.all_objects.create(organization=org, first_name="Cns", last_name="Ag", user=u_c)
    u_s = User.objects.create_user(email="sub-ag@ag-api.com", password="pw")
    subject_p = Person.all_objects.create(organization=org, first_name="Sub", last_name="Ag", user=u_s)
    AssignmentGroupMembership.all_objects.create(group=group_maple, person=counselor, role_in_group="author")
    AssignmentGroupMembership.all_objects.create(group=group_maple, person=subject_p, role_in_group="subject")

    user, _ = staff_user
    api.force_authenticate(user=user)
    r = api.get(f"/api/v1/assignment-groups/{group_maple.pk}/subjects/", **_hdr(org.slug))
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert subject_p.pk in ids
    assert counselor.pk not in ids


@pytest.mark.django_db
def test_authors_action(api, org, program, staff_user, group_maple):
    u_c = User.objects.create_user(email="cns-ag2@ag-api.com", password="pw")
    counselor = Person.all_objects.create(organization=org, first_name="Cns2", last_name="Ag", user=u_c)
    u_s = User.objects.create_user(email="sub-ag2@ag-api.com", password="pw")
    subject_p = Person.all_objects.create(organization=org, first_name="Sub2", last_name="Ag", user=u_s)
    AssignmentGroupMembership.all_objects.create(group=group_maple, person=counselor, role_in_group="author")
    AssignmentGroupMembership.all_objects.create(group=group_maple, person=subject_p, role_in_group="subject")

    user, _ = staff_user
    api.force_authenticate(user=user)
    r = api.get(f"/api/v1/assignment-groups/{group_maple.pk}/authors/", **_hdr(org.slug))
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert counselor.pk in ids
    assert subject_p.pk not in ids


@pytest.mark.django_db
def test_include_descendants_param(api, org, program, staff_user):
    parent = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Unit Parent", slug="unit-parent", group_type="unit",
    )
    child = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk Child", slug="bunk-child", group_type="bunk",
        parent=parent,
    )
    grandchild = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk GrandChild", slug="bunk-gc", group_type="bunk",
        parent=child,
    )
    user, _ = staff_user
    api.force_authenticate(user=user)
    r = api.get(
        "/api/v1/assignment-groups/",
        {"parent": str(parent.pk), "include_descendants": "true"},
        **_hdr(org.slug),
    )
    assert r.status_code == 200
    ids = {g["id"] for g in r.json()}
    assert parent.pk in ids
    assert child.pk in ids
    assert grandchild.pk in ids


@pytest.mark.django_db
def test_cross_org_group_not_accessible(api, org, org_b, staff_user, group_other_org):
    user, _ = staff_user
    api.force_authenticate(user=user)
    r = api.get(f"/api/v1/assignment-groups/{group_other_org.pk}/", **_hdr(org.slug))
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Reflection API: new fields and filters
# ---------------------------------------------------------------------------


@pytest.fixture
def self_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Self Tpl AG",
        slug="self-tpl-ag",
        cadence="weekly",
        schema={"fields": [{"key": "note", "type": "text", "prompts": {"en": "Note"}}]},
    )


@pytest.mark.django_db
def test_reflection_response_includes_new_fields(api, org, program, staff_user, self_template, group_maple):
    user, _person = staff_user
    api.force_authenticate(user=user)
    resp = api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program.slug,
            "template": self_template.id,
            "period_start": "2026-07-01",
            "period_end": "2026-07-07",
            "answers": {"note": "test"},
            "language": "en",
        },
        format="json",
        **_hdr(org.slug),
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert "subject" in body
    assert "author" in body
    assert "submission_id" in body
    assert "assignment_group" in body
    assert "subject_group" in body


@pytest.mark.django_db
def test_reflection_filter_by_subject(api, org, program, staff_user, self_template):
    user, person = staff_user
    api.force_authenticate(user=user)
    api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program.slug,
            "template": self_template.id,
            "period_start": "2026-07-01",
            "period_end": "2026-07-07",
            "answers": {"note": "subject filter"},
            "language": "en",
        },
        format="json",
        **_hdr(org.slug),
    )
    r = api.get(
        "/api/v1/reflections/",
        {"subject": str(person.pk)},
        **_hdr(org.slug),
    )
    assert r.status_code == 200
    assert len(r.json()) == 1

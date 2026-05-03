from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

User = get_user_model()


def _hdr_org(slug: str):
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Mem Org A", slug="mem-org-a")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Mem Org B", slug="mem-org-b")


@pytest.fixture
def program_a(org_a):
    return Program.all_objects.create(
        organization=org_a,
        name="Mem Org A Summer",
        slug="prog-mem-a",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def program_b(org_b):
    return Program.all_objects.create(
        organization=org_b,
        name="Mem Org B Summer",
        slug="prog-mem-b",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def admin_user(org_a, program_a):
    u = User.objects.create_user(email="memadmin@example.com", password="pw")
    p = Person.all_objects.create(organization=org_a, first_name="Ada", last_name="Min", user=u)
    Membership.all_objects.create(program=program_a, person=p, role="admin", is_active=True)
    return u, p


@pytest.fixture
def counselor_user(org_a, program_a):
    u = User.objects.create_user(email="memcns@example.com", password="pw")
    p = Person.all_objects.create(organization=org_a, first_name="Cas", last_name="Cee", user=u)
    Membership.all_objects.create(program=program_a, person=p, role="counselor", is_active=True)
    return u, p


def _make_member(org, program, *, first="Mem", last="Ber", role="counselor", tags=None):
    p = Person.all_objects.create(organization=org, first_name=first, last_name=last)
    m = Membership.all_objects.create(
        program=program,
        person=p,
        role=role,
        is_active=True,
        tags=tags or [],
    )
    return p, m


@pytest.mark.django_db
def test_admin_can_list_memberships_in_program(api, org_a, program_a, admin_user):
    user, _ = admin_user
    _make_member(org_a, program_a, last="Alpha")
    _make_member(org_a, program_a, last="Beta")
    api.force_authenticate(user=user)
    resp = api.get(
        "/api/v1/memberships/",
        {"program": program_a.slug},
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200, resp.content
    body = resp.json()
    items = body if isinstance(body, list) else body.get("results", body)
    assert len(items) >= 3


@pytest.mark.django_db
def test_non_admin_cannot_list(api, org_a, counselor_user):
    user, _ = counselor_user
    api.force_authenticate(user=user)
    resp = api.get("/api/v1/memberships/", **_hdr_org(org_a.slug))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_can_patch_tags(api, org_a, program_a, admin_user):
    user, _ = admin_user
    _, m = _make_member(org_a, program_a)
    api.force_authenticate(user=user)
    resp = api.patch(
        f"/api/v1/memberships/{m.id}/",
        {"tags": ["International", "Waterfront"]},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200, resp.content
    m.refresh_from_db()
    assert m.tags == ["international", "waterfront"]


@pytest.mark.django_db
def test_patch_rejects_non_string_tag(api, org_a, program_a, admin_user):
    user, _ = admin_user
    _, m = _make_member(org_a, program_a)
    api.force_authenticate(user=user)
    resp = api.patch(
        f"/api/v1/memberships/{m.id}/",
        {"tags": ["ok", 42]},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 400
    assert "tags" in resp.json()


@pytest.mark.django_db
def test_patch_dedupes_and_lowercases_tags(api, org_a, program_a, admin_user):
    user, _ = admin_user
    _, m = _make_member(org_a, program_a)
    api.force_authenticate(user=user)
    resp = api.patch(
        f"/api/v1/memberships/{m.id}/",
        {"tags": ["Arts", "arts", "  Sports  ", "ARTS"]},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200
    m.refresh_from_db()
    assert m.tags == ["arts", "sports"]


@pytest.mark.django_db
def test_role_field_is_read_only(api, org_a, program_a, admin_user):
    """Role should not be mutable via this endpoint to avoid privilege escalation surface."""
    user, _ = admin_user
    _, m = _make_member(org_a, program_a, role="counselor")
    api.force_authenticate(user=user)
    resp = api.patch(
        f"/api/v1/memberships/{m.id}/",
        {"role": "admin", "tags": ["x"]},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200
    m.refresh_from_db()
    assert m.role == "counselor"
    assert m.tags == ["x"]


@pytest.mark.django_db
def test_filter_by_role(api, org_a, program_a, admin_user):
    user, _ = admin_user
    _make_member(org_a, program_a, role="counselor", last="Cn1")
    _make_member(org_a, program_a, role="specialist", last="Sp1")
    _make_member(org_a, program_a, role="specialist", last="Sp2")
    api.force_authenticate(user=user)
    resp = api.get(
        "/api/v1/memberships/",
        {"program": program_a.slug, "role": "specialist"},
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200
    items = resp.json()
    items = items if isinstance(items, list) else items.get("results", items)
    assert {m["role"] for m in items} == {"specialist"}
    assert len(items) == 2


@pytest.mark.django_db
def test_filter_by_tag_returns_only_matching(api, org_a, program_a, admin_user):
    user, _ = admin_user
    _make_member(org_a, program_a, last="A1", tags=["international", "waterfront"])
    _make_member(org_a, program_a, last="A2", tags=["domestic"])
    _make_member(org_a, program_a, last="A3", tags=["israeli", "waterfront"])
    api.force_authenticate(user=user)
    resp = api.get(
        "/api/v1/memberships/",
        {"program": program_a.slug, "tag": "waterfront"},
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200
    items = resp.json()
    items = items if isinstance(items, list) else items.get("results", items)
    last_names = {m["person_name"].split(" ")[-1] for m in items}
    assert last_names == {"A1", "A3"}


@pytest.mark.django_db
def test_filter_by_multiple_tags_is_intersection(api, org_a, program_a, admin_user):
    user, _ = admin_user
    _make_member(org_a, program_a, last="X1", tags=["international", "waterfront"])
    _make_member(org_a, program_a, last="X2", tags=["international"])
    _make_member(org_a, program_a, last="X3", tags=["waterfront"])
    api.force_authenticate(user=user)
    resp = api.get(
        f"/api/v1/memberships/?program={program_a.slug}&tag=international&tag=waterfront",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200
    items = resp.json()
    items = items if isinstance(items, list) else items.get("results", items)
    last_names = {m["person_name"].split(" ")[-1] for m in items}
    assert last_names == {"X1"}


@pytest.mark.django_db
def test_bulk_tag_add_and_remove(api, org_a, program_a, admin_user):
    user, _ = admin_user
    _, m1 = _make_member(org_a, program_a, last="B1", tags=["existing"])
    _, m2 = _make_member(org_a, program_a, last="B2")
    _, m3 = _make_member(org_a, program_a, last="B3", tags=["other"])
    api.force_authenticate(user=user)

    add = api.post(
        "/api/v1/memberships/bulk-tag/",
        {
            "operation": "add",
            "membership_ids": [m1.id, m2.id, m3.id],
            "tags": ["International", "Waterfront"],
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert add.status_code == 200, add.content
    assert add.json()["updated"] == 3
    m1.refresh_from_db()
    m2.refresh_from_db()
    m3.refresh_from_db()
    assert m1.tags == ["existing", "international", "waterfront"]
    assert m2.tags == ["international", "waterfront"]
    assert m3.tags == ["other", "international", "waterfront"]

    remove = api.post(
        "/api/v1/memberships/bulk-tag/",
        {
            "operation": "remove",
            "membership_ids": [m1.id, m3.id],
            "tags": ["waterfront"],
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert remove.status_code == 200
    assert remove.json()["updated"] == 2
    m1.refresh_from_db()
    m3.refresh_from_db()
    assert "waterfront" not in m1.tags
    assert "waterfront" not in m3.tags


@pytest.mark.django_db
def test_bulk_tag_set_overwrites(api, org_a, program_a, admin_user):
    user, _ = admin_user
    _, m1 = _make_member(org_a, program_a, last="S1", tags=["one", "two"])
    api.force_authenticate(user=user)
    resp = api.post(
        "/api/v1/memberships/bulk-tag/",
        {
            "operation": "set",
            "membership_ids": [m1.id],
            "tags": ["fresh"],
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200
    m1.refresh_from_db()
    assert m1.tags == ["fresh"]


@pytest.mark.django_db
def test_bulk_tag_rejects_non_admin(api, org_a, program_a, counselor_user):
    user, _ = counselor_user
    api.force_authenticate(user=user)
    resp = api.post(
        "/api/v1/memberships/bulk-tag/",
        {"operation": "add", "membership_ids": [1], "tags": ["x"]},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_bulk_tag_validates_payload(api, org_a, program_a, admin_user):
    user, _ = admin_user
    api.force_authenticate(user=user)
    bad_op = api.post(
        "/api/v1/memberships/bulk-tag/",
        {"operation": "destroy", "membership_ids": [1], "tags": ["x"]},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert bad_op.status_code == 400

    bad_ids = api.post(
        "/api/v1/memberships/bulk-tag/",
        {"operation": "add", "membership_ids": "not-a-list", "tags": ["x"]},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert bad_ids.status_code == 400

    bad_tags = api.post(
        "/api/v1/memberships/bulk-tag/",
        {"operation": "add", "membership_ids": [1], "tags": [1, 2]},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert bad_tags.status_code == 400


@pytest.mark.django_db
def test_cross_org_isolation_on_list(api, org_a, org_b, program_a, program_b, admin_user):
    """An admin scoped to org_a must not see memberships in org_b."""
    user, _ = admin_user
    _make_member(org_a, program_a, last="Mine")
    _make_member(org_b, program_b, last="Theirs")
    api.force_authenticate(user=user)
    resp = api.get("/api/v1/memberships/", **_hdr_org(org_a.slug))
    assert resp.status_code == 200
    items = resp.json()
    items = items if isinstance(items, list) else items.get("results", items)
    last_names = {m["person_name"].split(" ")[-1] for m in items}
    assert "Theirs" not in last_names


@pytest.mark.django_db
def test_cross_org_isolation_on_patch(api, org_a, org_b, program_a, program_b, admin_user):
    user, _ = admin_user
    _, other = _make_member(org_b, program_b, last="OtherOrg")
    api.force_authenticate(user=user)
    resp = api.patch(
        f"/api/v1/memberships/{other.id}/",
        {"tags": ["snooped"]},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code in (403, 404)
    other.refresh_from_db()
    assert other.tags == []

"""Tests for the configurable catalog module (Step 7_catalog).

Covers, lean within full mode:

* Admin catalog CRUD happy path + org-admin permission gate.
* CSV import preview (valid + malformed row) and commit upsert.
* Counselor line-item back-compat: legacy camper-care ``item`` and a
  maintenance ``category`` each persist a :class:`RequestLineItem`.
* Planning dashboard aggregation (group-by-item, status filter, CSV).
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import CatalogItem
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import RequestLineItem
from bunk_logs.core.models import RequestType
from bunk_logs.core.models import Store

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org():
    return Organization.objects.create(name="Catalog Camp", slug="catalog-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Catalog Camp Summer 2026", slug="catalog-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="admin@catalog.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ada", last_name="Min", user=u,
    )
    Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )
    return u


@pytest.fixture
def counselor_user(org, program):
    u = User.objects.create_user(email="c@catalog.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Cara", last_name="Counselor", user=u,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    return u


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


# ---------------------------------------------------------------------------
# Admin CRUD + permissions
# ---------------------------------------------------------------------------


def test_admin_catalog_crud_happy_path(org, admin_user):
    c = _client(admin_user, org)
    with organization_context(org):
        store = c.post(
            "/api/v1/admin/catalog/stores/",
            {"name": "Camper Care", "fulfilling_role": "camper_care"},
            format="json",
        )
        assert store.status_code == 201, store.data
        store_id = store.data["id"]

        rt = c.post(
            "/api/v1/admin/catalog/request-types/",
            {"name": "Camper Care Items Request", "store_id": store_id},
            format="json",
        )
        assert rt.status_code == 201, rt.data
        rt_id = rt.data["id"]

        item = c.post(
            "/api/v1/admin/catalog/items/",
            {"name": "Toothbrush", "request_type_id": rt_id, "labels": {"en": "Toothbrush", "es": "Cepillo"}},
            format="json",
        )
        assert item.status_code == 201, item.data
        item_id = item.data["id"]

        tree = c.get("/api/v1/admin/catalog/tree/")
        assert tree.status_code == 200
        assert tree.data["stores"][0]["request_types"][0]["items"][0]["id"] == item_id

        patched = c.patch(
            f"/api/v1/admin/catalog/items/{item_id}/",
            {"is_active": False}, format="json",
        )
        assert patched.status_code == 200
        assert patched.data["is_active"] is False


def test_admin_catalog_requires_admin(org, counselor_user):
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/admin/catalog/tree/")
    assert resp.status_code == 403


def test_admin_catalog_org_scoped(org, admin_user):
    """A store created in one org is invisible to a second org's admin."""
    other = Organization.objects.create(name="Other", slug="other-catalog")
    other_program = Program.all_objects.create(
        organization=other, name="Other Summer 2026", slug="other-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )
    other_user = User.objects.create_user(email="a2@catalog.test", password="pw")
    other_person = Person.all_objects.create(
        organization=other, first_name="O", last_name="A", user=other_user,
    )
    Membership.all_objects.create(
        program=other_program, person=other_person, role="admin", is_active=True,
    )
    store = Store.all_objects.create(
        organization=org, name="CC", slug="cc", fulfilling_role="camper_care",
    )

    c = _client(other_user, other)
    with organization_context(other):
        resp = c.get(f"/api/v1/admin/catalog/stores/{store.id}/")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------


_VALID_CSV = (
    "store,fulfilling_role,request_type,item_name,label_es,track_quantity,unit,sort_order,is_active\n"
    "Maintenance,maintenance,Maintenance Items Request,Toilet Paper,Papel,true,roll,1,true\n"
    "Camper Care,camper_care,Camper Care Items Request,Toothbrush,Cepillo,true,,1,true\n"
)


def test_csv_import_preview_then_commit(org, admin_user):
    c = _client(admin_user, org)
    with organization_context(org):
        preview = c.post(
            "/api/v1/admin/catalog/import/?mode=preview",
            {"csv_text": _VALID_CSV}, format="json",
        )
        assert preview.status_code == 200, preview.data
        assert preview.data["valid"] is True
        assert preview.data["row_count"] == 2

        commit = c.post(
            "/api/v1/admin/catalog/import/?mode=commit",
            {"csv_text": _VALID_CSV}, format="json",
        )
        assert commit.status_code == 200, commit.data
        assert commit.data["summary"]["items_created"] == 2

    assert Store.all_objects.filter(organization=org).count() == 2
    assert CatalogItem.all_objects.filter(organization=org).count() == 2


def test_csv_import_reports_malformed_row(org, admin_user):
    bad = (
        "store,fulfilling_role,request_type,item_name\n"
        "Maintenance,maintenance,Maintenance Items Request,Toilet Paper\n"
        "Maintenance,,Maintenance Items Request,\n"  # missing item_name
    )
    c = _client(admin_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/admin/catalog/import/?mode=preview",
            {"csv_text": bad}, format="json",
        )
    assert resp.status_code == 400
    assert resp.data["valid"] is False
    assert any("item_name" in e for e in resp.data["errors"])


# ---------------------------------------------------------------------------
# Counselor line-item back-compat
# ---------------------------------------------------------------------------


def _camper_care_setup(org, program):
    """Mint a counselor on a bunk so camper-care POSTs are authorized."""
    from bunk_logs.core.models import AssignmentGroup
    from bunk_logs.core.models import AssignmentGroupMembership

    user = User.objects.create_user(email="cc@catalog.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ce", last_name="Ce", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    bunk = AssignmentGroup.objects.create(
        organization=org, program=program, name="Bunk Oak", slug="bunk-oak-cat",
        group_type="bunk", is_active=True,
    )
    AssignmentGroupMembership.objects.create(
        group=bunk, person=person, role_in_group="author", is_active=True,
    )
    return user


def test_camper_care_legacy_item_creates_line_item(org, program):
    user = _camper_care_setup(org, program)
    c = _client(user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/camper-care-requests/",
            {"item": "Sunscreen", "item_note": "SPF 50",
             "client_submission_id": str(uuid.uuid4())},
            format="json",
        )
    assert resp.status_code == 201, resp.data
    order = Order.all_objects.get(id=resp.data["id"])
    lines = list(RequestLineItem.all_objects.filter(order=order))
    assert len(lines) == 1
    assert lines[0].item_label == "Sunscreen"
    assert lines[0].quantity == 1
    # Order.item still populated for back-compat.
    assert order.item == "Sunscreen"


def test_camper_care_line_items_with_quantity(org, program):
    user = _camper_care_setup(org, program)
    c = _client(user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/camper-care-requests/",
            {"item": "Bug spray",
             "line_items": [{"item_label": "Bug spray", "quantity": 3}],
             "client_submission_id": str(uuid.uuid4())},
            format="json",
        )
    assert resp.status_code == 201, resp.data
    order = Order.all_objects.get(id=resp.data["id"])
    line = RequestLineItem.all_objects.get(order=order)
    assert line.quantity == 3


def test_maintenance_legacy_category_creates_line_item(org, program):
    user = _camper_care_setup(org, program)
    c = _client(user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/maintenance-tickets/",
            {"location": "Bunk Oak", "category": "plumbing",
             "urgency": "normal", "client_submission_id": str(uuid.uuid4())},
            format="json",
        )
    assert resp.status_code == 201, resp.data
    lines = RequestLineItem.all_objects.filter(ticket_id=resp.data["id"])
    assert lines.count() == 1
    assert lines.first().item_label == "plumbing"


def test_maintenance_catalog_category_creates_ticket(org, program):
    """A configurable catalog label (not a legacy enum value) is accepted."""
    store = Store.all_objects.create(
        organization=org, name="Maintenance", slug="maintenance",
        fulfilling_role="maintenance",
    )
    rt = RequestType.all_objects.create(
        organization=org, store=store, name="Service", slug="service",
    )
    CatalogItem.all_objects.create(
        organization=org, request_type=rt, name="Clogged toilet",
        track_quantity=False,
    )
    user = _camper_care_setup(org, program)
    c = _client(user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/maintenance-tickets/",
            {"location": "Bunk Oak", "category": "Clogged toilet",
             "urgency": "normal", "client_submission_id": str(uuid.uuid4())},
            format="json",
        )
    assert resp.status_code == 201, resp.data
    line = RequestLineItem.all_objects.get(ticket_id=resp.data["id"])
    assert line.item_label == "Clogged toilet"
    assert line.item_id is not None


def test_maintenance_options_endpoint(org, program):
    store = Store.all_objects.create(
        organization=org, name="Maintenance", slug="maintenance",
        fulfilling_role="maintenance",
    )
    rt = RequestType.all_objects.create(
        organization=org, store=store, name="Items", slug="items",
    )
    CatalogItem.all_objects.create(
        organization=org, request_type=rt, name="Toilet Paper",
        track_quantity=True, unit="roll",
    )
    user = _camper_care_setup(org, program)
    c = _client(user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/maintenance-options/")
    assert resp.status_code == 200, resp.data
    items = resp.data["request_types"][0]["items"]
    assert items[0]["label"] == "Toilet Paper"
    assert items[0]["track_quantity"] is True


# ---------------------------------------------------------------------------
# Planning dashboard aggregation
# ---------------------------------------------------------------------------


def _make_catalog_order(org, program, item, *, quantity, status="new"):
    order = Order.all_objects.create(
        organization=org, program=program, item=item.name,
        client_submission_id=uuid.uuid4(), status=status,
    )
    RequestLineItem.all_objects.create(
        organization=org, order=order, item=item,
        item_label=item.name, quantity=quantity,
    )
    return order


def test_planning_dashboard_aggregates_by_item(org, program, admin_user):
    store = Store.all_objects.create(
        organization=org, name="Camper Care", slug="cc",
        fulfilling_role="camper_care",
    )
    rt = RequestType.all_objects.create(
        organization=org, store=store, name="Items", slug="items",
    )
    toothbrush = CatalogItem.all_objects.create(
        organization=org, request_type=rt, name="Toothbrush",
    )
    soap = CatalogItem.all_objects.create(
        organization=org, request_type=rt, name="Soap",
    )
    _make_catalog_order(org, program, toothbrush, quantity=2, status="fulfilled")
    _make_catalog_order(org, program, toothbrush, quantity=3, status="new")
    _make_catalog_order(org, program, soap, quantity=5, status="fulfilled")

    c = _client(admin_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/admin/catalog/planning/?group_by=item")
    assert resp.status_code == 200, resp.data
    by_label = {r["label"]: r for r in resp.data["rows"]}
    assert by_label["Toothbrush"]["quantity"] == 5
    assert by_label["Toothbrush"]["request_count"] == 2
    assert by_label["Soap"]["quantity"] == 5
    assert resp.data["totals"]["quantity"] == 10

    with organization_context(org):
        fulfilled = c.get("/api/v1/admin/catalog/planning/?status=fulfilled")
    f_by_label = {r["label"]: r for r in fulfilled.data["rows"]}
    assert f_by_label["Toothbrush"]["quantity"] == 2
    assert fulfilled.data["totals"]["quantity"] == 7


def test_planning_dashboard_csv_export(org, program, admin_user):
    store = Store.all_objects.create(
        organization=org, name="Camper Care", slug="cc",
        fulfilling_role="camper_care",
    )
    rt = RequestType.all_objects.create(
        organization=org, store=store, name="Items", slug="items",
    )
    item = CatalogItem.all_objects.create(
        organization=org, request_type=rt, name="Toothbrush",
    )
    _make_catalog_order(org, program, item, quantity=4, status="fulfilled")

    c = _client(admin_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/admin/catalog/planning/?export=csv")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    body = resp.content.decode("utf-8")
    assert "Toothbrush" in body
    assert "label,store,request_type,quantity,request_count" in body

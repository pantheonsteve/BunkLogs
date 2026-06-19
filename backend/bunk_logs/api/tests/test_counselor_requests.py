"""Tests for ``GET /api/v1/counselor/requests/`` (Stories 7 + 8 combined list)."""
from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="RQ Camp", slug="rq-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="RQ Camp Summer 2026",
        slug="rq-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="cnsl@rq.test", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org, first_name="Mira", last_name="Sand", user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )


@pytest.fixture
def bunk(org, program):
    return AssignmentGroup.objects.create(
        organization=org,
        program=program,
        name="Bunk Pine",
        slug="bunk-pine",
        group_type="bunk",
        is_active=True,
    )


@pytest.fixture
def counselor_as_author(bunk, counselor_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk, person=counselor_person, role_in_group="author", is_active=True,
    )


@pytest.fixture
def co_person(org):
    u = User.objects.create_user(email="co@rq.test", password="pw")
    return Person.all_objects.create(organization=org, first_name="Jordan", last_name="Patel", user=u)


@pytest.fixture
def co_membership(program, co_person):
    return Membership.all_objects.create(
        program=program, person=co_person, role="counselor", is_active=True,
    )


@pytest.fixture
def co_as_author(bunk, co_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk, person=co_person, role_in_group="author", is_active=True,
    )


@pytest.fixture
def camper(org, bunk):
    p = Person.all_objects.create(organization=org, first_name="Sarah", last_name="Levin")
    AssignmentGroupMembership.objects.create(
        group=bunk, person=p, role_in_group="subject", is_active=True,
    )
    return p


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


# ---------------------------------------------------------------------------
# Self requests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_requests_lists_own_order(
    org, program, counselor_user, counselor_person, counselor_membership, camper,
):
    Order.all_objects.create(
        organization=org,
        program=program,
        subject=camper,
        submitted_by=counselor_membership,
        item="Toothbrush",
        status="new",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/requests/")
    assert resp.status_code == 200
    assert len(resp.data["requests"]) == 1
    row = resp.data["requests"][0]
    assert row["type"] == "camper_care"
    assert row["item"] == "Toothbrush"
    assert row["submitter"]["is_self"] is True
    assert row["submitter"]["name"] is None


@pytest.mark.django_db
def test_requests_lists_maintenance_ticket(
    org, program, counselor_user, counselor_person, counselor_membership,
):
    MaintenanceTicket.all_objects.create(
        organization=org,
        program=program,
        submitted_by=counselor_membership,
        location="Bunk Pine",
        category=MaintenanceTicket.Category.LEAK,
        description="Drip",
        urgency="urgent",
        urgent_reason="Standing water in bunk",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/requests/")
    row = resp.data["requests"][0]
    assert row["type"] == "maintenance"
    assert row["urgency"] == "urgent"
    assert row["category"] == "leak"


# ---------------------------------------------------------------------------
# Co-counselor scoping (C4)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_requests_excludes_co_counselor_request(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, co_person, co_membership, co_as_author, camper,
):
    Order.all_objects.create(
        organization=org,
        program=program,
        subject=camper,
        submitted_by=co_membership,
        item="Bug spray",
        status="in_progress",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/requests/")
    assert resp.data["requests"] == []


@pytest.mark.django_db
def test_requests_excludes_other_bunk_counselor(
    org, program, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author,
):
    # An unrelated counselor on a DIFFERENT bunk; their order must not show.
    other_bunk = AssignmentGroup.objects.create(
        organization=org,
        program=program,
        name="Bunk Other",
        slug="bunk-other",
        group_type="bunk",
        is_active=True,
    )
    other_user = User.objects.create_user(email="other@rq.test", password="pw")
    other_person = Person.all_objects.create(
        organization=org, first_name="Other", last_name="One", user=other_user,
    )
    other_membership = Membership.all_objects.create(
        program=program, person=other_person, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.objects.create(
        group=other_bunk, person=other_person, role_in_group="author", is_active=True,
    )
    Order.all_objects.create(
        organization=org,
        program=program,
        submitted_by=other_membership,
        item="not mine",
        status="new",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/requests/")
    assert resp.data["requests"] == []


# ---------------------------------------------------------------------------
# Status filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_requests_default_excludes_closed(
    org, program, counselor_user, counselor_person, counselor_membership,
):
    Order.all_objects.create(
        organization=org,
        program=program,
        submitted_by=counselor_membership,
        item="closed item",
        status="fulfilled",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/requests/")
    assert resp.data["requests"] == []


@pytest.mark.django_db
def test_requests_status_all_returns_closed(
    org, program, counselor_user, counselor_person, counselor_membership,
):
    Order.all_objects.create(
        organization=org,
        program=program,
        submitted_by=counselor_membership,
        item="closed item",
        status="fulfilled",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/requests/?status=all")
    assert len(resp.data["requests"]) == 1
    assert resp.data["requests"][0]["status"] == "fulfilled"


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_requests_does_not_leak_other_org(
    org, program, counselor_user, counselor_person, counselor_membership,
):
    other = Organization.objects.create(name="Other", slug="other-rq")
    other_program = Program.all_objects.create(
        organization=other,
        name="Other Summer",
        slug="other-rq-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )
    other_user = User.objects.create_user(email="x@other.test", password="pw")
    other_person = Person.all_objects.create(
        organization=other, first_name="X", last_name="Y", user=other_user,
    )
    other_membership = Membership.all_objects.create(
        program=other_program, person=other_person, role="counselor", is_active=True,
    )
    Order.all_objects.create(
        organization=other,
        program=other_program,
        submitted_by=other_membership,
        item="cross-org",
        status="new",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/requests/")
    assert resp.data["requests"] == []


@pytest.mark.django_db
def test_camper_care_request_detail_returns_order_and_activity(
    org,
    program,
    counselor_user,
    counselor_person,
    counselor_membership,
    bunk,
    counselor_as_author,
    camper,
):
    order = Order.all_objects.create(
        organization=org,
        program=program,
        subject=camper,
        submitted_by=counselor_membership,
        item="Bug spray",
        item_note="SPF 50",
        description="Running low",
        status="new",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/counselor/requests/camper-care/{order.id}/")
    assert resp.status_code == 200
    assert resp.data["scope"] == "viewer"
    assert resp.data["order"]["item"] == "Bug spray"
    assert resp.data["order"]["editable"] is True
    assert resp.data["order"]["subject"]["name"]


@pytest.mark.django_db
def test_camper_care_request_patch_updates_open_request(
    org,
    program,
    counselor_user,
    counselor_membership,
    bunk,
    counselor_as_author,
    camper,
):
    order = Order.all_objects.create(
        organization=org,
        program=program,
        subject=camper,
        submitted_by=counselor_membership,
        item="Bug spray",
        status="new",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/counselor/requests/camper-care/{order.id}/",
            {"item": "Sunscreen", "item_note": "SPF 50"},
            format="json",
        )
    assert resp.status_code == 200
    assert resp.data["order"]["item"] == "Sunscreen"
    assert resp.data["order"]["item_note"] == "SPF 50"
    order.refresh_from_db()
    assert order.item == "Sunscreen"


@pytest.mark.django_db
def test_camper_care_request_patch_forbidden_when_in_progress(
    org,
    program,
    counselor_user,
    counselor_membership,
    camper,
):
    order = Order.all_objects.create(
        organization=org,
        program=program,
        subject=camper,
        submitted_by=counselor_membership,
        item="Bug spray",
        status="in_progress",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/counselor/requests/camper-care/{order.id}/",
            {"item": "Sunscreen"},
            format="json",
        )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_camper_care_request_detail_404_for_other_counselor(
    org,
    program,
    counselor_user,
    counselor_membership,
    co_membership,
    camper,
):
    order = Order.all_objects.create(
        organization=org,
        program=program,
        subject=camper,
        submitted_by=co_membership,
        item="Hidden",
        status="new",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/counselor/requests/camper-care/{order.id}/")
    assert resp.status_code == 404

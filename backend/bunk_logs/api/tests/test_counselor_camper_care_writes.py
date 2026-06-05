"""Tests for ``POST /api/v1/counselor/camper-care-requests/`` (Story 7)."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import OrderItemSuggestion
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
    return Organization.objects.create(name="CC Camp", slug="cc-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="CC Camp Summer 2026", slug="cc-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="c@cc.test", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org, first_name="Lee", last_name="A", user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )


@pytest.fixture
def bunk(org, program):
    return AssignmentGroup.objects.create(
        organization=org, program=program, name="Bunk Pine",
        slug="bunk-pine-cc", group_type="bunk", is_active=True,
    )


@pytest.fixture
def counselor_as_author(bunk, counselor_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk, person=counselor_person, role_in_group="author", is_active=True,
    )


@pytest.fixture
def camper(org, bunk):
    p = Person.all_objects.create(organization=org, first_name="Avi", last_name="L")
    AssignmentGroupMembership.objects.create(
        group=bunk, person=p, role_in_group="subject", is_active=True,
    )
    return p


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


@pytest.mark.django_db
def test_create_camper_care_request_201(
    org, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, camper,
):
    c = _client(counselor_user, org)
    payload = {
        "subject_id": camper.id,
        "item": "Toothbrush",
        "item_note": "purple please",
        "client_submission_id": str(uuid.uuid4()),
    }
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/camper-care-requests/", payload, format="json",
        )
    assert resp.status_code == 201, resp.data
    assert resp.data["item"] == "Toothbrush"
    order = Order.all_objects.get(id=resp.data["id"])
    assert order.subject == camper
    assert order.submitted_by == counselor_membership
    assert order.submitted_from_bunk == bunk
    assert order.status == "new"


@pytest.mark.django_db
def test_camper_care_request_idempotent(
    org, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, camper,
):
    c = _client(counselor_user, org)
    csid = str(uuid.uuid4())
    payload = {
        "subject_id": camper.id, "item": "Toothpaste",
        "client_submission_id": csid,
    }
    with organization_context(org):
        first = c.post(
            "/api/v1/counselor/camper-care-requests/", payload, format="json",
        )
        second = c.post(
            "/api/v1/counselor/camper-care-requests/", payload, format="json",
        )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert Order.all_objects.filter(client_submission_id=csid).count() == 1


@pytest.mark.django_db
def test_camper_care_emits_audit(
    org, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author, camper,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        c.post(
            "/api/v1/counselor/camper-care-requests/",
            {"subject_id": camper.id, "item": "Sunscreen",
             "client_submission_id": str(uuid.uuid4())}, format="json",
        )
    assert AuditEvent.all_objects.filter(
        event_type=AuditEvent.EventType.CREATED, content_type="order",
    ).exists()


@pytest.mark.django_db
def test_camper_care_subject_must_be_on_viewer_bunk(
    org, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author,
):
    other_camper = Person.all_objects.create(
        organization=org, first_name="Off", last_name="Roster",
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/camper-care-requests/",
            {"subject_id": other_camper.id, "item": "X",
             "client_submission_id": str(uuid.uuid4())}, format="json",
        )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_item_suggestions_returns_active_rows_in_sort_order(
    org, counselor_user, counselor_person, counselor_membership,
    program,
):
    OrderItemSuggestion.objects.create(program=program, label="Toothpaste", sort_order=2)
    OrderItemSuggestion.objects.create(program=program, label="Bug spray", sort_order=1)
    OrderItemSuggestion.objects.create(
        program=program, label="Hidden", sort_order=0, is_active=False,
    )
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/camper-care-item-suggestions/")
    assert resp.status_code == 200, resp.data
    labels = [s["label"] for s in resp.data["suggestions"]]
    assert labels == ["Bug spray", "Toothpaste"]
    assert all("id" in s and "sort_order" in s for s in resp.data["suggestions"])


@pytest.mark.django_db
def test_item_suggestions_empty_when_no_program(
    org, counselor_user, counselor_person,
):
    """A viewer without a program membership gets an empty list, not a 500."""
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/counselor/camper-care-item-suggestions/")
    assert resp.status_code == 200
    assert resp.data == {"suggestions": []}


@pytest.mark.django_db
def test_camper_care_no_subject_allowed(
    org, counselor_user, counselor_person, counselor_membership,
    bunk, counselor_as_author,
):
    """Bunk-scoped requests (no subject) are allowed for general bunk needs."""
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/camper-care-requests/",
            {"item": "Bug spray", "item_note": "Whole bunk",
             "client_submission_id": str(uuid.uuid4())}, format="json",
        )
    assert resp.status_code == 201, resp.data
    assert resp.data["subject_id"] is None

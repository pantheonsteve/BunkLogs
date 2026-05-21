"""Tests for counselor maintenance ticket write endpoints (Story 8)."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import TicketPhoto

User = get_user_model()


# 1x1 white PNG generated via PIL; passes ImageField's image-content
# verification. Inlined as bytes so the test doesn't depend on PIL at runtime.
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff"
    b"?\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="MT Camp", slug="mt-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="MT Camp Summer 2026", slug="mt-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="c@mt.test", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org, first_name="Lior", last_name="K", user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


def _png_upload(name="photo.png"):
    return SimpleUploadedFile(name, PNG_BYTES, content_type="image/png")


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_ticket_201(
    org, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    payload = {
        "location": "Bunk Maple — sink",
        "category": "plumbing",
        "description": "Drain runs slow",
        "urgency": "normal",
        "client_submission_id": str(uuid.uuid4()),
    }
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/maintenance-tickets/", payload, format="json",
        )
    assert resp.status_code == 201, resp.data
    ticket = MaintenanceTicket.all_objects.get(id=resp.data["id"])
    assert ticket.location == "Bunk Maple — sink"
    assert ticket.category == "plumbing"
    assert ticket.submitted_by == counselor_membership


@pytest.mark.django_db
def test_urgent_requires_reason(
    org, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    payload = {
        "location": "Bunk Maple",
        "category": "leak",
        "description": "Major leak",
        "urgency": "urgent",
        "client_submission_id": str(uuid.uuid4()),
    }
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/maintenance-tickets/", payload, format="json",
        )
    assert resp.status_code == 400
    assert "urgent_reason" in (resp.data or {})


@pytest.mark.django_db
def test_create_ticket_idempotent(
    org, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    csid = str(uuid.uuid4())
    payload = {
        "location": "Pool deck", "category": "broken_light",
        "description": "Floodlight out", "urgency": "normal",
        "client_submission_id": csid,
    }
    with organization_context(org):
        first = c.post(
            "/api/v1/counselor/maintenance-tickets/", payload, format="json",
        )
        second = c.post(
            "/api/v1/counselor/maintenance-tickets/", payload, format="json",
        )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert MaintenanceTicket.all_objects.filter(client_submission_id=csid).count() == 1


@pytest.mark.django_db
def test_create_ticket_emits_audit(
    org, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        c.post(
            "/api/v1/counselor/maintenance-tickets/",
            {"location": "Loc", "category": "other", "urgency": "low",
             "client_submission_id": str(uuid.uuid4())},
            format="json",
        )
    assert AuditEvent.all_objects.filter(
        event_type=AuditEvent.EventType.CREATED, content_type="maintenance_ticket",
    ).exists()


# ---------------------------------------------------------------------------
# Photo upload
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_ticket_with_photos(
    org, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    data = {
        "location": "Bunk Maple",
        "category": "pest",
        "description": "Wasp nest",
        "urgency": "normal",
        "client_submission_id": str(uuid.uuid4()),
        "photos": [_png_upload("a.png"), _png_upload("b.png")],
    }
    with organization_context(org):
        resp = c.post(
            "/api/v1/counselor/maintenance-tickets/", data, format="multipart",
        )
    assert resp.status_code == 201, resp.data
    assert len(resp.data["photos"]) == 2
    assert all(p["is_followup"] is False for p in resp.data["photos"])


@pytest.mark.django_db
def test_followup_photo_endpoint(
    org, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        create_resp = c.post(
            "/api/v1/counselor/maintenance-tickets/",
            {"location": "Loc", "category": "other", "urgency": "low",
             "client_submission_id": str(uuid.uuid4())},
            format="json",
        )
        ticket_id = create_resp.data["id"]
        upload_resp = c.post(
            f"/api/v1/counselor/maintenance-tickets/{ticket_id}/photos/",
            {"image": _png_upload("followup.png"), "caption": "after"},
            format="multipart",
        )
    assert upload_resp.status_code == 201, upload_resp.data
    assert upload_resp.data["is_followup"] is True
    assert TicketPhoto.objects.filter(
        ticket_id=ticket_id, is_followup=True,
    ).count() == 1


@pytest.mark.django_db
def test_followup_photo_403_on_other_submitter(
    org, program, counselor_user, counselor_person, counselor_membership,
):
    c = _client(counselor_user, org)
    with organization_context(org):
        create_resp = c.post(
            "/api/v1/counselor/maintenance-tickets/",
            {"location": "Loc", "category": "other", "urgency": "low",
             "client_submission_id": str(uuid.uuid4())},
            format="json",
        )
        ticket_id = create_resp.data["id"]

    other_user = User.objects.create_user(email="other@mt.test", password="pw")
    other_person = Person.all_objects.create(
        organization=org, first_name="X", last_name="Y", user=other_user,
    )
    Membership.all_objects.create(
        program=program, person=other_person, role="counselor", is_active=True,
    )
    c2 = _client(other_user, org)
    with organization_context(org):
        resp = c2.post(
            f"/api/v1/counselor/maintenance-tickets/{ticket_id}/photos/",
            {"image": _png_upload("nope.png")}, format="multipart",
        )
    assert resp.status_code == 403

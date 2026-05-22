"""Tests for maintenance notes create + edit (Step 7_10, Story 33)."""

from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def org():
    return Organization.objects.create(name="Notes Org", slug="notes-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Notes Org Summer",
        slug="notes-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def maint_user(org, program):
    user = User.objects.create_user(email="mnotes@notes.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Notes", last_name="Staff", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="maintenance", is_active=True,
    )
    return user


@pytest.fixture
def ticket(org, program):
    with organization_context(org):
        return MaintenanceTicket.objects.create(
            organization=org,
            program=program,
            location="Field",
            description="Broken fence",
            urgency=MaintenanceTicket.Urgency.LOW,
        )


@pytest.fixture
def api():
    return APIClient()


# ---------------------------------------------------------------------------
# Note create
# ---------------------------------------------------------------------------


class TestMaintenanceNoteCreate:
    def test_team_only_note(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.post(
            f"/api/v1/maintenance/tickets/{ticket.id}/notes/",
            {"body": "Checked the fence", "visibility": "team_only"},
            format="json",
            **_hdr(org.slug),
        )
        assert r.status_code == 201, r.content
        data = r.json()
        assert data["event_type"] == "note"
        assert data["note"] == "Checked the fence"
        assert data["visibility"] == "team_only"

    def test_submitter_visible_note(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.post(
            f"/api/v1/maintenance/tickets/{ticket.id}/notes/",
            {"body": "We are on it", "visibility": "submitter_visible"},
            format="json",
            **_hdr(org.slug),
        )
        assert r.status_code == 201
        assert r.json()["visibility"] == "submitter_visible"

    def test_note_persisted_in_activity(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        api.post(
            f"/api/v1/maintenance/tickets/{ticket.id}/notes/",
            {"body": "Persisted note", "visibility": "team_only"},
            format="json",
            **_hdr(org.slug),
        )
        events = OrderActivityEvent.all_objects.filter(
            content_type="maintenance_ticket",
            content_id=ticket.id,
            event_type=OrderActivityEvent.EventType.NOTE,
        )
        assert events.exists()
        assert events.first().note == "Persisted note"

    def test_body_required(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.post(
            f"/api/v1/maintenance/tickets/{ticket.id}/notes/",
            {"body": "", "visibility": "team_only"},
            format="json",
            **_hdr(org.slug),
        )
        assert r.status_code == 400
        assert "body" in r.json()

    def test_invalid_visibility_rejected(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.post(
            f"/api/v1/maintenance/tickets/{ticket.id}/notes/",
            {"body": "hi", "visibility": "bogus"},
            format="json",
            **_hdr(org.slug),
        )
        assert r.status_code == 400
        assert "visibility" in r.json()

    def test_cannot_note_on_closed_ticket(self, api, org, ticket, maint_user):
        ticket.status = MaintenanceTicket.Status.FULFILLED
        ticket.save()
        api.force_authenticate(user=maint_user)
        r = api.post(
            f"/api/v1/maintenance/tickets/{ticket.id}/notes/",
            {"body": "After close", "visibility": "team_only"},
            format="json",
            **_hdr(org.slug),
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Note edit
# ---------------------------------------------------------------------------


class TestMaintenanceNoteEdit:
    def test_author_can_edit_within_window(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.post(
            f"/api/v1/maintenance/tickets/{ticket.id}/notes/",
            {"body": "Original", "visibility": "team_only"},
            format="json",
            **_hdr(org.slug),
        )
        note_id = r.json()["id"]
        r2 = api.patch(
            f"/api/v1/maintenance/tickets/{ticket.id}/notes/{note_id}/",
            {"body": "Updated", "visibility": "submitter_visible"},
            format="json",
            **_hdr(org.slug),
        )
        assert r2.status_code == 200, r2.content
        assert r2.json()["note"] == "Updated"
        assert r2.json()["visibility"] == "submitter_visible"

    def test_edit_window_enforced(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.post(
            f"/api/v1/maintenance/tickets/{ticket.id}/notes/",
            {"body": "Old", "visibility": "team_only"},
            format="json",
            **_hdr(org.slug),
        )
        note_id = r.json()["id"]

        # Wind back the created_at beyond 24h
        event = OrderActivityEvent.all_objects.get(pk=note_id)
        event.created_at = timezone.now() - timedelta(hours=25)
        event.save(update_fields=["created_at"])

        r2 = api.patch(
            f"/api/v1/maintenance/tickets/{ticket.id}/notes/{note_id}/",
            {"body": "Too late"},
            format="json",
            **_hdr(org.slug),
        )
        assert r2.status_code == 403

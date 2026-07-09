"""Tests for maintenance queue, ticket detail, and urgency validation (Step 7_10)."""

from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
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
    return Organization.objects.create(name="MQ Org", slug="mq-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="MQ Org Summer",
        slug="mq-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def maint_user(org, program):
    user = User.objects.create_user(email="maint@mq.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Maint", last_name="Staff", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="maintenance", is_active=True,
    )
    return user


@pytest.fixture
def counselor_membership(org, program):
    user = User.objects.create_user(email="counselor@mq.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Coun", last_name="Selor", user=user,
    )
    membership = Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    membership.user = user  # convenience handle for tests
    return membership


@pytest.fixture
def counselor_user(counselor_membership):
    return counselor_membership.user


@pytest.fixture
def ticket(org, program):
    with organization_context(org):
        return MaintenanceTicket.objects.create(
            organization=org,
            program=program,
            location="Bunk 12",
            category=MaintenanceTicket.Category.PLUMBING,
            description="Sink draining slowly",
            urgency=MaintenanceTicket.Urgency.NORMAL,
        )


@pytest.fixture
def urgent_ticket(org, program):
    with organization_context(org):
        return MaintenanceTicket.objects.create(
            organization=org,
            program=program,
            location="Dining Hall",
            category=MaintenanceTicket.Category.LEAK,
            description="Water pouring from ceiling",
            urgency=MaintenanceTicket.Urgency.URGENT,
            urgent_reason="Flooding risk",
        )


@pytest.fixture
def admin_user(org, program):
    user = User.objects.create_user(email="admin@mq.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Org", last_name="Admin", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )
    return user


@pytest.fixture
def api():
    return APIClient()


# ---------------------------------------------------------------------------
# Happy path: queue
# ---------------------------------------------------------------------------


class TestMaintenanceQueue:
    def test_returns_open_tickets_by_default(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.get("/api/v1/maintenance/queue/", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        data = r.json()
        assert "tickets" in data
        assert "counts" in data
        ids = [t["id"] for t in data["tickets"]]
        assert str(ticket.id) in ids

    def test_counts_header(self, api, org, ticket, urgent_ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.get("/api/v1/maintenance/queue/", **_hdr(org.slug))
        counts = r.json()["counts"]
        assert counts["new"] >= 2
        assert counts["urgent_open"] >= 1

    def test_urgent_sorted_first(self, api, org, ticket, urgent_ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.get("/api/v1/maintenance/queue/", **_hdr(org.slug))
        tickets = r.json()["tickets"]
        urgencies = [t["urgency"] for t in tickets]
        urgent_idx = urgencies.index("urgent")
        normal_idx = urgencies.index("normal")
        assert urgent_idx < normal_idx

    def test_closed_filter(self, api, org, ticket, maint_user):
        ticket.status = MaintenanceTicket.Status.FULFILLED
        ticket.save()
        api.force_authenticate(user=maint_user)
        r = api.get("/api/v1/maintenance/queue/?filter=closed", **_hdr(org.slug))
        assert r.status_code == 200
        ids = [t["id"] for t in r.json()["tickets"]]
        assert str(ticket.id) in ids

    def test_closed_search(self, api, org, ticket, maint_user):
        ticket.status = MaintenanceTicket.Status.FULFILLED
        ticket.save()
        api.force_authenticate(user=maint_user)
        r = api.get(
            "/api/v1/maintenance/queue/?filter=closed&search=draining",
            **_hdr(org.slug),
        )
        assert r.status_code == 200
        ids = [t["id"] for t in r.json()["tickets"]]
        assert str(ticket.id) in ids

    def test_invalid_filter_rejected(self, api, org, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.get("/api/v1/maintenance/queue/?filter=bogus", **_hdr(org.slug))
        assert r.status_code == 400

    def test_maintenance_sees_operational_program_not_newest_membership(
        self, api, org,
    ):
        """Future-session roster rows must not hide the session running today."""
        today = timezone.now().date()
        current_program = Program.all_objects.create(
            organization=org,
            name="MQ Org Current Session",
            slug="mq-current-session",
            program_type="summer_camp",
            start_date=today - timedelta(days=7),
            end_date=today + timedelta(days=7),
        )
        future_program = Program.all_objects.create(
            organization=org,
            name="MQ Org Future Session",
            slug="mq-future-session",
            program_type="summer_camp",
            start_date=today + timedelta(days=30),
            end_date=today + timedelta(days=60),
        )
        user = User.objects.create_user(email="multi-maint@mq.com", password="pw")
        person = Person.all_objects.create(
            organization=org, first_name="Multi", last_name="Maint", user=user,
        )
        Membership.all_objects.create(
            program=current_program, person=person, role="maintenance", is_active=True,
        )
        Membership.all_objects.create(
            program=future_program, person=person, role="maintenance", is_active=True,
        )
        with organization_context(org):
            current_ticket = MaintenanceTicket.objects.create(
                organization=org,
                program=current_program,
                location="Shower house",
                category=MaintenanceTicket.Category.PLUMBING,
                description="Running session leak",
                urgency=MaintenanceTicket.Urgency.NORMAL,
            )
            MaintenanceTicket.objects.create(
                organization=org,
                program=future_program,
                location="Future bunk",
                category=MaintenanceTicket.Category.PLUMBING,
                description="Not operational yet",
                urgency=MaintenanceTicket.Urgency.NORMAL,
            )
        api.force_authenticate(user=user)
        r = api.get("/api/v1/maintenance/queue/", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        ids = [t["id"] for t in r.json()["tickets"]]
        assert str(current_ticket.id) in ids
        assert r.json()["scope"] == "team"

    def test_admin_sees_tickets_from_other_program(
        self, api, org, admin_user, counselor_membership,
    ):
        """Org admins see the full org queue, not only their own program."""
        other_program = Program.all_objects.create(
            organization=org,
            name="MQ Org Other Session",
            slug="mq-other-session",
            program_type="summer_camp",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 8, 15),
        )
        with organization_context(org):
            other_ticket = MaintenanceTicket.objects.create(
                organization=org,
                program=other_program,
                location="New bunk",
                category=MaintenanceTicket.Category.PLUMBING,
                description="Leak in current session",
                urgency=MaintenanceTicket.Urgency.NORMAL,
                submitted_by=counselor_membership,
            )
        api.force_authenticate(user=admin_user)
        r = api.get("/api/v1/maintenance/queue/", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        ids = [t["id"] for t in r.json()["tickets"]]
        assert str(other_ticket.id) in ids
        assert r.json()["scope"] == "team"

    def test_admin_can_open_ticket_detail_from_other_program(
        self, api, org, admin_user, counselor_membership,
    ):
        other_program = Program.all_objects.create(
            organization=org,
            name="MQ Org Detail Session",
            slug="mq-detail-session",
            program_type="summer_camp",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 8, 15),
        )
        with organization_context(org):
            other_ticket = MaintenanceTicket.objects.create(
                organization=org,
                program=other_program,
                location="Shower house",
                category=MaintenanceTicket.Category.LEAK,
                description="Dripping faucet",
                urgency=MaintenanceTicket.Urgency.NORMAL,
                submitted_by=counselor_membership,
            )
        api.force_authenticate(user=admin_user)
        r = api.get(
            f"/api/v1/maintenance/tickets/{other_ticket.id}/",
            **_hdr(org.slug),
        )
        assert r.status_code == 200, r.content
        assert r.json()["ticket"]["id"] == str(other_ticket.id)
        assert r.json()["scope"] == "team"


# ---------------------------------------------------------------------------
# Scope: non-maintenance members get a read-only view of the full queue
# ---------------------------------------------------------------------------


class TestMaintenanceQueueViewerScope:
    def test_team_scope_for_maintenance(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.get("/api/v1/maintenance/queue/", **_hdr(org.slug))
        assert r.status_code == 200
        assert r.json()["scope"] == "team"
        # Team scope keeps transition actions available.
        rows = r.json()["tickets"]
        assert any(row["available_transitions"] for row in rows)

    def test_viewer_defaults_to_mine_filter(
        self, api, org, program, ticket, counselor_membership,
    ):
        with organization_context(org):
            mine = MaintenanceTicket.objects.create(
                organization=org,
                program=program,
                location="Bunk 5",
                category=MaintenanceTicket.Category.PLUMBING,
                description="My leak",
                urgency=MaintenanceTicket.Urgency.NORMAL,
                submitted_by=counselor_membership,
            )
        api.force_authenticate(user=counselor_membership.user)
        r = api.get("/api/v1/maintenance/queue/", **_hdr(org.slug))
        assert r.status_code == 200
        ids = [t["id"] for t in r.json()["tickets"]]
        assert str(mine.id) in ids
        assert str(ticket.id) not in ids

    def test_viewer_can_see_all_open_with_filter(
        self, api, org, ticket, counselor_membership,
    ):
        api.force_authenticate(user=counselor_membership.user)
        r = api.get("/api/v1/maintenance/queue/?filter=open", **_hdr(org.slug))
        ids = [t["id"] for t in r.json()["tickets"]]
        assert str(ticket.id) in ids

    def test_viewer_can_close_own_ticket(
        self, api, org, program, counselor_membership,
    ):
        with organization_context(org):
            mine = MaintenanceTicket.objects.create(
                organization=org,
                program=program,
                location="Bunk 5",
                category=MaintenanceTicket.Category.PLUMBING,
                description="My leak",
                urgency=MaintenanceTicket.Urgency.NORMAL,
                status=MaintenanceTicket.Status.NEW,
                submitted_by=counselor_membership,
            )
        api.force_authenticate(user=counselor_membership.user)
        r = api.get("/api/v1/maintenance/queue/", **_hdr(org.slug))
        row = next(t for t in r.json()["tickets"] if t["id"] == str(mine.id))
        assert row["is_mine"] is True
        assert "fulfilled" in row["available_transitions"]

        tr = api.post(
            f"/api/v1/maintenance/{mine.id}/transition/",
            {"to_state": "fulfilled"},
            format="json",
            **_hdr(org.slug),
        )
        assert tr.status_code == 200, tr.content
        mine.refresh_from_db()
        assert mine.status == MaintenanceTicket.Status.FULFILLED

    def test_viewer_cannot_close_others_ticket(
        self, api, org, ticket, counselor_membership,
    ):
        api.force_authenticate(user=counselor_membership.user)
        r = api.post(
            f"/api/v1/maintenance/{ticket.id}/transition/",
            {"to_state": "fulfilled"},
            format="json",
            **_hdr(org.slug),
        )
        assert r.status_code == 403

    def test_unauthenticated_rejected(self, api, org):
        r = api.get("/api/v1/maintenance/queue/", **_hdr(org.slug))
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Ticket detail
# ---------------------------------------------------------------------------


class TestMaintenanceTicketDetail:
    def test_returns_ticket_and_activity(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        r = api.get(f"/api/v1/maintenance/tickets/{ticket.id}/", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        data = r.json()
        assert data["ticket"]["id"] == str(ticket.id)
        assert "activity" in data
        assert "photos" in data

    def test_viewer_can_read_detail_readonly(
        self, api, org, ticket, counselor_membership,
    ):
        # Any active member can open a ticket to follow progress, but read-only.
        api.force_authenticate(user=counselor_membership.user)
        r = api.get(f"/api/v1/maintenance/tickets/{ticket.id}/", **_hdr(org.slug))
        assert r.status_code == 200, r.content
        data = r.json()
        assert data["scope"] == "viewer"
        assert data["ticket"]["available_transitions"] == []

    def test_viewer_cannot_see_team_only_notes(
        self, api, org, program, ticket, counselor_membership, maint_user,
    ):
        with organization_context(org):
            OrderActivityEvent.objects.create(
                organization=org,
                program=program,
                event_type=OrderActivityEvent.EventType.NOTE,
                content_type="maintenance_ticket",
                content_id=ticket.id,
                note="Internal only",
                metadata={"visibility": "team_only"},
            )
            OrderActivityEvent.objects.create(
                organization=org,
                program=program,
                event_type=OrderActivityEvent.EventType.NOTE,
                content_type="maintenance_ticket",
                content_id=ticket.id,
                note="Shared with submitter",
                metadata={"visibility": "submitter_visible"},
            )
        api.force_authenticate(user=counselor_membership.user)
        r = api.get(f"/api/v1/maintenance/tickets/{ticket.id}/", **_hdr(org.slug))
        notes = [e["note"] for e in r.json()["activity"] if e["event_type"] == "note"]
        assert "Shared with submitter" in notes
        assert "Internal only" not in notes

        # The maintenance team still sees both notes.
        api.force_authenticate(user=maint_user)
        r2 = api.get(f"/api/v1/maintenance/tickets/{ticket.id}/", **_hdr(org.slug))
        team_notes = [e["note"] for e in r2.json()["activity"] if e["event_type"] == "note"]
        assert "Internal only" in team_notes
        assert "Shared with submitter" in team_notes

    def test_404_for_wrong_program(self, api, org, maint_user):
        other_org = Organization.objects.create(name="Other", slug="other-mq")
        other_program = Program.all_objects.create(
            organization=other_org,
            name="Other Other Program",
            slug="other-mq-summer",
            program_type="summer_camp",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 31),
        )
        with organization_context(other_org):
            other_ticket = MaintenanceTicket.objects.create(
                organization=other_org,
                program=other_program,
                urgency=MaintenanceTicket.Urgency.NORMAL,
            )
        api.force_authenticate(user=maint_user)
        r = api.get(f"/api/v1/maintenance/tickets/{other_ticket.id}/", **_hdr(org.slug))
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Urgency validation
# ---------------------------------------------------------------------------


class TestUrgencyValidation:
    def test_urgent_requires_reason(self, org, program):
        t = MaintenanceTicket(
            organization=org,
            program=program,
            urgency=MaintenanceTicket.Urgency.URGENT,
            urgent_reason="",
        )
        with pytest.raises(ValidationError, match="urgent_reason"):
            t.full_clean()

    def test_urgent_with_reason_valid(self, org, program):
        t = MaintenanceTicket(
            organization=org,
            program=program,
            urgency=MaintenanceTicket.Urgency.URGENT,
            urgent_reason="Flooding risk — immediate danger",
        )
        t.full_clean()  # should not raise

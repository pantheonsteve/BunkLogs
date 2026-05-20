"""API tests for Step 7_2 transition / bulk-transition / correct-last endpoints."""

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
from bunk_logs.core.models import Order
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.state_machine import CORRECTION_WINDOW
from bunk_logs.core.state_machine import OrderStateMachine as StateMachine

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def org():
    return Organization.objects.create(name="API SM Org", slug="api-sm-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="API SM Org Summer",
        slug="api-sm-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def cc_user(org, program):
    user = User.objects.create_user(email="cc@iso.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="C", last_name="C", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="camper_care", is_active=True,
    )
    return user


@pytest.fixture
def maint_user(org, program):
    user = User.objects.create_user(email="m@iso.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="M", last_name="M", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="maintenance", is_active=True,
    )
    return user


@pytest.fixture
def counselor_user(org, program):
    user = User.objects.create_user(email="counselor@iso.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Co", last_name="Un", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    return user


@pytest.fixture
def order(org, program):
    with organization_context(org):
        return Order.objects.create(organization=org, program=program)


@pytest.fixture
def ticket(org, program):
    with organization_context(org):
        return MaintenanceTicket.objects.create(
            organization=org, program=program, urgency="normal",
        )


@pytest.fixture
def api():
    return APIClient()


class TestOrderTransitionEndpoint:
    def test_camper_care_can_transition(self, api, org, order, cc_user):
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/orders/{order.id}/transition/",
                {"to_state": StateMachine.IN_PROGRESS, "note": "picked up"},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        data = r.json()
        assert data["content"]["status"] == StateMachine.IN_PROGRESS
        assert data["content"]["available_transitions"] == sorted(
            [StateMachine.FULFILLED, StateMachine.UNABLE_TO_FULFILL],
        )
        assert len(data["activity"]) == 1
        assert data["activity"][0]["from_state"] == StateMachine.NEW
        assert data["activity"][0]["to_state"] == StateMachine.IN_PROGRESS

    def test_counselor_cannot_transition(self, api, org, order, counselor_user):
        api.force_authenticate(user=counselor_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/orders/{order.id}/transition/",
                {"to_state": StateMachine.IN_PROGRESS},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403
        order.refresh_from_db()
        assert order.status == StateMachine.NEW

    def test_invalid_transition_returns_400(self, api, org, order, cc_user):
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/orders/{order.id}/transition/",
                {"to_state": StateMachine.NEW},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "to_state" in r.json()

    def test_missing_reason_returns_400(self, api, org, order, cc_user):
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/orders/{order.id}/transition/",
                {"to_state": StateMachine.UNABLE_TO_FULFILL, "reason": "tiny"},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 400
        assert "reason" in r.json()

    def test_unauthenticated_rejected(self, api, org, order):
        with organization_context(org):
            r = api.post(
                f"/api/v1/orders/{order.id}/transition/",
                {"to_state": StateMachine.IN_PROGRESS},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code in (401, 403)

    def test_legacy_orders_int_route_unaffected(self, api, org, cc_user):
        """The legacy ``/api/v1/orders/<int:pk>/`` route handled by the old
        ``OrderViewSet`` must still respond independently of UUID routes.
        """
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            r = api.get("/api/v1/orders/", **_hdr(org.slug))
        # Listing the legacy router endpoint should not 404 / 405; status is
        # legacy-permission-dependent but never UUID-routing failure (404).
        assert r.status_code != 404


class TestOrderCorrectLastEndpoint:
    def test_correct_within_window(self, api, org, order, cc_user):
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            api.post(
                f"/api/v1/orders/{order.id}/transition/",
                {"to_state": StateMachine.IN_PROGRESS},
                format="json",
                **_hdr(org.slug),
            )
            r = api.post(
                f"/api/v1/orders/{order.id}/correct-last/",
                {},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        order.refresh_from_db()
        assert order.status == StateMachine.NEW

    def test_correct_after_window_returns_409(self, api, org, order, cc_user):
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            api.post(
                f"/api/v1/orders/{order.id}/transition/",
                {"to_state": StateMachine.IN_PROGRESS},
                format="json",
                **_hdr(org.slug),
            )
            order.refresh_from_db()
            order.last_transition_at = timezone.now() - CORRECTION_WINDOW - timedelta(seconds=1)
            order.save(update_fields=["last_transition_at"])
            r = api.post(
                f"/api/v1/orders/{order.id}/correct-last/",
                {},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 409


class TestOrderBulkTransitionEndpoint:
    def test_bulk_transitions_all_eligible(self, api, org, program, cc_user):
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            ids = []
            for _ in range(3):
                o = Order.objects.create(organization=org, program=program)
                ids.append(str(o.id))
            r = api.post(
                "/api/v1/orders/bulk-transition/",
                {"ids": ids, "to_state": StateMachine.FULFILLED, "note": "all walked over"},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        body = r.json()
        assert len(body["transitioned"]) == 3
        assert body["failed"] == []
        assert body["missing"] == []
        for oid in ids:
            assert OrderActivityEvent.all_objects.filter(
                content_type="order", content_id=oid,
            ).count() == 1

    def test_bulk_partial_failure_returns_207(self, api, org, program, cc_user):
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            o1 = Order.objects.create(organization=org, program=program)
            o2 = Order.objects.create(
                organization=org, program=program, status=StateMachine.FULFILLED,
            )
            r = api.post(
                "/api/v1/orders/bulk-transition/",
                {
                    "ids": [str(o1.id), str(o2.id), "00000000-0000-0000-0000-000000000000"],
                    "to_state": StateMachine.FULFILLED,
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 207
        body = r.json()
        assert len(body["transitioned"]) == 1
        assert {f["id"] for f in body["failed"]} == {str(o2.id)}
        assert body["missing"] == ["00000000-0000-0000-0000-000000000000"]


class TestMaintenanceTicketEndpoints:
    def test_maintenance_can_transition_ticket(self, api, org, ticket, maint_user):
        api.force_authenticate(user=maint_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/maintenance/{ticket.id}/transition/",
                {"to_state": StateMachine.IN_PROGRESS},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        ticket.refresh_from_db()
        assert ticket.status == StateMachine.IN_PROGRESS

    def test_camper_care_cannot_transition_ticket(self, api, org, ticket, cc_user):
        api.force_authenticate(user=cc_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/maintenance/{ticket.id}/transition/",
                {"to_state": StateMachine.IN_PROGRESS},
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_maintenance_bulk_transition(self, api, org, program, maint_user):
        api.force_authenticate(user=maint_user)
        with organization_context(org):
            tickets = [
                MaintenanceTicket.objects.create(organization=org, program=program)
                for _ in range(2)
            ]
            r = api.post(
                "/api/v1/maintenance/bulk-transition/",
                {
                    "ids": [str(t.id) for t in tickets],
                    "to_state": StateMachine.IN_PROGRESS,
                },
                format="json",
                **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        assert len(r.json()["transitioned"]) == 2

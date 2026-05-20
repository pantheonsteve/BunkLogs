"""API tests for the Admin-only audit endpoints (Step 7_4)."""

from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from bunk_logs.core import audit as audit_module
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

User = get_user_model()
pytestmark = pytest.mark.django_db


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Audit API Org", slug="audit-api-org")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="Audit API Other", slug="audit-api-other")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Audit API Org Summer",
        slug="audit-api-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def other_program(other_org):
    return Program.all_objects.create(
        organization=other_org,
        name="Audit API Other Summer",
        slug="audit-api-other-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="audit-admin@example.com", password="pw")
    p = Person.all_objects.create(
        organization=org, first_name="Au", last_name="Dit", user=u,
    )
    Membership.all_objects.create(
        program=program, person=p, role="admin", is_active=True,
    )
    return u


@pytest.fixture
def uh_user(org, program):
    u = User.objects.create_user(email="audit-uh@example.com", password="pw")
    p = Person.all_objects.create(
        organization=org, first_name="Aud", last_name="UH", user=u,
    )
    Membership.all_objects.create(
        program=program, person=p, role="unit_head", is_active=True,
    )
    return u


@pytest.fixture
def admin_membership(admin_user):
    person = Person.all_objects.get(user=admin_user)
    return Membership.all_objects.get(person=person, role="admin")


@pytest.fixture
def cc_membership(org, program):
    p = Person.all_objects.create(organization=org, first_name="Cc", last_name="X")
    return Membership.all_objects.create(
        program=program, person=p, role="camper_care", is_active=True,
    )


@pytest.fixture
def order(org, program):
    with organization_context(org):
        return Order.objects.create(organization=org, program=program)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


class TestAuditAuthorization:
    def test_unauthenticated_blocked(self, api, org, order):
        r = api.get(
            "/api/v1/audit/",
            {"content_type": "order", "content_id": str(order.id)},
            **_hdr(org.slug),
        )
        assert r.status_code in (401, 403)

    def test_non_admin_blocked(self, api, org, order, uh_user):
        api.force_authenticate(user=uh_user)
        with organization_context(org):
            r = api.get(
                "/api/v1/audit/",
                {"content_type": "order", "content_id": str(order.id)},
                **_hdr(org.slug),
            )
        assert r.status_code == 403

    def test_admin_allowed(self, api, org, order, admin_user, admin_membership):
        with organization_context(org):
            audit_module.created(admin_membership, order)
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(
                "/api/v1/audit/",
                {"content_type": "order", "content_id": str(order.id)},
                **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content


# ---------------------------------------------------------------------------
# GET /audit/ (by content)
# ---------------------------------------------------------------------------


class TestAuditByContent:
    def test_returns_chronological_trail(
        self, api, org, order, admin_user, admin_membership, cc_membership,
    ):
        with organization_context(org):
            audit_module.created(admin_membership, order)
            order.transition_to("in_progress", actor=cc_membership)
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(
                "/api/v1/audit/",
                {"content_type": "order", "content_id": str(order.id)},
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        events = r.json()
        # CREATED + STATE_CHANGED (transition_to) + AUDIT_VIEW (meta) appear,
        # but AUDIT_VIEW is written *after* the response is serialised so the
        # body returns the two pre-existing events only.
        types = [e["event_type"] for e in events]
        assert types[:2] == ["created", "state_changed"]

    def test_missing_params_returns_400(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/audit/", **_hdr(org.slug))
        assert r.status_code == 400

    def test_meta_audit_view_event_written(
        self, api, org, order, admin_user, admin_membership,
    ):
        with organization_context(org):
            audit_module.created(admin_membership, order)
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            api.get(
                "/api/v1/audit/",
                {"content_type": "order", "content_id": str(order.id)},
                **_hdr(org.slug),
            )
        view_events = AuditEvent.all_objects.filter(
            event_type=AuditEvent.EventType.AUDIT_VIEW,
            content_type="order",
            content_id=str(order.id),
        )
        assert view_events.count() == 1

    def test_cross_org_rows_invisible(
        self, api, org, other_org, other_program, admin_user, admin_membership,
    ):
        # Foreign org event that should NOT show up via the requesting org's
        # admin token.
        with organization_context(other_org):
            foreign_order = Order.objects.create(
                organization=other_org, program=other_program,
            )
        # Write an event into the foreign org directly.
        AuditEvent.all_objects.create(
            event_type=AuditEvent.EventType.CREATED,
            actor_membership=None,
            content_type="order",
            content_id=str(foreign_order.id),
            organization=other_org,
            program=other_program,
        )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(
                "/api/v1/audit/",
                {"content_type": "order", "content_id": str(foreign_order.id)},
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        assert r.json() == []


# ---------------------------------------------------------------------------
# GET /audit/by-actor/
# ---------------------------------------------------------------------------


class TestAuditByActor:
    def test_filters_by_membership(
        self, api, org, order, admin_user, admin_membership, cc_membership,
    ):
        with organization_context(org):
            audit_module.created(admin_membership, order)
            audit_module.created(cc_membership, order)
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(
                "/api/v1/audit/by-actor/",
                {"membership_id": str(cc_membership.id)},
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        events = r.json()
        assert len(events) == 1
        assert events[0]["actor_membership"] == cc_membership.id

    def test_membership_id_required(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/audit/by-actor/", **_hdr(org.slug))
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# GET /audit/admin-overrides/
# ---------------------------------------------------------------------------


class TestAuditAdminOverrides:
    def test_returns_only_override_events(
        self, api, org, order, admin_user, admin_membership,
    ):
        with organization_context(org):
            audit_module.created(admin_membership, order)  # not an override
            audit_module.override_close(
                admin_membership, order, reason="duplicate ticket",
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get("/api/v1/audit/admin-overrides/", **_hdr(org.slug))
        assert r.status_code == 200
        events = r.json()
        assert len(events) == 1
        assert events[0]["event_type"] == "override_close"
        assert events[0]["is_admin_override"] is True

    def test_since_filters_by_date(
        self, api, org, order, admin_user, admin_membership,
    ):
        with organization_context(org):
            audit_module.override_close(
                admin_membership, order, reason="duplicate ticket",
            )
        api.force_authenticate(user=admin_user)
        future = (timezone.now() + timedelta(days=1)).date().isoformat()
        with organization_context(org):
            r = api.get(
                "/api/v1/audit/admin-overrides/",
                {"since": future},
                **_hdr(org.slug),
            )
        assert r.status_code == 200
        assert r.json() == []

    def test_invalid_since_returns_400(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(
                "/api/v1/audit/admin-overrides/",
                {"since": "yesterday"},
                **_hdr(org.slug),
            )
        assert r.status_code == 400

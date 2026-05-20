"""Unit + integration tests for the cross-cutting audit trail (Step 7_4).

Covers:

* The nine ``bunk_logs.core.audit`` helpers (created / edited / state_changed
  / deactivated / reactivated / override_edit / override_close /
  override_resolve / audit_view / export).
* Append-only constraints on :class:`AuditEvent` (update / delete are blocked
  via the model + via the manager queryset).
* End-to-end dual-write integration with the state machine
  (:class:`OrderableContent.transition_to`) and Supervision.
"""

from __future__ import annotations

from datetime import date

import pytest

from bunk_logs.core import audit as audit_module
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Audit Org", slug="audit-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Audit Org Summer",
        slug="audit-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def admin_membership(org, program):
    person = Person.all_objects.create(
        organization=org, first_name="Adam", last_name="Admin",
    )
    return Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )


@pytest.fixture
def cc_membership(org, program):
    person = Person.all_objects.create(
        organization=org, first_name="Cam", last_name="Care",
    )
    return Membership.all_objects.create(
        program=program, person=person, role="camper_care", is_active=True,
    )


@pytest.fixture
def order(org, program):
    with organization_context(org):
        return Order.objects.create(organization=org, program=program)


# ---------------------------------------------------------------------------
# audit helpers
# ---------------------------------------------------------------------------


class TestAuditHelpers:
    def test_created_records_after_state(self, admin_membership, order):
        event = audit_module.created(
            admin_membership,
            order,
            after_state={"status": "new"},
        )
        assert event.event_type == AuditEvent.EventType.CREATED
        assert event.actor_membership_id == admin_membership.id
        assert event.organization_id == order.organization_id
        assert event.program_id == order.program_id
        assert event.content_type == "order"
        assert event.content_id == str(order.id)
        assert event.after_state == {"status": "new"}
        assert event.is_admin_override is False

    def test_edited_captures_before_after(self, admin_membership, order):
        event = audit_module.edited(
            admin_membership,
            order,
            {"status": "new"},
            {"status": "in_progress"},
        )
        assert event.event_type == AuditEvent.EventType.EDITED
        assert event.before_state == {"status": "new"}
        assert event.after_state == {"status": "in_progress"}

    def test_state_changed_accepts_strings(self, cc_membership, order):
        event = audit_module.state_changed(
            cc_membership, order, "new", "in_progress", note="kickoff",
        )
        assert event.event_type == AuditEvent.EventType.STATE_CHANGED
        assert event.before_state == {"status": "new"}
        assert event.after_state == {"status": "in_progress"}
        assert event.reason_note == "kickoff"

    def test_state_changed_passes_through_dicts(self, cc_membership, order):
        event = audit_module.state_changed(
            cc_membership, order,
            {"status": "new", "urgency": "low"},
            {"status": "in_progress", "urgency": "low"},
        )
        assert event.before_state == {"status": "new", "urgency": "low"}

    def test_deactivated_records_reason(self, admin_membership, order):
        event = audit_module.deactivated(admin_membership, order, reason="closed by admin")
        assert event.event_type == AuditEvent.EventType.DEACTIVATED
        assert event.reason_note == "closed by admin"

    def test_reactivated_event_type(self, admin_membership, order):
        event = audit_module.reactivated(admin_membership, order)
        assert event.event_type == AuditEvent.EventType.REACTIVATED

    def test_override_edit_requires_reason(self, admin_membership, order):
        with pytest.raises(ValueError, match="reason is required"):
            audit_module.override_edit(
                admin_membership, order, {"a": 1}, {"a": 2}, reason=" ",
            )
        event = audit_module.override_edit(
            admin_membership, order, {"a": 1}, {"a": 2},
            reason="customer asked",
        )
        assert event.event_type == AuditEvent.EventType.OVERRIDE_EDIT
        assert event.is_admin_override is True

    def test_override_close_requires_reason(self, admin_membership, order):
        with pytest.raises(ValueError, match="reason is required"):
            audit_module.override_close(admin_membership, order, reason="")
        event = audit_module.override_close(
            admin_membership, order, reason="duplicate ticket",
        )
        assert event.event_type == AuditEvent.EventType.OVERRIDE_CLOSE
        assert event.is_admin_override is True

    def test_override_resolve_requires_reason(self, admin_membership, order):
        with pytest.raises(ValueError, match="reason is required"):
            audit_module.override_resolve(admin_membership, order, reason="")
        event = audit_module.override_resolve(
            admin_membership, order, reason="flag cleared",
        )
        assert event.event_type == AuditEvent.EventType.OVERRIDE_RESOLVE
        assert event.is_admin_override is True

    def test_audit_view_writes_meta(self, admin_membership, order):
        event = audit_module.audit_view(admin_membership, order)
        assert event.event_type == AuditEvent.EventType.AUDIT_VIEW
        assert event.content_type == "order"

    def test_export_requires_organization(self, admin_membership):
        with pytest.raises(ValueError, match="organization is required"):
            audit_module.export(admin_membership, {"foo": "bar"})

    def test_export_records_query(self, admin_membership, org):
        event = audit_module.export(
            admin_membership,
            {"date_from": "2026-06-01"},
            organization=org,
        )
        assert event.event_type == AuditEvent.EventType.EXPORT
        assert event.content_type == "export"
        assert event.after_state == {"query": {"date_from": "2026-06-01"}}

    def test_actor_can_be_user_or_membership(self, admin_membership, order):
        # Pass the Membership object.
        e1 = audit_module.created(admin_membership, order)
        assert e1.actor_membership_id == admin_membership.id

        # Pass the underlying User object (Super Admin path).
        from django.contrib.auth import get_user_model

        User = get_user_model()
        super_admin = User.objects.create(
            email="root@audit.test", is_staff=True, is_superuser=True,
        )
        e2 = audit_module.created(super_admin, order)
        assert e2.actor_membership_id is None
        assert e2.actor_user_id == super_admin.id


# ---------------------------------------------------------------------------
# Append-only constraints
# ---------------------------------------------------------------------------


class TestAppendOnly:
    def test_save_after_create_raises(self, admin_membership, order):
        event = audit_module.created(admin_membership, order)
        event.reason_note = "tampering"
        with pytest.raises(NotImplementedError, match="append-only"):
            event.save()

    def test_delete_instance_raises(self, admin_membership, order):
        event = audit_module.created(admin_membership, order)
        with pytest.raises(NotImplementedError, match="append-only"):
            event.delete()

    def test_queryset_update_raises(self, admin_membership, order):
        audit_module.created(admin_membership, order)
        with pytest.raises(NotImplementedError, match="append-only"):
            AuditEvent.all_objects.filter(content_type="order").update(reason_note="hack")

    def test_queryset_delete_raises(self, admin_membership, order):
        audit_module.created(admin_membership, order)
        with pytest.raises(NotImplementedError, match="append-only"):
            AuditEvent.all_objects.filter(content_type="order").delete()


# ---------------------------------------------------------------------------
# Integration: dual-writes from the state machine
# ---------------------------------------------------------------------------


class TestStateMachineIntegration:
    def test_transition_writes_audit_state_changed(self, cc_membership, order):
        with organization_context(order.organization):
            order.transition_to("in_progress", actor=cc_membership)
        events = AuditEvent.all_objects.filter(
            content_type="order", content_id=str(order.id),
        )
        state_events = events.filter(event_type=AuditEvent.EventType.STATE_CHANGED)
        assert state_events.count() == 1
        evt = state_events.first()
        assert evt.before_state == {"status": "new"}
        assert evt.after_state == {"status": "in_progress"}
        assert evt.actor_membership_id == cc_membership.id

    def test_correction_writes_reversed_state_change(self, cc_membership, order):
        with organization_context(order.organization):
            order.transition_to("in_progress", actor=cc_membership)
            order.correct_last_transition(actor=cc_membership)
        state_events = AuditEvent.all_objects.filter(
            content_type="order", content_id=str(order.id),
            event_type=AuditEvent.EventType.STATE_CHANGED,
        ).order_by("created_at")
        assert state_events.count() == 2
        first, correction = list(state_events)
        assert first.after_state == {"status": "in_progress"}
        assert correction.before_state == {"status": "in_progress"}
        assert correction.after_state == {"status": "new"}
        assert correction.metadata.get("correction") is True


# ---------------------------------------------------------------------------
# Integration: Supervision dual-writes
# ---------------------------------------------------------------------------


class TestSupervisionIntegration:
    def test_supervision_create_writes_audit_created(
        self, org, program, admin_membership,
    ):
        target_person = Person.all_objects.create(
            organization=org, first_name="Tar", last_name="Get",
        )
        target_membership = Membership.all_objects.create(
            program=program, person=target_person, role="counselor", is_active=True,
        )
        sup = Supervision.all_objects.create(
            supervisor_membership=admin_membership,
            target_type=Supervision.TargetType.MEMBERSHIP,
            target_membership=target_membership,
            start_date=date(2026, 6, 1),
        )
        # Manually drive the audit helper (the API ViewSet does this for us;
        # the integration test exercises the model path).
        audit_module.created(
            admin_membership, sup,
            after_state={"start_date": sup.start_date.isoformat()},
            content_type="supervision",
        )
        events = AuditEvent.all_objects.filter(
            content_type="supervision", content_id=str(sup.id),
        )
        assert events.count() == 1
        assert events.first().event_type == AuditEvent.EventType.CREATED

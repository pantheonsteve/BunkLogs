"""Unit tests for ``OrderStateMachine`` and ``OrderableContent`` mixin (Step 7_2)."""

from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.utils import timezone

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import OrderActivityEvent
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.state_machine import CORRECTION_WINDOW
from bunk_logs.core.state_machine import MIN_REASON_LENGTH
from bunk_logs.core.state_machine import CorrectionWindowExpiredError
from bunk_logs.core.state_machine import InvalidTransitionError
from bunk_logs.core.state_machine import MissingReasonError
from bunk_logs.core.state_machine import NoTransitionToCorrectError
from bunk_logs.core.state_machine import OrderStateMachine
from bunk_logs.core.state_machine import TransitionPlan
from bunk_logs.core.state_machine import filter_invalid_targets

pytestmark = pytest.mark.django_db


SM = OrderStateMachine


@pytest.fixture
def org(db):
    return Organization.objects.create(name="SM Org", slug="sm-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="SM Org Summer",
        slug="sm-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
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
def maint_membership(org, program):
    person = Person.all_objects.create(
        organization=org, first_name="Main", last_name="Tenance",
    )
    return Membership.all_objects.create(
        program=program, person=person, role="maintenance", is_active=True,
    )


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


# ---------------------------------------------------------------------------
# OrderStateMachine: pure validation
# ---------------------------------------------------------------------------


class TestStateMachineTable:
    def test_initial_state_is_new(self):
        assert SM.INITIAL_STATE == SM.NEW

    @pytest.mark.parametrize(
        ("from_state", "to_state", "needs_reason"),
        [
            (SM.NEW, SM.IN_PROGRESS, False),
            (SM.NEW, SM.FULFILLED, False),
            (SM.NEW, SM.UNABLE_TO_FULFILL, True),
            (SM.IN_PROGRESS, SM.FULFILLED, False),
            (SM.IN_PROGRESS, SM.UNABLE_TO_FULFILL, True),
            (SM.FULFILLED, SM.IN_PROGRESS, True),  # reopen
            (SM.UNABLE_TO_FULFILL, SM.IN_PROGRESS, True),  # reopen
        ],
    )
    def test_canonical_transitions(self, from_state, to_state, needs_reason):
        assert SM.requires_reason(from_state, to_state) is needs_reason
        if needs_reason:
            SM.validate_transition(
                from_state=from_state, to_state=to_state,
                reason="x" * MIN_REASON_LENGTH,
            )
        else:
            SM.validate_transition(from_state=from_state, to_state=to_state)

    @pytest.mark.parametrize(
        ("from_state", "to_state"),
        [
            (SM.NEW, SM.NEW),
            (SM.IN_PROGRESS, SM.NEW),
            (SM.FULFILLED, SM.UNABLE_TO_FULFILL),
            (SM.UNABLE_TO_FULFILL, SM.FULFILLED),
            (SM.FULFILLED, SM.NEW),
            (SM.UNABLE_TO_FULFILL, SM.NEW),
        ],
    )
    def test_invalid_transitions_rejected(self, from_state, to_state):
        with pytest.raises(InvalidTransitionError):
            SM.validate_transition(from_state=from_state, to_state=to_state)

    def test_unknown_state_rejected(self):
        with pytest.raises(InvalidTransitionError):
            SM.validate_transition(from_state="bogus", to_state=SM.NEW)
        with pytest.raises(InvalidTransitionError):
            SM.validate_transition(from_state=SM.NEW, to_state="bogus")

    def test_reason_required_with_min_length(self):
        with pytest.raises(MissingReasonError):
            SM.validate_transition(
                from_state=SM.NEW, to_state=SM.UNABLE_TO_FULFILL, reason="too short",
            )
        with pytest.raises(MissingReasonError):
            SM.validate_transition(
                from_state=SM.NEW, to_state=SM.UNABLE_TO_FULFILL, reason=None,
            )
        # Exactly at the min length is allowed.
        SM.validate_transition(
            from_state=SM.NEW, to_state=SM.UNABLE_TO_FULFILL,
            reason="x" * MIN_REASON_LENGTH,
        )

    def test_available_transitions_for_each_state(self):
        assert SM.available_transitions(SM.NEW) == sorted(
            [SM.IN_PROGRESS, SM.FULFILLED, SM.UNABLE_TO_FULFILL],
        )
        assert SM.available_transitions(SM.IN_PROGRESS) == sorted(
            [SM.FULFILLED, SM.UNABLE_TO_FULFILL],
        )
        assert SM.available_transitions(SM.FULFILLED) == [SM.IN_PROGRESS]
        assert SM.available_transitions(SM.UNABLE_TO_FULFILL) == [SM.IN_PROGRESS]
        assert SM.available_transitions("bogus") == []

    def test_filter_invalid_targets(self):
        assert filter_invalid_targets(
            from_states=[SM.NEW, SM.IN_PROGRESS, SM.FULFILLED],
            to_state=SM.UNABLE_TO_FULFILL,
        ) == [SM.FULFILLED]


class TestCorrectionWindow:
    def test_within_window(self):
        now = timezone.now()
        assert SM.is_within_correction_window(now - timedelta(seconds=30)) is True

    def test_at_boundary_inclusive(self):
        now = timezone.now()
        assert SM.is_within_correction_window(
            now - CORRECTION_WINDOW, now=now,
        ) is True

    def test_past_window(self):
        now = timezone.now()
        assert SM.is_within_correction_window(
            now - CORRECTION_WINDOW - timedelta(seconds=1), now=now,
        ) is False

    def test_no_transition_returns_false(self):
        assert SM.is_within_correction_window(None) is False


class TestTransitionPlan:
    def test_build_succeeds_for_valid_transition(self):
        plan = TransitionPlan.build(
            from_state=SM.NEW, to_state=SM.IN_PROGRESS, note="hi",
        )
        assert plan.from_state == SM.NEW
        assert plan.to_state == SM.IN_PROGRESS
        assert plan.requires_reason is False
        assert plan.note == "hi"
        assert plan.reason == ""

    def test_build_strips_whitespace(self):
        plan = TransitionPlan.build(
            from_state=SM.NEW, to_state=SM.UNABLE_TO_FULFILL,
            reason="  out of stock indefinitely   ",
        )
        assert plan.reason == "out of stock indefinitely"
        assert plan.requires_reason is True


# ---------------------------------------------------------------------------
# OrderableContent mixin: model integration
# ---------------------------------------------------------------------------


class TestModelTransitions:
    def test_default_status_is_new(self, order):
        assert order.status == SM.NEW
        assert order.last_transition_at is None
        assert order.last_transition_by is None

    def test_transition_records_activity(self, order, cc_membership):
        with organization_context(order.organization):
            event = order.transition_to(
                SM.IN_PROGRESS, actor=cc_membership, note="picked up",
            )
        assert order.status == SM.IN_PROGRESS
        assert order.last_transition_at is not None
        assert order.last_transition_by_id == cc_membership.id
        assert event.from_state == SM.NEW
        assert event.to_state == SM.IN_PROGRESS
        assert event.note == "picked up"
        assert event.actor_membership_id == cc_membership.id
        assert event.content_type == "order"
        assert event.content_id == order.id

    def test_transition_validation_propagates(self, order, cc_membership):
        with organization_context(order.organization):
            with pytest.raises(InvalidTransitionError):
                order.transition_to(SM.NEW, actor=cc_membership)
            with pytest.raises(MissingReasonError):
                order.transition_to(SM.UNABLE_TO_FULFILL, actor=cc_membership)

    def test_full_lifecycle_with_reopen(self, order, cc_membership):
        with organization_context(order.organization):
            order.transition_to(SM.IN_PROGRESS, actor=cc_membership)
            order.transition_to(SM.FULFILLED, actor=cc_membership)
            order.transition_to(
                SM.IN_PROGRESS, actor=cc_membership,
                reason="Counselor reported still missing supplies.",
            )
            order.transition_to(
                SM.UNABLE_TO_FULFILL, actor=cc_membership,
                reason="Item is out of stock through end of session.",
            )
        events = list(
            OrderActivityEvent.all_objects.filter(
                content_type="order", content_id=order.id,
            ).order_by("created_at"),
        )
        assert [e.to_state for e in events] == [
            SM.IN_PROGRESS, SM.FULFILLED, SM.IN_PROGRESS, SM.UNABLE_TO_FULFILL,
        ]

    def test_cross_program_actor_rejected(self, org, order, cc_membership):
        other_program = Program.all_objects.create(
            organization=org,
            name="SM Org Other",
            slug="sm-other",
            program_type="summer_camp",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
        )
        person = Person.all_objects.create(
            organization=org, first_name="Else", last_name="Where",
        )
        intruder = Membership.all_objects.create(
            program=other_program, person=person, role="camper_care", is_active=True,
        )
        from django.core.exceptions import ValidationError
        with organization_context(order.organization), pytest.raises(ValidationError):
            order.transition_to(SM.IN_PROGRESS, actor=intruder)


class TestCorrectLastTransition:
    def test_correct_within_window_reverts_status(self, order, cc_membership):
        with organization_context(order.organization):
            order.transition_to(SM.IN_PROGRESS, actor=cc_membership)
            event = order.correct_last_transition(actor=cc_membership)
        assert order.status == SM.NEW
        assert event.event_type == OrderActivityEvent.EventType.CORRECTION
        assert event.from_state == SM.IN_PROGRESS
        assert event.to_state == SM.NEW

    def test_correct_window_boundary(self, order, cc_membership):
        with organization_context(order.organization):
            order.transition_to(SM.IN_PROGRESS, actor=cc_membership)
            order.last_transition_at = timezone.now() - CORRECTION_WINDOW + timedelta(seconds=1)
            order.save(update_fields=["last_transition_at"])
            order.correct_last_transition(actor=cc_membership)
        assert order.status == SM.NEW

    def test_correct_after_window_rejected(self, order, cc_membership):
        with organization_context(order.organization):
            order.transition_to(SM.IN_PROGRESS, actor=cc_membership)
            order.last_transition_at = timezone.now() - CORRECTION_WINDOW - timedelta(seconds=1)
            order.save(update_fields=["last_transition_at"])
            with pytest.raises(CorrectionWindowExpiredError):
                order.correct_last_transition(actor=cc_membership)
        assert order.status == SM.IN_PROGRESS

    def test_correct_with_no_prior_transition(self, order, cc_membership):
        with organization_context(order.organization), pytest.raises(NoTransitionToCorrectError):
            order.correct_last_transition(actor=cc_membership)

    def test_correct_restores_prior_transition_pointer(self, order, cc_membership):
        with organization_context(order.organization):
            order.transition_to(SM.IN_PROGRESS, actor=cc_membership)
            first_at = order.last_transition_at
            order.transition_to(SM.FULFILLED, actor=cc_membership)
            order.correct_last_transition(actor=cc_membership)
        assert order.status == SM.IN_PROGRESS
        assert order.last_transition_at == first_at


class TestMaintenanceTicketBehavesIdentically:
    def test_ticket_lifecycle(self, ticket, maint_membership):
        with organization_context(ticket.organization):
            ticket.transition_to(SM.IN_PROGRESS, actor=maint_membership)
            ticket.transition_to(
                SM.UNABLE_TO_FULFILL, actor=maint_membership,
                reason="Specialty contractor needed; deferring to fall.",
            )
        assert ticket.status == SM.UNABLE_TO_FULFILL
        events = list(
            OrderActivityEvent.all_objects.filter(
                content_type="maintenance_ticket", content_id=ticket.id,
            ).order_by("created_at"),
        )
        assert len(events) == 2
        assert events[0].content_type == "maintenance_ticket"

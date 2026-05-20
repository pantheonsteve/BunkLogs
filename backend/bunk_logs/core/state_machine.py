"""Shared state machine for Camper Care orders and Maintenance tickets.

Canonical product spec: ``docs/user_stories/00_cross_cutting/order_state_machine.md``.

This module is intentionally framework-light: it does not depend on Django models
beyond the abstract ``OrderableContent`` mixin. The state machine validates a
proposed transition and surfaces structured errors that callers (model methods,
API views, admin actions) can translate into HTTP responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from collections.abc import Iterable


CORRECTION_WINDOW = timedelta(minutes=5)
MIN_REASON_LENGTH = 10


class OrderStateMachineError(ValueError):
    """Base error type for state-machine validation failures."""


class InvalidTransitionError(OrderStateMachineError):
    """Raised when a transition is not in the canonical transition table."""


class MissingReasonError(OrderStateMachineError):
    """Raised when a reason note is required but missing or too short."""


class CorrectionWindowExpiredError(OrderStateMachineError):
    """Raised when an actor tries to correct outside the 5-minute window."""


class NoTransitionToCorrectError(OrderStateMachineError):
    """Raised when ``correct_last_transition`` is called before any transition."""


class OrderStateMachine:
    """Canonical state machine governing Camper Care orders + Maintenance tickets.

    States: ``new``, ``in_progress``, ``fulfilled``, ``unable_to_fulfill``.

    Reopen is modelled as a forward transition from a closed state
    (``fulfilled`` or ``unable_to_fulfill``) back to ``in_progress``; multiple
    reopen cycles are supported because every transition writes a fresh
    activity event and resets the correction window.
    """

    NEW = "new"
    IN_PROGRESS = "in_progress"
    FULFILLED = "fulfilled"
    UNABLE_TO_FULFILL = "unable_to_fulfill"

    STATES: frozenset[str] = frozenset({
        NEW,
        IN_PROGRESS,
        FULFILLED,
        UNABLE_TO_FULFILL,
    })

    INITIAL_STATE: str = NEW

    # (from_state, to_state) -> requires_reason
    _TRANSITIONS: dict[tuple[str, str], bool] = {
        (NEW, IN_PROGRESS): False,
        (NEW, FULFILLED): False,
        (NEW, UNABLE_TO_FULFILL): True,
        (IN_PROGRESS, FULFILLED): False,
        (IN_PROGRESS, UNABLE_TO_FULFILL): True,
        # Reopen paths — a reason explaining why we are reopening is required.
        (FULFILLED, IN_PROGRESS): True,
        (UNABLE_TO_FULFILL, IN_PROGRESS): True,
    }

    @classmethod
    def is_valid_state(cls, state: str) -> bool:
        return state in cls.STATES

    @classmethod
    def available_transitions(cls, from_state: str) -> list[str]:
        """States reachable from ``from_state`` via a single transition."""
        if from_state not in cls.STATES:
            return []
        return sorted({
            to_state
            for (frm, to_state) in cls._TRANSITIONS
            if frm == from_state
        })

    @classmethod
    def requires_reason(cls, from_state: str, to_state: str) -> bool:
        """Whether the (from -> to) transition requires a non-empty reason."""
        return cls._TRANSITIONS.get((from_state, to_state), False)

    @classmethod
    def validate_transition(
        cls,
        *,
        from_state: str,
        to_state: str,
        reason: str | None = None,
    ) -> None:
        """Raise ``OrderStateMachineError`` if the transition isn't allowed.

        ``reason`` is required (and must be at least ``MIN_REASON_LENGTH`` chars)
        for transitions where ``requires_reason`` returns True.
        """
        if from_state not in cls.STATES:
            msg = f"unknown source state {from_state!r}"
            raise InvalidTransitionError(msg)
        if to_state not in cls.STATES:
            msg = f"unknown target state {to_state!r}"
            raise InvalidTransitionError(msg)
        if (from_state, to_state) not in cls._TRANSITIONS:
            msg = f"transition {from_state!r} -> {to_state!r} is not allowed"
            raise InvalidTransitionError(msg)
        if cls._TRANSITIONS[(from_state, to_state)]:
            stripped = (reason or "").strip()
            if len(stripped) < MIN_REASON_LENGTH:
                msg = (
                    f"transition {from_state!r} -> {to_state!r} requires a "
                    f"reason note of at least {MIN_REASON_LENGTH} characters"
                )
                raise MissingReasonError(msg)

    @classmethod
    def is_within_correction_window(
        cls,
        last_transition_at,
        *,
        now=None,
    ) -> bool:
        """Whether a transition timestamped at ``last_transition_at`` is still
        within the 5-minute correction window relative to ``now``.
        """
        if last_transition_at is None:
            return False
        now = now or timezone.now()
        return (now - last_transition_at) <= CORRECTION_WINDOW


@dataclass(frozen=True)
class TransitionPlan:
    """Result of validating a transition before applying it.

    Useful for views that want to validate inputs before opening a DB
    transaction or computing audit payloads.
    """

    from_state: str
    to_state: str
    requires_reason: bool
    reason: str
    note: str

    @classmethod
    def build(
        cls,
        *,
        from_state: str,
        to_state: str,
        note: str | None = None,
        reason: str | None = None,
    ) -> TransitionPlan:
        OrderStateMachine.validate_transition(
            from_state=from_state, to_state=to_state, reason=reason,
        )
        return cls(
            from_state=from_state,
            to_state=to_state,
            requires_reason=OrderStateMachine.requires_reason(from_state, to_state),
            reason=(reason or "").strip(),
            note=(note or "").strip(),
        )


def filter_invalid_targets(
    *, from_states: Iterable[str], to_state: str,
) -> list[str]:
    """Return the subset of ``from_states`` that cannot transition to ``to_state``.

    Used by bulk transition endpoints to return precise per-item errors instead
    of failing the whole batch on the first ineligible item.
    """
    invalid: list[str] = []
    for state in from_states:
        if (state, to_state) not in OrderStateMachine._TRANSITIONS:
            invalid.append(state)
    return invalid

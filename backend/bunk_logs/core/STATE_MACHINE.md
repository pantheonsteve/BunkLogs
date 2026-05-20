# Order / Ticket State Machine

> Implementation reference for Step 7_2. Canonical product spec:
> [`docs/user_stories/00_cross_cutting/order_state_machine.md`](../../../docs/user_stories/00_cross_cutting/order_state_machine.md).

A single state machine governs Camper Care orders (`core.Order`) and
Maintenance tickets (`core.MaintenanceTicket`). Encoding it once keeps the
audit / correction / reopen story uniform across both content types and
guarantees the UI affordances stay in sync.

## States

```
new ─┬─► in_progress ─┬─► fulfilled ───┐
     │                │                ▼
     ├─► fulfilled    ├─► unable_to_fulfill ──► in_progress (reopen)
     └─► unable_to_fulfill                          │
                                                    ▼
                                              … further reopens supported
```

## Transition table

| From | To | Reason note required? |
|---|---|---|
| `new` | `in_progress` | no |
| `new` | `fulfilled` | no |
| `new` | `unable_to_fulfill` | **yes** (≥10 chars) |
| `in_progress` | `fulfilled` | no |
| `in_progress` | `unable_to_fulfill` | **yes** |
| `fulfilled` | `in_progress` *(reopen)* | **yes** |
| `unable_to_fulfill` | `in_progress` *(reopen)* | **yes** |

All other transitions raise `InvalidTransitionError`. Re-opening a closed
item simply transitions it back to `in_progress` with a fresh activity event;
multiple reopen cycles are explicitly supported.

## Modules

### `bunk_logs.core.state_machine`

- `OrderStateMachine.validate_transition(from_state=..., to_state=..., reason=...)` —
  validates a proposed transition. Raises `InvalidTransitionError` or
  `MissingReasonError`.
- `OrderStateMachine.available_transitions(state)` — sorted list of legal
  next states.
- `OrderStateMachine.requires_reason(from_state, to_state)` — boolean.
- `OrderStateMachine.is_within_correction_window(last_transition_at, *, now=None)` —
  true while a transition is still inside the 5-minute correction window.
- `TransitionPlan.build(...)` — `dataclass` returned after validation, useful
  for views that want to compute audit payloads before opening a DB
  transaction.

Constants: `CORRECTION_WINDOW = timedelta(minutes=5)`,
`MIN_REASON_LENGTH = 10`.

### `bunk_logs.core.models.OrderableContent`

Abstract mixin. Concrete subclasses (`Order`, `MaintenanceTicket`) inherit
fields and behaviour:

- `status` — defaults to `new`.
- `urgency` — Low / Normal / Urgent. Used by Maintenance; stored as `""`
  for Camper Care orders unless the program opts in.
- `last_transition_at`, `last_transition_by` — pinned to the audit event's
  `created_at` so the correction window check is exact.

Methods:

- `transition_to(new_state, *, actor, note=None, reason=None)` — wraps
  state-machine validation in a DB transaction and records an
  `OrderActivityEvent`.
- `can_correct_last_transition(*, now=None)` — true within the window.
- `correct_last_transition(*, actor)` — reverts the most recent state change
  if still inside the window. Raises `CorrectionWindowExpiredError` outside
  it. Walks the activity log back one step to restore
  `last_transition_at` / `last_transition_by`.
- `available_transitions()` — instance helper that delegates to
  `OrderStateMachine`.

### `bunk_logs.core.models.OrderActivityEvent`

Append-only activity log keyed by (`content_type`, `content_id`).

> **Forward reference to Step 7_4 audit trail.** When the cross-cutting
> `core.AuditEvent` model lands, write a one-off backfill that copies the
> activity events into audit events and switch new writes over. The columns
> on `OrderActivityEvent` deliberately mirror the `AuditEvent` shape so the
> migration is mechanical.

## HTTP API

All routes live under `/api/v1/`. They require an authenticated user with
either Super Admin status, an org-Admin Membership, or an active Membership
in the **fulfilling role** for the program (`camper_care` for orders,
`maintenance` for tickets).

| Verb | Path | Body | Returns |
|---|---|---|---|
| POST | `/orders/<uuid>/transition/` | `{to_state, note?, reason?}` | `{content, activity}` |
| POST | `/orders/<uuid>/correct-last/` | `{}` | `{content, activity}` |
| POST | `/orders/bulk-transition/` | `{ids, to_state, note?, reason?}` | `{transitioned, activity_by_id, failed, missing}` (200 or 207) |
| POST | `/maintenance/<uuid>/transition/` | same as orders | same |
| POST | `/maintenance/<uuid>/correct-last/` | `{}` | same |
| POST | `/maintenance/bulk-transition/` | same as orders | same |

Bulk transitions return HTTP 207 when any item failed validation or could
not be found, with per-item error rows under `failed`. The legacy
`/api/v1/orders/<int:pk>/` viewset (Crane Lake's old order data model) is
unaffected — UUID lookups are routed before the legacy router include.

### Error contract

| HTTP | Cause | Body |
|---|---|---|
| 400 | unknown `to_state` or unsupported transition | `{to_state: "..."}` |
| 400 | `reason` missing or under 10 chars when required | `{reason: "..."}` |
| 403 | not the fulfilling role / no Membership / no org context | `{detail: "..."}` |
| 404 | unknown `<uuid>` | `{detail: "Not found."}` |
| 409 | `correct-last` outside the 5-minute window or no prior transition | `{detail: "..."}` |
| 207 | bulk transition with partial failures | `{transitioned, failed, missing}` |

## Frontend

- `frontend/src/hooks/useOrderStateMachine.js` — wraps the three endpoints.
  Returns `{availableTransitions, isWithinCorrectionWindow, transitionTo,
  correctLast, bulkTransition}`.
- `frontend/src/components/OrderStatusBadge.jsx` — colour-distinct pill,
  shared between Camper Care and Maintenance UIs.
- `frontend/src/components/OrderActivityList.jsx` — chronological timeline
  rendered from the `activity` payload returned by the API.

## Testing

- Unit tests: `backend/bunk_logs/core/test_state_machine.py` cover every
  cell of the transition table, every reason-required path, the boundary +
  out-of-window correction cases, and the cross-program actor guard.
- API tests: `backend/bunk_logs/api/tests/test_orders_state_machine.py`
  cover authorization (fulfilling role vs. counselor), invalid transitions,
  correction-window 409s, bulk partial-failure 207s, and confirm the legacy
  `/orders/` route still resolves.
- Frontend: `useOrderStateMachine.test.jsx`, `OrderStatusBadge.test.jsx`,
  `OrderActivityList.test.jsx`.

Run everything via `make test-backend` and `make test-frontend`.

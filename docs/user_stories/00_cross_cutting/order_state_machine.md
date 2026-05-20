# Order/Ticket State Machine

The same state machine governs Camper Care orders (Stories 22–23) and Maintenance tickets (Stories 30–35). Implemented once as a shared backend primitive, applied to two content types with role-specific UI affordances.

## States

```
New → In Progress → Fulfilled
                  → Unable to Fulfill

Fulfilled       → In Progress (reopen)
Unable to Fulfill → In Progress (reopen)
```

## Transition table

| From | To | Required input | Available to |
|---|---|---|---|
| New | In Progress | Optional note | Fulfilling role |
| New | Fulfilled | Optional note | Fulfilling role |
| New | Unable to Fulfill | Required reason note (min 10 chars) | Fulfilling role |
| In Progress | Fulfilled | Optional note | Fulfilling role |
| In Progress | Unable to Fulfill | Required reason note (min 10 chars) | Fulfilling role |
| Fulfilled | In Progress | Required reason note (reopen) | Fulfilling role |
| Unable to Fulfill | In Progress | Required reason note (reopen) | Fulfilling role |

## Universal rules

- Every transition captures: actor, timestamp, optional or required note per the table.
- Within 5 minutes of a transition, the actor can correct it. After 5 minutes, transitions are immutable; the only way to change state is a new forward transition.
- Submitters (counselors) read status but cannot transition.
- An order/ticket cannot be deleted. Retraction is via *Unable to Fulfill* with a reason.
- Reopen preserves the full history: original submission, prior activity, prior closure with reason, reopen with reason. Multiple reopen cycles are supported.

## Role-specific applications

- **Camper Care order** — fulfilling role is Camper Care (team-shared, not caseload-scoped). UI per Story 23.
- **Maintenance ticket** — fulfilling role is Maintenance Staff (single team queue). UI per Stories 32 and 34.

## Bulk operations

Fulfilling roles can transition multiple items at once (e.g., bulk fulfillment of items walked to a bunk in one trip). Bulk transitions share a single closing note across all selected items.

## Audit trail

Every transition writes an audit event per the audit trail spec. The complete activity history of an order/ticket is the chronological sequence of these events plus any notes added without status change.

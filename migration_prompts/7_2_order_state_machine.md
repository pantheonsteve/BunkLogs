# Step 7_2: Order/Ticket State Machine

**Goal:** Implement the shared state machine governing Camper Care orders and Maintenance tickets.

**Canonical product spec:** `docs/user_stories/00_cross_cutting/order_state_machine.md`

**Scope of this step:**

1. Backend: implement `bunk_logs/core/state_machine.py` with `OrderStateMachine` class defining states, transitions, validators, and the 5-minute correction window.
2. Backend: implement abstract `OrderableContent` mixin model in `core.models` with fields: `status`, `urgency` (optional, used by Maintenance), and methods `transition_to(new_state, actor, note=None, reason=None)`, `can_correct_last_transition()`, `correct_last_transition()`.
3. Backend: integrate state machine with `core.Order` (Camper Care orders) and `core.MaintenanceTicket` models. Both inherit from `OrderableContent`. Existing data: migration sets `status='Submitted'` on existing records (default for legacy orders if any).
4. Backend: state transitions write audit events per Step 7_4's audit trail (forward reference — if 7_4 hasn't shipped, write to a simple log table for now and migrate to audit events when 7_4 lands).
5. Backend: API endpoints under `/api/v1/orders/<id>/transition/` and `/api/v1/maintenance/<id>/transition/`. POST with `to_state`, optional `note`, optional `reason`. Validates per state machine. Returns updated content + activity history.
6. Backend: bulk transition endpoint `POST /api/v1/orders/bulk-transition/` accepting `ids[]`, `to_state`, shared `note`. Same for maintenance.
7. Backend: correction endpoint `POST /api/v1/orders/<id>/correct-last/` (and maintenance equivalent). Validates 5-minute window. Returns updated content.
8. Frontend: implement `useOrderStateMachine` hook at `frontend/src/hooks/useOrderStateMachine.js` wrapping the API calls. Returns: `availableTransitions`, `transitionTo`, `correctLast`, `isWithinCorrectionWindow`.
9. Frontend: implement `OrderStatusBadge` component visually distinct per state. `OrderActivityList` component rendering chronological state changes + notes. Both reusable across Camper Care orders (Story 23) and Maintenance tickets (Stories 31, 33, 34).
10. Tests:
    1. Backend: state machine unit tests covering every transition in the table, plus invalid transitions, plus correction window edge cases.
    2. Backend: API tests for transition endpoint, bulk transition, correction.
    3. Frontend: Vitest tests for hook and components.
11. Documentation: `bunk_logs/core/STATE_MACHINE.md` developer reference.

**Out of scope:**

- Order/ticket UI screens themselves (land in Camper Care flow Step 7_8 and Maintenance flow Step 7_10).
- Reopen-specific flow (uses same transition mechanism, surfaces in role-flow steps).

**Completion requirements per migration prompts convention. Commit scope: `feat(7_2_order_state_machine): ...`. PR title prefix: `7_2`.**

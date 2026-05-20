# Audit Trail (Step 7_4)

The cross-cutting **audit trail** is the system of record for "who did what when" across every BunkLogs content type. It backs Admin investigations (Story 59), Counselor "Edited [time]" indicators (Stories 4, 27, 41), and Camper Care / Specialist / Maintenance note-edit history (Stories 21, 26, 33).

- **Canonical product spec:** [`docs/user_stories/00_cross_cutting/audit_trail.md`](../../../docs/user_stories/00_cross_cutting/audit_trail.md)
- **State machine spec (consumer):** [`docs/user_stories/00_cross_cutting/order_state_machine.md`](../../../docs/user_stories/00_cross_cutting/order_state_machine.md)
- **Supervision spec (consumer):** [`docs/user_stories/00_cross_cutting/supervision_relationship.md`](../../../docs/user_stories/00_cross_cutting/supervision_relationship.md)

## Principle

Every mutation that materially affects content or relationships writes an immutable `AuditEvent` row. The log is the source of truth for compliance, debugging, and "Edited [time]" indicators surfaced in read views. Application code cannot update or delete audit rows — both the model and the queryset manager raise `NotImplementedError` if you try.

## Model: `core.AuditEvent`

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | Auto-generated. |
| `created_at` | DateTime (auto) | Source of chronological order. Indexed. |
| `actor_membership` | FK → `Membership` (nullable) | Who performed the action, when an in-app Membership exists. |
| `actor_user` | FK → `User` (nullable) | Captured even when no Membership row (Super Admins acting cross-org). |
| `event_type` | enum (10 values) | See below. |
| `content_type` | CharField(64) | Stable string label (`order`, `reflection`, `supervision`, `note`, `export`). |
| `content_id` | CharField(64) | Serialised PK of the related row — UUID string for `Order` / `MaintenanceTicket`, integer string for int-PK models. |
| `organization` | FK → `Organization` | Query-scoping anchor. |
| `program` | FK → `Program` (nullable) | When the event is program-scoped. |
| `before_state` / `after_state` | JSONField | Caller-supplied snapshots. |
| `reason_note` | TextField | Required for admin-override and reason-bearing transitions. |
| `is_admin_override` | Boolean (indexed) | Set automatically by the `override_*` helpers. |
| `metadata` | JSONField | Event-specific context (e.g. `activity_event_id` for state changes). |

### Managers

- `AuditEvent.objects` — tenant-scoped (`AuditEventScopedManager`). Filters by the current organization context. Used by ViewSets.
- `AuditEvent.all_objects` — cross-tenant escape hatch for migrations / platform support.

Both managers raise `NotImplementedError` on `.update()` / `.delete()`. Genuine schema-migration cleanups must use raw SQL.

### Event types (`AuditEvent.EventType`)

| Value | Helper | When to write |
| --- | --- | --- |
| `created` | `audit.created` | Content authored. |
| `edited` | `audit.edited` | In-window self-edit by the original author. |
| `state_changed` | `audit.state_changed` | Order / ticket / flag transitions (Step 7_2). |
| `deactivated` | `audit.deactivated` | Membership / Supervision end-date set. |
| `reactivated` | `audit.reactivated` | Previously deactivated row brought back. |
| `override_edit` | `audit.override_edit` | Admin edited content authored by another role. |
| `override_close` | `audit.override_close` | Admin closed an order/ticket without the fulfilling role. |
| `override_resolve` | `audit.override_resolve` | Admin resolved a flag normally handled by another role. |
| `audit_view` | `audit.audit_view` | Meta-audit: an Admin opened a content trail (Story 59 criterion 10). |
| `export` | `audit.export` | CSV export of audit data (Step 7_13). |

The four `override_*` helpers all require a non-empty `reason` and set `is_admin_override=True` automatically.

## Module: `bunk_logs.core.audit`

Single source of truth for audit writes. Call sites should never construct `AuditEvent` rows by hand — go through the helpers so:

- `actor_membership` / `actor_user` resolution is uniform (helpers accept either a `Membership`, a `User`, or any duck-typed object with `.membership` / `.user`).
- `content_type` resolution prefers an explicit override, then `content._audit_content_type_label()`, then snake-case of the class name (the same rule used by `OrderableContent._content_type_label`).
- `content_id` is always serialised to `str(...)` so int- and UUID-keyed models coexist.

### Snapshot helpers

`bunk_logs.core.models` exports compact, JSON-safe snapshot helpers consumers should reach for when building `before_state` / `after_state` payloads:

- `supervision_snapshot(supervision)`
- `reflection_snapshot(reflection)`
- `note_snapshot(note)`

If you add a new content type, add a `<thing>_snapshot()` next to the model so every audit producer reuses the same shape.

## Integration points

### State machine (Step 7_2)

`OrderableContent.transition_to` and `correct_last_transition` dual-write to both `OrderActivityEvent` (the 7_2 forward-compat shim) and `AuditEvent`. The audit row carries the `activity_event_id` in `metadata` so future backfills can join them 1:1. Once we backfill historical `OrderActivityEvent` rows into `AuditEvent` (separate follow-up PR), the legacy table can be retired.

### Supervision (Step 7_3)

`api.supervisions.SupervisionViewSet.create` writes `SupervisionEvent` and `AuditEvent.CREATED`. `partial_update` writes `DEACTIVATED` when `end_date` is set and `EDITED` when it is cleared (rare). The supervision serializer never touches audit directly; the ViewSet owns the actor resolution and snapshot calls.

### Reflections

`api.reflections.ReflectionViewSet.perform_create` / `perform_update` write `CREATED` / `EDITED`. `perform_update` re-fetches the row before saving so the snapshot reflects the pre-mutation state, and only writes `EDITED` if the snapshot actually changed.

### Notes (Steps 7_8 / 7_9 / 7_10)

Note edit views aren't built yet. When the role-specific Note views land, they should:

1. Snapshot the existing row via `note_snapshot(note)` before save.
2. Call `audit_module.edited(actor, note, before, after, content_type="note")` from `perform_update`.
3. Call `audit_module.created(actor, note, after_state=note_snapshot(note), content_type="note")` from `perform_create`.

## HTTP surface

All three endpoints are Admin-only (`IsOrgAdminOrSuperuser`), org-scoped, and read-only:

| Endpoint | Purpose | Notes |
| --- | --- | --- |
| `GET /api/v1/audit/?content_type=<type>&content_id=<id>` | Chronological trail for a specific content row. | Writes an `AUDIT_VIEW` meta-event after serialising the response. |
| `GET /api/v1/audit/by-actor/?membership_id=<id>` | Newest-first events authored by a Membership. | No meta-audit. |
| `GET /api/v1/audit/admin-overrides/?since=<YYYY-MM-DD>` | Org-wide overrides since the given date (default: 30 days). | No meta-audit. |

`content_id` is the string serialisation of the underlying PK (UUID for `Order`/`MaintenanceTicket`, integer for `Reflection`/`Note`/`Supervision`).

## Frontend usage

- `frontend/src/hooks/useAuditTrail.js` wraps all three endpoints behind a single hook with `mode` switching (`by-content` default, `by-actor`, `admin-overrides`).
- `frontend/src/components/AuditTrail.jsx` is the Admin-only chronological list. Renders `null` for non-Admin viewers (no fetch is issued).
- `frontend/src/components/EditedIndicator.jsx` is the "Edited [time]" indicator surfaced on read views for every role. Non-Admin viewers see the timestamp only; Admin viewers see the editor identity and (optionally) get a click target that opens the full `<AuditTrail/>` modal.

Both components key off `frontend/src/utils/auth/isSuperAdmin.js` for Super Admin detection and accept an explicit `isAdmin` prop for tenant Admin detection (callers compute it via Membership lookup elsewhere).

## Testing

- `backend/bunk_logs/core/test_audit.py` — unit tests for each helper, append-only constraints, and integration with the state machine / Supervision.
- `backend/bunk_logs/api/tests/test_audit_api.py` — Admin-only access, by-content / by-actor / admin-overrides routes, meta-audit logging, cross-org isolation.
- `frontend/src/hooks/__tests__/useAuditTrail.test.jsx` — mode switching, parameter forwarding, error / refetch behaviour.
- `frontend/src/components/__tests__/AuditTrail.test.jsx` — Admin gating, list rendering, empty / error states.
- `frontend/src/components/__tests__/EditedIndicator.test.jsx` — role-aware editor-identity reveal, click-to-open behaviour.

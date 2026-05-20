# Step 7_4: Audit Trail

**Goal:** Implement the cross-cutting audit trail used by reflection edits, note edits, status changes, supervision changes, and admin overrides.

**Canonical product spec:** `docs/user_stories/00_cross_cutting/audit_trail.md`

**Scope of this step:**

1. Backend: implement `core.AuditEvent` model per spec event shape. UUID id, created_at auto, actor_membership FK, event_type enum, content_type CharField, content_id UUID, organization FK, program FK nullable, before_state JSONField, after_state JSONField, reason_note TextField, is_admin_override BooleanField, metadata JSONField.
2. Backend: implement `core.audit` module with helpers:
   1. `audit.created(actor, content)` — for content creation
   2. `audit.edited(actor, content, before, after)` — for in-window edits
   3. `audit.state_changed(actor, content, before_state, after_state, note)` — for order/flag transitions
   4. `audit.deactivated(actor, content, reason)` — for Membership/Supervision ends
   5. `audit.override_edit(actor, content, before, after, reason)` — Admin override path
   6. `audit.override_close(actor, content, reason)` — Admin override close
   7. `audit.override_resolve(actor, content, reason)` — Admin override resolve
   8. `audit.audit_view(actor, target_content)` — meta-audit for Admin viewing audit trail
   9. `audit.export(actor, content_query)` — for CSV export tracking
3. Backend: integration with Step 7_2's state machine. Every order/ticket state transition calls `audit.state_changed`.
4. Backend: integration with reflection edit views (Counselor edits to camper reflection, self-reflection edits, etc.). Every save during an open edit window writes `audit.edited`.
5. Backend: integration with note edit views (Camper Care, Specialist, Maintenance). Every edit writes `audit.edited`.
6. Backend: integration with Step 7_3's Supervision. Every Supervision create/modify/end writes appropriate audit event.
7. Backend: API endpoints for Admin:
   1. `GET /api/v1/audit/?content_type=<type>&content_id=<id>` — audit trail for a specific content record. Admin only. Logs `audit.audit_view`.
   2. `GET /api/v1/audit/by-actor/?membership_id=<id>` — Admin view of an actor's audit events.
   3. `GET /api/v1/audit/admin-overrides/?since=<date>` — list of Admin override events in date range.
8. Frontend: implement `<AuditTrail>` component at `frontend/src/components/AuditTrail.jsx`. Visible to Admin only (per role check). Renders chronological list of audit events for a given content record. Props: `contentType`, `contentId`.
9. Frontend: scope-appropriate "Edited [time]" indicators on read views (no prior versions surfaced; just the indicator). Reusable component `EditedIndicator` showing time only for non-Admin roles; full audit access only for Admin via `<AuditTrail>` link.
10. Backend constraint: audit events are append-only at the application layer. No update or delete operations through any ViewSet. Custom manager raises on `update()` or `delete()` calls.
11. Tests:
    1. Backend: audit module unit tests for each helper.
    2. Backend: integration tests covering state machine transitions, reflection edits, note edits, supervision changes.
    3. Backend: API tests for audit endpoints, including Admin-only access enforcement.
    4. Frontend: Vitest tests for AuditTrail component (renders events, hides for non-Admin) and EditedIndicator.
12. Documentation: `bunk_logs/core/AUDIT_TRAIL.md` developer reference.

**Out of scope:**

- Admin override UI affordances (land in Step 7_13).
- CSV export of audit events (also Step 7_13).

**Commit scope: `feat(7_4_audit_trail): ...`. PR title prefix: `7_4`.**

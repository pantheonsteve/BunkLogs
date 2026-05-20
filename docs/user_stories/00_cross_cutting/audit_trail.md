# Audit Trail

A cross-cutting concern referenced by multiple content types: reflection edits (Stories 4, 27, 41), note edits (Stories 21, 26, 33), order/ticket state transitions (Order State Machine), Supervision changes (Supervision Relationship), and Admin overrides (Story 59).

## Principle

Every action that modifies content or relationships writes an immutable audit event. The audit log is the system of record for "who did what when," available to Admin for investigation and to platform support for debugging.

## Event shape

Every audit event has:

- `id` (UUID)
- `created_at` (DateTimeField, auto, immutable)
- `actor_membership` (FK to Membership) — who did the action
- `event_type` (enum) — see below
- `content_type` (CharField) — what kind of content was acted on
- `content_id` (UUID) — which specific record
- `organization` (FK to Organization) — for query scoping
- `program` (FK to Program, nullable) — when applicable
- `before_state` (JSONField, nullable) — content before the change, when applicable
- `after_state` (JSONField, nullable) — content after the change, when applicable
- `reason_note` (TextField, nullable) — required for Admin overrides and some state transitions
- `is_admin_override` (BooleanField) — true when the action used the Admin override path
- `metadata` (JSONField) — event-specific extra context

## Event types

- `CREATED` — content was authored
- `EDITED` — content was modified by its author within their edit window
- `STATE_CHANGED` — order/ticket state transition or flag state change
- `DEACTIVATED` — Membership or Supervision ended
- `REACTIVATED` — a deactivated Membership was reactivated
- `OVERRIDE_EDIT` — Admin edited content authored by another role
- `OVERRIDE_CLOSE` — Admin closed an order/ticket without the fulfilling role's normal path
- `OVERRIDE_RESOLVE` — Admin resolved a flag normally resolvable by another role
- `AUDIT_VIEW` — Admin viewed an audit trail (meta-audit per Story 59 criterion 10)
- `EXPORT` — Admin exported content via CSV

## Storage

Audit events are write-only and append-only at the application level. No update or delete operations are permitted through the application API. Database-level integrity follows the same constraint; only platform-support migration scripts can modify audit records, and any such modification is itself logged via the application's standard observability stack (Datadog).

## Retention

Audit events are retained for the life of the organization. Storage cost is negligible relative to the audit's value.

## Access

- **Admin** sees the full audit trail for any content within their org, accessible from any content's detail view.
- **Other roles** see scope-appropriate audit summaries:
  - Authors see edit timestamps on their own content
  - Supervisors see "Edited [time]" indicators on content they read; they do not see prior versions
  - Counselors see "Edited [time]" on co-counselor reflections; they do not see the editor's identity (UH and above see editor identity)
- **Platform support** has cross-org access via Django admin for support cases.

## Cross-content audit views

Admin can run audit queries across multiple content types:

- All Admin overrides in the last 30 days
- All edits to a specific Membership's content
- All state transitions on Camper Care orders in a date range
- All Supervision changes affecting a specific team

Available via CSV export per Story 59.

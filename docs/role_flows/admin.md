# Admin Flow — Step 7_13 (Stories 54-60)

## Overview

The Admin role owns org-wide configuration, oversight, and override
authority. Admin lands on a Story 54 home dashboard, has full read-as
access to every operational role surface (Story 59 c1), maintains
People + Memberships + Programs + Settings (Stories 55, 56, 58), and
can author / oversee reflection templates (Story 57).

This file is the running reference for the Admin namespace. PR1 lands
the foundation (dashboard + override path + audit access + viewing
banner). PR2 + PR3 fill in People / Assignments / Programs / Settings /
Global search / Templates wrapper.

## Invariants

- Every admin endpoint goes through `IsOrgAdminOrSuperuser`
  (`backend/bunk_logs/core/permissions/drf.py`). Reaching `/api/v1/admin/*`
  without an active `role="admin"` Membership in the active org returns
  403, even with a valid JWT.
- Super Admins (`is_staff` or `is_superuser`) get the same access; the
  admin-context helper records `is_super_admin=True` so audit rows can
  show "no membership" actor when needed.
- All edits that target another role's content go through the override
  path (`POST /admin/override-edit/`). The reason note is mandatory and
  the action is captured as `OVERRIDE_EDIT` so reviewers can see who
  did what and why.
- Reading an audit trail is itself audited (`AUDIT_VIEW`) per Story 59
  criterion 10.

## Backend endpoints (PR1)

| Method | Path | Story |
|--------|------|-------|
| GET | `/api/v1/admin/dashboard/` | 54 |
| POST | `/api/v1/admin/override-edit/` | 59 c8 |
| GET | `/api/v1/admin/audit/?content_type=&content_id=` | 59 c9 |
| GET | `/api/v1/admin/audit/by-actor/?membership_id=` | 7_4 |
| GET | `/api/v1/admin/audit/admin-overrides/?since=` | 7_4 |

Each path lives in `backend/bunk_logs/api/admin_flow/` (the package is
named `admin_flow` to avoid clashing with the
`bunk_logs/api/admin.py` stub the Django app system already loads).

### `GET /api/v1/admin/dashboard/`

Returns the Story 54 home payload:

```json
{
  "today": "2026-07-15",
  "org": { "id": 1, "name": "...", "slug": "...", "active_programs": [...] },
  "org_snapshot": {
    "active_people": 87,
    "memberships_by_role": [{ "role": "counselor", "count": 32 }, ...],
    "open_camper_care_orders": 4,
    "open_maintenance_tickets": 2,
    "active_flags": 1
  },
  "attention_required": [{ "key": "...", "label": "...", "count": 0, ... }, ...],
  "recent_activity": [{ "id": "...", "event_type": "...", "summary": "...", ... }]
}
```

Six attention conditions are always present (zero counts allowed) so the
frontend can render a stable grid:

1. `stale_maintenance_tickets` — open older than the
   `stale_maintenance_ticket_days` org setting (default 3).
2. `stale_camper_care_orders` — open older than the
   `stale_camper_care_order_days` org setting (default 3).
3. `unresolved_flags` — active flags older than 7 days.
4. `pending_template_review` — templates published in the last 14 days
   (the per-template Reviewed / Needs revision flag lands in PR3).
5. `digest_delivery_failures` — Maintenance digest emails that failed 3
   consecutive sends in the last 7 days.
6. `translation_pipeline_failures` — 5 or more `TranslationRecord`
   rows in `failed_terminal` state in the last 24h.

Recent activity is the latest 25 significant `AuditEvent` rows from the
last 7 days, filtered to operational content types (orders, tickets,
flags, memberships, supervisions, templates, programs, people). Routine
reflection / note edits are deliberately excluded to keep the feed
useful.

### `POST /api/v1/admin/override-edit/`

PR1 supports `content_type` of `reflection` or `note`. PR2 extends with
order / ticket / flag overrides (those have dedicated state-machine
paths). Request body:

```json
{
  "content_type": "reflection",
  "content_id": "<uuid or int>",
  "patch": { "answers": { ... } },
  "reason": "Required, non-empty"
}
```

- Missing / blank reason → 422.
- Missing content fields → 400.
- Cross-org target → 404 (the row is invisible to this Admin).
- Allowed reflection fields: `answers`, `language`, `team_visibility`,
  `is_complete`, `is_sensitive`.
- Allowed note fields: `body`, `is_sensitive`, `maintenance_visibility`,
  `language`.

The endpoint writes an `OVERRIDE_EDIT` AuditEvent with the captured
before / after snapshot via
`bunk_logs.core.audit.override_edit`.

### `/api/v1/admin/audit/...`

Mounts the existing `AuditEventViewSet` under the admin namespace so the
frontend can use one consistent path for audit reads. The per-content
trail call (`GET /admin/audit/?content_type=&content_id=`) writes the
required `AUDIT_VIEW` meta-event on every fetch.

## Frontend (PR1)

| Route | Component |
|-------|-----------|
| `/admin` | `pages/admin/Dashboard.jsx` (Story 54) |
| `/admin/dashboard` | same component, explicit path |
| `/admin/hub` | legacy `pages/admin/AdminHub.jsx` (kept for bookmarks) |

`AdminLayout` continues to wrap every `/admin/*` route with sidebar +
header. The default `/admin` index used to render the `AdminHub` cards;
PR1 swaps it for the Story 54 dashboard so an Admin lands on the
home view that matches the spec. The hub is still reachable at
`/admin/hub`.

### Shared components

- `components/admin/AdminViewingBanner.jsx` — Story 59 c2 "Viewing as
  Admin" chip. Mounted in PR1 on `MaintenanceTicketDetail.jsx`;
  PR2 wires it into the other operational detail surfaces.
- `components/admin/EditAsAdminButton.jsx` — Story 59 c8 override
  affordance. Opens a modal with a required reason textarea, posts to
  `/api/v1/admin/override-edit/`, surfaces the AuditEvent through the
  existing `AuditTrail` panel.
- `components/AuditTrail.jsx` + `EditedIndicator.jsx` from Step 7_4
  are wired into the maintenance ticket detail in PR1 as the
  representative example. PR2 wires the remaining reflection / note /
  flag detail pages.

## Out of scope for PR1

- People / Assignments / Programs / Settings CRUD (PR2)
- Global search (PR3)
- Bulk Person import UI + invitation flow (PR3)
- Templates wrapper + Mark Reviewed / Needs revision flag (PR3)
- Admin self-reflection card (deferred — already supported via the
  shared self-reflection pipeline once an Admin template is assigned)
- Cross-org Admin (Decision A1 — not a customer-facing role)
- Performance indexes for FTS (Step 7_17)

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

## Backend endpoints (PR2)

| Method | Path | Story |
|--------|------|-------|
| GET | `/api/v1/admin/people/` | 55 |
| POST | `/api/v1/admin/people/` | 55 c9 |
| GET | `/api/v1/admin/people/<id>/` | 55 c5 |
| PATCH | `/api/v1/admin/people/<id>/` | 55 |
| POST | `/api/v1/admin/people/<id>/memberships/` | 55 |
| POST | `/api/v1/admin/people/<id>/invite/` | 55 |
| PATCH | `/api/v1/admin/memberships/<id>/` | 55 |
| POST | `/api/v1/admin/memberships/<id>/deactivate/` | 55 |
| GET | `/api/v1/admin/assignments/?sub_tab=...` | 56 |
| POST | `/api/v1/admin/assignments/` | 56 |
| PATCH | `/api/v1/admin/assignments/<id>/?kind=...` | 56 |
| GET | `/api/v1/admin/programs/` | 58 |
| POST | `/api/v1/admin/programs/` | 58 |
| PATCH | `/api/v1/admin/programs/<id>/` | 58 |
| POST | `/api/v1/admin/programs/<id>/end/` | 58 c5 |
| GET | `/api/v1/admin/settings/` | 58 |
| PATCH | `/api/v1/admin/settings/` | 58 |

### People (Story 55)

- `POST /people/` requires `{first_name, last_name, membership: {program_id, role}}`. Email conflict returns **409** with an `existing_person` payload (with memberships) so the UI can offer "Add a membership to the existing record" without a duplicate.
- `Membership.role` is **immutable** post-create. `PATCH /memberships/<id>/` silently ignores `role` and `capability` because RBAC capability is derived from `role`. Use a new Membership (different role) or deactivate + recreate.
- `POST /memberships/<id>/deactivate/` is soft-delete: `is_active=False` + `end_date=today`. Historical content stays attached to the original membership (Story 56 A4).
- `POST /people/<id>/invite/` audits the invitation and returns a `{status: "queued"}` payload. The actual email send is wired separately so the audit row alone confirms "we know who invited who, when".

### Assignments (Story 56)

Single endpoint, five sub-tabs:

| `sub_tab` | Underlying model | Role |
|-----------|------------------|------|
| `uh_counselor` | `Supervision` `target_type=MEMBERSHIP` | UH supervises a counselor |
| `cc_caseload` | `Supervision` `target_type=BUNK` | CC owns a bunk caseload |
| `lt_team` | `Supervision` `target_type=ROLE_IN_PROGRAM` | LT covers a role/program slice |
| `counselor_bunk` | `AssignmentGroupMembership` `role_in_group=author` | Counselor placed on a Bunk |
| `camper_bunk` | `AssignmentGroupMembership` `role_in_group=subject` | Camper/Student placed on a Bunk/Class |

**Backdated safety invariant (Story 56 c4 + A4).** If the requested `start_date` is in the past, the server **clamps the effective start to today** and stashes the original date in `metadata.requested_start_date` on the new row. Historical reflections, notes, supervisions, and orders are *not* retroactively reattributed — they stay anchored to whichever Membership / AssignmentGroupMembership authored them at the time. The response surfaces `backdated_clamped: true` and `requested_start_date` so the UI can render an "info" banner instead of failing the form.

**Conflict warnings (Story 56 c9).** Overlapping supervisions on the same target return a non-blocking `warnings` array with the prior supervisor's name + Membership id so the UI can show "Co-supervision now in place" inline.

`PATCH /admin/assignments/<id>/?kind=supervision|group_membership` is intentionally narrow — only `end_date` (and `is_active` for group memberships) can be patched. To reassign, deactivate the old row and create a new one. This keeps audit attribution clean.

### Programs + Settings (Story 58)

`POST /admin/programs/<id>/end/` is the one **multi-table transaction** in the admin surface:

1. Refuse with 400 if any `Flag.status == ACTIVE` still references the program — those need a human decision.
2. Inside `transaction.atomic`:
   - Deactivate every active `Membership` in the program (write `DEACTIVATED` AuditEvent per row).
   - Close every open `Order` and `MaintenanceTicket` via the state machine's `unable_to_fulfill` transition (write `OVERRIDE_CLOSE` AuditEvent per row).
   - Set `Program.is_active=False`. If `today >= start_date`, also set `end_date=today`; otherwise leave `end_date` alone (the model's `end_date >= start_date` check would block updates for programs ended before they started; `is_active=False` is the canonical "ended" flag).
   - Write a `DEACTIVATED` AuditEvent on the Program itself.
3. Any uncaught exception in the block rolls back every change. Verified by `test_end_program_rolls_back_on_unexpected_failure` (injects a RuntimeError into the `override_close` helper and confirms the program / memberships / orders are unchanged).

`reason` is required (returns 422 otherwise) and lands in the audit `reason_note` on every row touched.

`PATCH /admin/settings/` accepts a partial dict of `{settings, supported_languages, rollover_hour, tag_vocabulary}` and writes a manual `AuditEvent` against `content_type="organization_settings"`. (Organization itself is not org-scoped so the standard audit helpers can't auto-derive `(org, program)`.) The frontend gates `rollover_hour` changes behind a typed-confirmation modal because changing it shifts the org's "today" anchor for every dashboard.

## Frontend (PR2)

| Route | Component | Story |
|-------|-----------|-------|
| `/admin/people` | `pages/admin/People.jsx` | 55 |
| `/admin/assignments` | `pages/admin/Assignments.jsx` | 56 |
| `/admin/settings` | `pages/admin/Settings.jsx` (Identity / Tags / Programs) | 58 |

Sidebar gets three new entries under the Admin section: People, Assignments, Settings. `Memberships`, `Templates`, `Assignment groups`, `Field keys` stay where they were so the existing admin sub-flows aren't disturbed.

### People page

- Two-pane layout: filters + list on the left, profile drawer with Identity / Memberships / Recent activity tabs on the right.
- Add Person modal (Story 55 c9) renders the 409 email-conflict response inline with an "Open existing" action that jumps to the existing person.
- Membership rows expose a "Deactivate" affordance with a required-reason inline input that posts the audit-bearing soft delete.

### Assignments page

- Sub-tab nav across the five relationships. Selecting a tab fires `GET /admin/assignments/?sub_tab=...`.
- Status pill renders Active / Ending within 7d / Recently ended / Future-dated using only the row's `start_date` / `end_date` / `is_active`.
- Create form is shape-aware per sub_tab (different field set for each). When the backend reports `backdated_clamped`, the form surfaces a yellow inline panel reminding the admin that historical content stays anchored to the prior assignment.

### Settings page

- **Identity & Localization** tab: edit supported languages list + day-rollover hour. Changing the rollover hour requires a confirm-twice gesture.
- **Tag vocabulary** tab: one-tag-per-line textarea persisted to `settings.tag_vocabulary`.
- **Programs** tab: list + Create Program form + End Program modal. The End Program modal requires the admin to type the program `slug` *and* enter a reason. On success it shows a summary card (memberships deactivated, orders closed, tickets closed, ended_at).

## Backend endpoints (PR3)

| Method | Path | Story |
|--------|------|-------|
| GET | `/api/v1/admin/search/?q=` | 60 |
| GET | `/api/v1/admin/templates/` | 57 |
| POST | `/api/v1/admin/templates/<id>/review/` | 57 |
| POST | `/api/v1/admin/people/import/preview/` | 55 + import flow |
| POST | `/api/v1/admin/people/import/commit/` | 55 + import flow |

### Global search (Story 60)

`GET /admin/search/?q=` runs a query-time
`django.contrib.postgres.search.SearchVector` across six content types,
all scoped to the active organization:

| Group | Source columns |
|-------|----------------|
| `people` | `Person.full_name + email`; `external_ids` JSON matched with `icontains` so `campminder_id` / `tbe_id` work |
| `reflections` | `Reflection.answers` text-cast (Postgres `::text`) |
| `notes` | `Note.body` |
| `orders` | `Order.title + Order.body` |
| `tickets` | `MaintenanceTicket.title + MaintenanceTicket.body` |
| `templates` | `ReflectionTemplate.name + schema` text-cast |

Up to 25 rows per group, sorted by `SearchRank` desc (then `created_at`).
Each row carries `{id, label, secondary, deep_link, content_type}` so
the frontend dropdown can deep-link without a second roundtrip.
Short queries (< 2 chars) are rejected with 400 to avoid scanning the
whole catalogue while the user is mid-type. Performance indexes
(GIN over `to_tsvector(...)`) are deferred to **Step 7_17** — the
search surface already returns under 200ms at TBE Fall 2026 scale
without them and we don't want to ship indexes the perf pass might
re-tune.

### Templates oversight (Story 57)

`GET /admin/templates/` returns **every** template the active org owns
(plus system templates surfaced read-only), regardless of who authored
them, grouped by status (`draft` / `published` / `archived`). Each row
includes a derived `pending_review` flag — `True` when the template
status is `published`, was published in the last 14 days
(`published_at` is the anchor; falls back to `created_at` for legacy
rows that pre-date the field), and has **not** been marked
`reviewed` / `needs_revision` in `metadata.review_status`.

`POST /admin/templates/<id>/review/` writes `metadata.review_status`,
`metadata.reviewed_at`, `metadata.reviewed_by_membership_id`, and
`metadata.review_note`. Allowed `review_status` values are
`reviewed`, `needs_revision`, or `cleared` (un-marks). The action is
captured as an `EDITED` AuditEvent with a `reason_note` so reviewers
can see the conversation history.

The `ReflectionTemplate.metadata` JSONField schema is intentionally
defined here rather than in a constants module: this is the only
caller and the shape is admin-facing UX, not a public contract.

### Bulk import (Story 55 + roster import flow)

`POST /admin/people/import/preview/` and `/admin/people/import/commit/`
are thin wrappers around the existing
`backend/bunk_logs/core/management/commands/import_campminder_roster.py`
and `import_tbe_roster.py` management commands. The wrappers:

1. Validate `source ∈ {campminder, tbe}` + `program_slug` resolves to
   an active program in the active org.
2. Stream the uploaded CSV to a temp file (the management commands
   take a path argument).
3. For `/preview/`, run with `--dry-run` and parse the command's
   summary stdout into `{summary: {row_count, add, change, noop, skip,
   conflict}, rows: [...first 100 classified rows...]}`.
4. For `/commit/`, run inside `transaction.atomic` so a mid-import
   failure rolls everything back. Returns the `RosterImportLog` row
   id + summary so the UI can deep-link to the log entry.

Idempotence: re-running the same CSV is a no-op (the underlying
management commands key on `external_ids.{campminder,tbe}_id`).

## Frontend (PR3)

| Route / mount | Component | Story |
|---------------|-----------|-------|
| `AdminLayout` header | `components/admin/GlobalSearch.jsx` | 60 |
| `/admin/templates` | `pages/admin/Templates.jsx` (oversight wrapper) | 57 |
| `/admin/templates/library` | existing `TemplateListPage.jsx` (kept for bookmarks) | 57 |
| `/admin/people` | `pages/admin/People.jsx` + `BulkImportModal.jsx` | 55 |

### Global search

- Header-mounted search box (debounced 300ms, minimum 2 chars).
- Results dropdown groups by content type with a deep-link `Link` per
  row. Clicking a result navigates to that detail surface.
- Closes on outside click / `Esc`.
- Only mounted inside `AdminLayout`, so non-admin routes never see the
  affordance even if a non-admin role somehow lands inside an admin URL.

### Templates oversight wrapper

- Top banner shows a count + list of `pending_review` templates.
- Each row exposes a collapsible "Review" panel with an optional note,
  `Mark reviewed` / `Needs revision` / `Clear` buttons that post to
  `/admin/templates/<id>/review/` and refetch.
- The legacy `TemplateListPage` (sort + filter library view) stays at
  `/admin/templates/library` so existing bookmarks keep working.
- Authoring (`new`, `edit`) routes are unchanged.

### People bulk import

- `pages/admin/People.jsx` gets a "Bulk import" button next to "Add
  Person" that opens `components/admin/BulkImportModal.jsx`.
- Modal walks the admin through: pick source (`campminder` / `tbe`) →
  pick program → upload CSV → run preview → confirm commit.
- Preview surfaces the per-classification counts and the first ~100
  rows so the admin can spot-check. Commit surfaces the
  `RosterImportLog` id + counts for traceability.

## Out of scope for 7_13 entirely

- Admin self-reflection card (Story 60 — deferred. Already supported
  via the shared self-reflection pipeline once an Admin template is
  assigned via Story 52.)
- Performance indexes for full-text search (Step 7_17 — perf pass).
- Cross-org Admin (Decision A1 — not a customer-facing role).
- Approval gating for template review (Decision LT8 — Admin oversight
  is annotation-only, not a publish gate).
- Anything touching the legacy
  `Session/Unit/Bunk/CamperBunkAssignment/BunkLog` hierarchy
  (Crane Lake production single-tenant data).

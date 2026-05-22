# Camper Care flow — developer reference

This document describes the **Camper Care flow** introduced in
migration step `7_8` (Stories 18-23) plus the polish iteration
shipped in `7_8d`. It is the canonical developer-facing reference
for everything CC touches in the new multi-tenant stack.

If you are looking for the product spec (acceptance criteria,
screens, copy), see `docs/user_stories/03_camper_care/STORIES.md`.
Routing prompts live in `migration_prompts/7_8_camper_care_flow.md`.

The Camper Care flow is the first role flow that has **no legacy
counterpart** — there is no Crane Lake "Camper Care log" table to
bridge against, so the data lives entirely in the new multi-tenant
model from day one. There are no dual-write signals or backfill
commands for this role.

---

## 1. Surface area

### 1.1 Backend endpoints

All CC-scoped APIs live under `/api/v1/camper-care/`:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/dashboard/?date=` | Caseload home: summary, workspace counts, units → bunks tree, self-reflection state. Cached per-viewer for 30s. |
| `GET` | `/bunks/<bunk_id>/?date=` | Per-bunk drill-down — delegates to the shared `<BunkDashboard />` payload (Step 7_7). Caseload-gated. |
| `GET` | `/campers/<camper_id>/?date=&range=` | Per-camper drill-down — delegates to the shared `<CamperDashboard />` payload. Caseload-gated. Adds `flag_history` + optional `notes_from`/`notes_to` date-range filter. |
| `GET` | `/flags/?status=&caseload_only=` | Flag workspace listing (Story 20). Returns `today` + `carried-over` buckets when `status` is omitted (active + followed_up). |
| `POST` | `/flags/<id>/follow-up/` | Move a flag to `followed_up` (interim; optional note). |
| `POST` | `/flags/<id>/resolve/` | Terminal transition. Closing note required (Story 20 c.5.ii). |
| `POST` | `/flags/<id>/reopen/` | Resurrect a resolved or followed-up flag (reason required). |
| `GET` | `/orders/?filter=&bunk_id=&item=&resolved_since=&resolved_until=` | Orders workspace listing (Story 22). |
| `POST` | `/orders/<id>/transition/` | Single-order state transition (alias to the shared state machine). |
| `POST` | `/orders/bulk-transition/` | Bulk transition (Story 23 c.5). |
| `POST` | `/notes/` | Submit a Camper Care note (Story 21). |
| `PATCH` | `/notes/<id>/` | Edit a CC note within the 24h window (Story 21 c.6). |
| `GET` | `/notes/audience/?is_sensitive=` | Audience disclosure copy for the note form (Story 21 c.10). |
| `POST` | `/self-reflection/` | Submit a CC self-reflection. Supports the `day_off` shortcut. |
| `PATCH` | `/self-reflection/<id>/` | Edit a self-reflection within today's edit window. |
| `GET` | `/self-reflection/history/` | Paginated history with no-submission gaps + day-off rows. |

Caching: the home dashboard payload is cached in Redis per-viewer
for 30 seconds and invalidated on any self-reflection submission,
order transition, flag transition, or CC note write. See
`backend/bunk_logs/api/camper_care/dashboard.py` and the
`_bust_cc_dashboard_cache` helpers in `self_reflection.py` /
`flags.py` / `orders.py`.

### 1.2 Frontend routes

| Route | Component |
|---|---|
| `/camper-care` | `CamperCareDashboard` (the home screen) |
| `/camper-care/bunks/<bunkId>` | `BunkDashboardPage` (CC wrapper) |
| `/camper-care/campers/<camperId>` | `CamperDashboardPage` (CC wrapper) |
| `/camper-care/flags` | `CamperCareFlags` (workspace) |
| `/camper-care/orders` | `CamperCareOrders` (workspace) |
| `/camper-care/notes/new` | `CamperCareNoteForm` (accepts `?camperId=`) |
| `/camper-care/self-reflection` | `CamperCareSelfReflectionPage` (create or edit-today) |
| `/camper-care/self-reflection/history` | `CamperCareSelfReflectionHistoryPage` |
| `/camper-care/self-reflection/<id>/edit` | `CamperCareSelfReflectionPage` (edit mode) |

All routes go through `ProtectedRoute` and `AppLayout`. The API
client is `frontend/src/api/camperCare.js`; the self-reflection
POST sends a `client_submission_id` for idempotent retry.

### 1.3 Data model

The CC flow writes:

- `core.Reflection` — driven by the seeded
  `camper-care-self-reflection` ReflectionTemplate (migration
  `core/0032`). `author_role_filter=["camper_care"]`,
  `subject_mode="self"`, `cadence="daily"`.
- `core.Note` (with `note_type=CAMPER_CARE` and `category` from
  `Note.Category`).
- `core.Flag` — read-only for CC except via the workspace
  transition endpoints. Flags are *raised* by upstream roles
  (Counselor self-reflection, Specialist note, UH self-reflection)
  via the helpers in `core.flag_helpers`.
- `core.Order` — read-only for CC except via the transition
  endpoints, which delegate to the shared `OrderStateMachine`
  (Step 7_2).

---

## 2. Caseload + visibility

### 2.1 Caseload resolution

A CC member's caseload is the set of bunks attached to their
membership via `AssignmentGroup` rows where the membership's
`role_in_group` is `"camper_care"`. Helpers:

- `caseload_bunks(membership, today)` — `list[Bunk]`
- `caseload_bunk_ids(membership, today)` — `set[int]` (used by the
  self-reflection validator to gate `bunk_concerns_bunks`)
- `caseload_campers(membership, today)` — every camper currently
  rostered on those bunks

Overlapping caseloads (Story 18 c.2) are intentional: multiple CC
members can supervise the same bunk and both will see it on their
home dashboard. The flag workspace defaults to `caseload_only=False`
so any CC member can pick up an at-risk flag.

### 2.2 Visibility model

Reads route through `core.content_visibility` (Step 7_1):

- Sensitive CC notes: only other CC + Leadership readers.
- Non-sensitive CC notes (`CC5`): CC + Leadership; **never**
  Counselors or Unit Heads (regression-pinned in
  `test_camper_care_notes`).
- Specialist notes: visibility filter follows `SPECIALIST_NOTE`.
- Reflections: per-template `audience_roles` + the
  `RoleVisibilityFilterBackend`.

The shared `<CamperDashboard />` builder
(`api.unit_head.camper_dashboard.build_camper_dashboard_payload`)
filters all surfaced content through `notes_visible_to(request.user)`
and `reflections_visible_for_user(request.user, qs)`. Future role
flows that reuse the same builder inherit the same gate for free.

---

## 3. Flags

### 3.1 Sources

CC flags are raised by `core.flag_helpers`:

- `raise_flag_from_specialist_note(note)` — when a specialist
  records a note flagged for CC follow-up.
- `raise_flag_from_camper_reflection(reflection)` — when a
  counselor reflection answers indicate camper concern.
- `raise_flag_from_unit_head_reflection(reflection)` — when a UH
  reflection mentions a bunk concern matching one of the CC
  member's caseload.

Each helper records the trigger pointer (`trigger_content_type` +
`trigger_content_id`) so the workspace can render a preview.

### 3.2 Workspace contract

`GET /flags/` returns rows shaped by `_flag_payload`. Step 7_8d
adds the `trigger_preview` field — a 160-char snippet pulled from
the linked content (specialist note body or reflection answers
preview) so CC readers can triage without leaving the workspace.

Loaders are registered in `_PREVIEW_LOADERS` and are best-effort:
a missing or orphaned trigger returns `trigger_preview = ""`.

### 3.3 Camper dashboard cross-link

Each flag row links the camper name to
`/camper-care/campers/<id>?flagId=<uuid>#flag-<uuid>`. The CC
camper dashboard reads `?flagId=` and scrolls the matching flag
row in `flag_history` into view (Step 7_8d). The flag history
section lists every CC flag ever raised on the camper, newest
first, with the same trigger preview.

---

## 4. Self-reflection (Step 7_8d)

The CC self-reflection mirrors the UH pattern:

- Schema fields: `day_off`, `overall_day`, `wins`, `improvements`,
  `concern`, `bunk_concerns_bunks` (CC variant uses
  `option_source: "caseload_bunks"`), `bunk_concerns_note`.
- `day_off=true` is the canonical shortcut and a *complete*
  payload — the server fills `answers: {day_off: true}`.
- Idempotent retry via `client_submission_id` (uuid).
- Edit window: today only (rolls over at the org's local
  midnight). Editing yesterday's row returns 403; the UI hides
  the affordance.
- `bunk_concerns_bunks` is validated against the CC member's
  current caseload — bunks outside the caseload are rejected with
  a 400. Test coverage in
  `test_camper_care_endpoints.TestCamperCareSelfReflection`.

History endpoint paginates with `CamperCareSelfReflectionHistoryPagination`
and surfaces gaps (`state: "missing"`), day-off rows (`state:
"day_off"`), and complete rows with a short preview + the count
of bunks flagged.

---

## 5. Polish (Step 7_8d) — UX surfaces

This step added the high-value polish items on top of the merged
7_8 stack:

| Item | Where | Notes |
|---|---|---|
| Self-reflection routes | backend + frontend | Closes broken links from the dashboard. |
| Flag → camper navigation | `Flags.jsx` + `CamperDashboardPage.jsx` | Anchored deep link with smooth scroll. |
| Trigger preview snippet | `flags.py`, `Flags.jsx` | 160-char body / answers preview per flag row. |
| Flag history rail | `camper_dashboard.py`, `CamperDashboardPage.jsx` | Newest-first history on the camper page; anchored row highlighted. |
| Notes date-range filter | `camper_dashboard.py`, `CamperDashboardPage.jsx` | Optional `notes_from` / `notes_to` query params clamp `specialist_reports` + `camper_care_notes`. CC-only — UH endpoint unchanged. |
| Session-persisted unit collapse | `Dashboard.jsx` | Per-tab via `sessionStorage[cc.dashboard.collapsedUnits]`. |

---

## 6. Testing

Backend coverage lives in
`backend/bunk_logs/api/tests/test_camper_care_endpoints.py` and
covers:

- Dashboard payload shape + caching + invalidation.
- Bunk drill-down caseload gating + role gate.
- Camper drill-down caseload gating + role gate + flag history +
  notes date-range filter.
- Flag workspace listing + transitions + trigger preview.
- Orders workspace listing + single + bulk transitions.
- Notes create + edit + 24h window + visibility (the CC5
  contract is pinned in `test_camper_care_notes`).
- Self-reflection POST + PATCH + history, including the day-off
  shortcut, caseload-gated `bunk_concerns_bunks`, idempotent
  replay, and the today-only edit window.

Frontend coverage for the CC flow lives across the per-page test
files in `frontend/src/pages/camper-care/__tests__/`. The polish
items (flag deep link, trigger preview, flag history, notes
filter, collapse persistence) are pinned in
`Flags.test.jsx`, `CamperDashboardPage.test.jsx`, and
`Dashboard.test.jsx`.

---

## 7. Troubleshooting

**The "My reflection" card links nowhere / the form 404s.**

The `camper-care-self-reflection` template wasn't seeded. Run
`python manage.py migrate core` to apply migration `core/0032`.

**A CC member can't see a bunk on their home dashboard.**

Verify:

- They have an active `camper_care` membership in the program.
- The bunk has an active `AssignmentGroup` membership with
  `role_in_group = "camper_care"` pointing at the CC member.
- The dashboard cache hasn't gone stale — pass `?nocache=1` or
  wait the 30s TTL.

**A flag's trigger preview is empty in the workspace.**

`_PREVIEW_LOADERS` is a best-effort registry. Either the
`trigger_content_type` isn't registered, the linked content was
soft-deleted, or the linked reflection has empty answers. The
flag row still renders — just without the snippet.

**The notes date-range filter doesn't change the trend grid.**

That's by design. The filter clamps only the notes lists; the
trend grid still respects the dashboard-level `range` /
`date_start` / `date_end` params so CC can look at long-window
trends while focusing the notes review on a tight window.

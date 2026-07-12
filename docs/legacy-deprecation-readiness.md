# Legacy Model Deprecation - Readiness Audit and Go/No-Go

Status: audit complete. Parity verified against a raw production snapshot (2026-07-10).
Date: 2026-07-10
Scope: read-only audit. No models, migrations, endpoints, or frontend routes were changed.
Data basis: `make sync-prod-db-raw` (unscrubbed prod copy) restored locally; reconciliation run
against it.

This document assesses whether Crane Lake (org `clc`) is safe to begin Phase 6 of the
strangler-fig migration: deprecating and removing the legacy single-tenant data model
(`Session -> Unit -> Bunk -> CamperBunkAssignment -> BunkLog`, plus `StaffLog`, the legacy
`orders` app, and their assignment tables).

The follow-up sequence, gated on a GO below, is:
- `6_1` mark legacy models read-only + read-only admin (non-destructive)
- `6_2` remove legacy API endpoints + retire legacy frontend routes
- `6_3` drop legacy tables (maintenance window, backups both sides)

---

## Executive summary

The cutover is real. Over the trailing 60 days, production write traffic goes exclusively to
auth and new-model endpoints; **no legacy write endpoint was hit at all**, and real-user page
views on legacy routes are effectively zero.

Parity is now **verified against a raw production snapshot**:
- BunkLog -> Reflection: **100%** (14607 / 14607)
- Camper -> Person: **100%** (586 / 586)
- StaffLog -> Reflection: **82%** (965 / 1181) - the ~216 gap is NCO / test-session / off-season
  staff logs outside the two migrated summer-2025 sessions
- Memberships (2238) and AssignmentGroupMemberships (2715) are populated in bulk

Verdict: **GO for `6_1`** (read-only freeze). `6_2`/`6_3` remain gated on three remediation items:

1. Decide the fate of the ~216 unmigrated StaffLog rows (migrate them, or accept dropping them
   like the legacy orders). Everything else in scope reconciles 1:1.
2. Before `6_2`/`6_3`: retire/migrate the `counselorlogs` read caller(s) and remove the
   `leadership_team/responses.py` legacy fallback (the only remaining legacy reads).
3. Legacy `orders.Order` (113 rows, 2025 supply orders): **decision = DROP** (product-confirmed
   not important). No migration or archive needed; drop with the other legacy tables in `6_3`.

---

## Legacy model inventory

| Model | App / file | Admin | Legacy REST endpoint |
|---|---|---|---|
| `Session` | `bunks/models.py` | yes | none (nested in serializers) |
| `Unit` | `bunks/models.py` | yes | `/api/v1/units/` |
| `Cabin` | `bunks/models.py` | yes | none |
| `Bunk` | `bunks/models.py` | yes | `/api/v1/bunks/`, `/api/v1/bunk/{id}/` |
| `UnitStaffAssignment` | `bunks/models.py` | yes | `/api/v1/unit-staff-assignments/` |
| `CounselorBunkAssignment` | `bunks/models.py` | yes | none (via `UnitViewSet` actions) |
| `Camper` | `campers/models.py` | yes | `/api/v1/campers/`, `/campers/{id}/logs/` |
| `CamperBunkAssignment` | `campers/models.py` | yes | `/api/v1/camper-bunk-assignments/` |
| `BunkLog` | `bunklogs/models.py` | yes | `/api/v1/bunklogs/` (+ by-date, all-by-date) |
| `StaffLog` (+ `CounselorLog`, `LeadershipLog`, `KitchenStaffLog` proxies) | `bunklogs/models.py` | yes | `/api/v1/counselorlogs/` |
| `orders.Order`, `OrderItem`, `OrderType`, `Item`, `ItemCategory`, `BunkLogsOrderTypeItemCategory` | `orders/models.py` | yes | `/api/v1/orders/`, `/items/`, `/item-categories/`, `/order-types/` |

Note: `orders.Order` (legacy, int PK, FK to `Bunk`) is a distinct model from `core.Order`
(new, UUID, org/program-scoped camper-care + maintenance requests). They are different domains.

---

## Workstream A - Production traffic verification (Datadog)

Source: Datadog APM (`service:bunklogs-backend`, `service:postgres`) and RUM
(`service:bunklogs-frontend`). Windows: APM trailing 60 days; RUM trailing 28 days (30-day
retention).

Findings:
- Legacy WRITE endpoints: **zero** POST/PUT/PATCH/DELETE hits in 60 days. All write traffic is
  auth (JWT/allauth), new reflection/camper-care/counselor/leadership/admin_flow endpoints, and
  Django admin. No `BunkLogViewSet`, `CounselorLogViewSet`, legacy `OrderViewSet`, `BunkViewSet`,
  `UnitViewSet`, `CamperViewSet`, `CamperBunkAssignmentViewSet` writes.
- Legacy TABLE writes (postgres spans, 60 days): only 5 tiny buckets, all attributable to the
  `scrub_pii` dev/staging command (`UPDATE bunklogs_stafflog SET elaboration/values_reflection`,
  `UPDATE bunklogs_bunklog SET description`) and user-deletion cascades
  (`DELETE FROM bunklogs_bunklog/stafflog/unitstaffassignment WHERE ...`). These use
  `QuerySet.update()`/bulk delete, which bypass model `save()`/`delete()`.
- Legacy READ endpoints: essentially dead except `GET CounselorLogViewSet` = 2713 reads/60d,
  concentrated in a burst (week of 2026-06-25: 1820; week of 2026-07-02: 890) that has **ceased**
  (zero in the trailing ~week). `GET UnitStaffAssignmentViewSet` = 21 (negligible).
- RUM legacy page views (28d): only `/bunk/106/2025-07-18` = 2 views (a historical 2025 log).
  All other legacy routes = 0. `/dashboard` (2671 views) is a transient role-redirect page
  (`Dashboard.jsx` forwards via `homePathForUser`), not a legacy data view.
- RUM top routes are all new: `/counselor/camper-reflections`, `/counselor`, `/tasks`,
  `/reflect`, `/admin/home`, `/my-reflections`, `/unit-head`, `/camper-care`, `/dashboards/*`.

Verdict: PASS. Caveat: identify and migrate the `counselorlogs` read caller(s) before removing
that endpoint in `6_2` (see Workstream D).

---

## Workstream B - Data parity / reconciliation

Method: `audit_legacy_data` + a read-only Django-shell reconciliation against a **raw production
snapshot** (`make sync-prod-db-raw`, restored locally). Prod legacy volume: 442 users, 586
campers, 14607 BunkLogs, 1181 StaffLogs, 751 CBA, 289 CCBA, 27 USA. Crane Lake's camper/bunk-log
data is entirely Summer 2025 (their first season), so the `migrate_clc_legacy_data` 2025 scope
covers all historical camper data - there is no pre-2025 backlog.

Verified reconciliation (raw prod):
- Camper -> Person: **586 = 586** (`Person.external_ids.legacy_camper_id`). 100%.
- BunkLog -> Reflection: **14607 = 14607** on the historical migration template (pk=18). 100%.
  The batch was written in a single 16-minute window (2026-06-04), scoped to summer-2025
  programs; 15572 total reflections in that batch = 14607 BunkLog + 965 StaffLog.
- StaffLog -> Reflection: **965 / 1181 = 82%** (pk=19). The ~216 gap corresponds to staff logs
  outside the two migrated summer-2025 sessions: New Camper Orientation (96 in-window), the
  one-day Test Session, and off-season dates (StaffLog spans 2025-06-23 -> 2026-04-27).
- Membership: **2238** (`all_objects`); AssignmentGroupMembership: **2715**. Populated in bulk.
  (An earlier "zero" reading was a query error - `.objects` is org-scoped; `.all_objects` is
  correct.)

Two real findings (neither blocks the `6_1` read-only freeze):

1. Unmigrated StaffLogs (~216). Decision needed before dropping the `StaffLog` table in `6_3`:
   migrate the out-of-session logs too, or accept dropping them (same call as legacy orders).
   These are staff self-reflections, so confirm none are worth preserving before `6_3`.
2. Duplicate `clc-legacy-*` ReflectionTemplate slugs in production. These are NOT double-migration
   duplicates - they are distinct templates that happen to share a slug:
   - `clc-legacy-counselor-daily`: pk=18 = historical 2025 migration (programs 2/3); pk=25 =
     **live 2026** counselor camper-reflection flow (program 5, submissions ongoing through today,
     4210 rows); pk=20 = 21 early rows (programs 6/7).
   - `clc-legacy-staff-log-daily`: pk=19 = historical (965); pk=24 = live 2026 (535); pk=21 = 381.
   This is a `ReflectionTemplate` (new model) hygiene issue - slug-based resolution is ambiguous.
   It is orthogonal to legacy-table removal (templates are not dropped), but recommend
   renaming/deduping the slugs. Confirms the live 2026 flows write Reflections and do **not**
   depend on legacy tables.

Legacy `orders.Order` decision (product-confirmed): 113 rows, dated 2025-06-30 -> 2025-08-12, no
counterpart in `core.Order`, semantically different (`core.Order` = camper-care + maintenance
requests). **DROP** with the other legacy tables in `6_3`; no migration or archive required.

Verdict: PASS (parity verified). One open decision: the ~216 unmigrated StaffLogs before `6_3`.

---

## Workstream C - Backend runtime dependency map

Writers to legacy models (none on the request path for user flows):
- Legacy CRUD viewsets/serializers in `api/views.py` + `api/serializers.py` (the legacy
  endpoints themselves; removed in `6_2`).
- Django admin (`bunks/admin.py`, `campers/admin.py`, `bunklogs/admin.py`, `orders/admin.py`).
- CSV import services (`bunks/services/imports.py`, `campers/services/imports.py`,
  `orders/import_views.py`) - admin-operated, not scheduled.
- Management commands: seed/date-fix/scrub/migrate. `scrub_pii` is DEBUG-only + host-allowlisted.
- Signal: `bunklogs/signals.py` StaffLog -> Reflection dual-write (kill switch
  `BUNKLOGS_DUAL_WRITE_REFLECTION`). Dormant once StaffLog stops being written.

Runtime READS of legacy tables from NEW code - the only one:
- `api/leadership_team/responses.py._legacy_staff_assignment_groups()` (lines ~382-445): a
  documented fallback that queries `CounselorBunkAssignment` and `UnitStaffAssignment` and
  resolves `AssignmentGroup.metadata__legacy_bunk_id`. Runs only when org-native resolution
  returns nothing. **Must be removed or its data migrated into AssignmentGroup metadata before
  `6_3` (drop tables).**

Confirmed NOT runtime dependencies:
- `api/permissions.py` legacy `Bunk`/`CounselorBunkAssignment` queries are DEAD - the classes
  (`IsCounselorForBunk`, `UnitHeadPermission`, etc.) are only referenced in commented-out lines
  in `views.py`.
- `counselor/*`, `camper_care/*`, `unit_head/*` modules that import legacy names use them only
  in comments/error strings (e.g. "Camper is not on this bunk."), not ORM queries.
- Scheduled cron `send_daily_reports` (messaging app) does not touch legacy models. The legacy
  `orders/send_daily_digest.py` reads legacy `Order` but is **not** scheduled in `render.yaml`.

Verdict: PASS for `6_1`. One blocker for `6_3`: the leadership-team legacy fallback.

---

## Workstream D - Frontend legacy surface

Legacy routes still mounted (not redirects) in `frontend/src/routes/routeConfig.jsx`:
`/admin-dashboard(/:date)`, `/admin-bunk-logs(/:date)`, `/dashboard/unithead`,
`/dashboard/campercare`, `/counselor-dashboard(/:date)`, `/bunk/:bunk_id/:date`
(+ `/orders/:orderId(/edit)` subroutes), `/camper/:camper_id/:date`, `/orders`,
`/orders/:orderId`, `/orders/:orderId/edit`, `/admin-staff/:staffId`.

Legacy pages/partials/forms to retire:
- Pages: `AdminDashboard`, `AdminBunkLogs`, `BunkDashboard`, `CamperDashboard`,
  `CounselorDashboard`, `UnitHeadDashboard` (legacy), `CamperCareDashboard` (legacy),
  `StaffMemberHistory`, `Orders`, `OrderDetail`, `OrderEdit`.
- Partials: `partials/bunk-dashboard/*`, `partials/admin-dashboard/CounselorLogsGrid`,
  `partials/dashboard/UnitHeadBunkGrid`, `partials/dashboard/BunkGrid`,
  `partials/dashboard/CamperCareBunkGrid` and related lists.
- Forms: `components/form/BunkLogForm`, `components/form/CounselorLogForm`.
- `Dashboard.jsx`: keep as the role redirect, but strip the legacy `BunkGrid` admin fallback.

Navigation entry points: the main Sidebar already excludes legacy routes - `Sidebar.test.jsx`
asserts links do NOT include `/admin-bunk-logs` or `/admin-dashboard`. Remaining references are
self-referential navigation inside the legacy cluster only. So there are no active nav entry
points; legacy routes are reachable only by bookmark/direct URL.

`counselorlogs` callers (migrate/retire before `6_2`): `CounselorDashboard.jsx`,
`AdminDashboard.jsx`, `StaffMemberHistory.jsx`, `components/form/CounselorLogForm.jsx`,
`partials/dashboard/UnitHeadBunkGrid.jsx`.

`/api/` redirect shim: `backend/config/api_router.py` redirects legacy paths to `/api/v1/*` and
its docstring notes it can become `urlpatterns = []` once callers are confirmed on `/api/v1/`.
`frontend/src/pages/Orders.jsx` still calls `/api/orders/` (non-v1, line 75), riding the shim to
the legacy `OrderViewSet`. Remove/repoint with the orders cluster.

Also note: `/api/v1/users/email/{email}/` (used by `AuthContext`, `UserInfo`, `BunkGrid`) embeds
legacy bunk assignments in its payload. Untangle the legacy embedding when removing `BunkGrid`.

Verdict: PASS - a clean retirement list exists; no active nav entry points remain.

---

## Workstream E - Cross-store, external, and rollback readiness

Legacy-id soft-links: stored provenance in `Program.settings` (`legacy_session_id`),
`AssignmentGroup.metadata` (`legacy_bunk_id`, `legacy_unit_id`),
`AssignmentGroupMembership.metadata` (`legacy_*_assignment_id`), `Person.external_ids`
(`legacy_camper_id`, `legacy_user_id`), `Reflection.client_submission_id`. These are copies, safe
to keep. The only code that RESOLVES a legacy id against a live legacy table at runtime is the
`leadership_team/responses.py` fallback (already flagged in Workstream C).

External / scheduled: active crons are `send_daily_reports` (clean) and
`deactivate_ended_memberships` (new models). No cron references legacy models. CSV import flows
are admin-operated and should be retired in favor of the `admin_flow` bulk import.

Backups / rollback (per `CLAUDE.md`):
- Snapshot before changes: `make sync-prod-db`; Render Postgres daily automated backups (paid).
- Code rollback: `git revert <sha>` (Render auto-deploys) or Render dashboard "Rollback".
- `6_3` runbook must: take a fresh prod backup immediately before, run the `DeleteModel`
  migration in a maintenance window, verify, take a fresh backup after.

Verdict: PASS - rollback story is documented; enforce backup-before/after for `6_3`.

---

## Go/No-Go checklist

| # | Criterion | Status | Notes |
|---|---|---|---|
| A | Zero legacy writes; near-zero legacy reads (trailing 4+ wk) | PASS | Zero write-endpoint hits/60d; reads limited to a now-ceased CounselorLog burst + 2 historical page views |
| B | In-scope legacy rows reconciled to new models | PASS | Verified on raw prod: Camper->Person 586/586, BunkLog->Reflection 14607/14607, Memberships/AGMs populated |
| B2 | Legacy `orders.Order` fate decided | RESOLVED | DROP in `6_3` (product-confirmed not important) |
| B3 | Unmigrated StaffLogs (~216) decided | OPEN | Out-of-session staff self-reflections; migrate or accept drop before `6_3` |
| C | No new-model runtime path depends on legacy tables | PASS* | Only dependency: `leadership_team/responses.py` fallback - must go before `6_3` |
| D | Legacy frontend surface enumerated; no active entry points | PASS | Retirement list compiled; Sidebar already excludes legacy routes |
| E | Backup + rollback confirmed | PASS | Documented; enforce backup-before/after for `6_3` |

Overall: **GO for `6_1`** (read-only freeze) now. `6_2` and `6_3` remain gated on the remediation
items below (StaffLog decision, counselorlogs caller migration, leadership fallback removal).

---

## Remediation checklist (ordered)

Parity gating (DONE): reconciled against a raw prod snapshot - Camper/BunkLog at 100%,
Memberships/AGMs populated. `orders.Order` decision recorded = DROP.

`6_1` (read-only freeze - GO now, non-destructive):
1. Add deprecation docstrings + `save()`/`delete()` overrides that raise on legacy models. Note:
   `scrub_pii` uses `QuerySet.update()`/bulk delete (bypasses these), so it keeps working; verify
   admin user-deletion cascades still behave (or exempt via raw SQL).
2. Make legacy admin registrations read-only.

Before `6_2` (endpoint + frontend removal):
3. Migrate/retire `counselorlogs` read callers to the new Reflection API (5 files, Workstream D).
4. Repoint/remove `Orders.jsx` `/api/orders/` caller; retire the legacy frontend cluster and its
   routes; reduce `config/api_router.py` to `urlpatterns = []`.

Before `6_3` (drop tables):
5. Decide the ~216 unmigrated StaffLog rows (migrate the out-of-session logs, or accept dropping
   them). Confirm none are worth preserving.
6. Remove the `leadership_team/responses.py` legacy fallback (or migrate its data into
   `AssignmentGroup` metadata first).
7. Fresh prod backup, run `DeleteModel` migration (including all `orders.*` tables) in a
   maintenance window, verify, fresh backup after.

Follow-up hygiene (independent of legacy-table removal):
8. Dedupe/rename the duplicate `clc-legacy-*` `ReflectionTemplate` slugs (historical vs. live-2026
   rows share a slug), to remove slug-resolution ambiguity.

# Counselor flow — developer reference

This document describes the **production counselor flow** introduced in
migration step `7_6` and the data-bridge story that ties it back to the
legacy `bunklogs.StaffLog` table during the cutover period.

It is the canonical developer-facing reference for:

- which endpoints the mobile counselor UI talks to,
- where reflection data lives in the new `core.Reflection` model,
- how the legacy `CounselorLog` form continues to work in parallel,
- and how the dual-write + backfill bridge keeps both sides in sync.

If you are looking for the product spec (acceptance criteria, screens,
copy), see `docs/user_stories/01_counselor/`. Routing prompts live in
`migration_prompts/7_6_counselor_flow.md`.

---

## 1. Surface area

### 1.1 Backend endpoints

All counselor-scoped APIs live under `/api/v1/counselor/`:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/dashboard/` | Combined home payload: bunk roster, self-reflection state, open requests, all-set state. Cached 30s. |
| `GET` | `/camper-reflections/?date=` | Bunk roster + per-camper reflection state for a date. |
| `POST` | `/camper-reflections/` | Submit a camper reflection. Idempotent via `client_submission_id`. |
| `PATCH` | `/camper-reflections/<id>/` | Edit within the org's edit window (Story 4). |
| `POST` | `/self-reflection/` | Submit a self-reflection. Supports the `day_off` shortcut. |
| `PATCH` | `/self-reflection/<id>/` | Edit a self-reflection within the edit window. |
| `GET` | `/self-reflection/history/` | Paginated history (including no-submission gaps and day-off rows). |
| `POST` | `/camper-care-requests/` | Submit a camper care request (item or generic). |
| `GET` | `/camper-care-item-suggestions/` | Active program-scoped item autocomplete labels. |
| `POST` | `/maintenance-tickets/` | Submit a maintenance ticket (multipart, supports photos). |
| `POST` | `/maintenance-tickets/<id>/photos/` | Attach an additional photo to an existing ticket. |
| `GET` | `/requests/?status=open|all` | Combined list of camper-care + maintenance requests for the counselor + co-counselors. |

Caching: the dashboard payload is cached in Redis for 30 seconds and
invalidated on any reflection submission, edit, or status change. See
`backend/bunk_logs/api/counselor/dashboard.py`.

### 1.2 Frontend routes

| Route | Component |
|---|---|
| `/counselor` | `CounselorMobileDashboard` (the home screen) |
| `/counselor/camper-reflections` | `CamperReflectionList` |
| `/counselor/camper-reflections/<camperId>` | `CamperReflectionForm` |
| `/counselor/self-reflection` | `CounselorSelfReflectionPage` (create or edit-today) |
| `/counselor/self-reflection/history` | `CounselorSelfReflectionHistoryPage` |
| `/counselor/self-reflection/<id>/edit` | `CounselorSelfReflectionPage` (edit mode) |
| `/counselor/requests` | `CounselorRequestsListPage` (combined feed) |
| `/counselor/requests/camper-care/new` | `CamperCareRequestFormPage` |
| `/counselor/requests/maintenance/new` | `MaintenanceTicketFormPage` |

All routes go through `ProtectedRoute` and `AppLayout`. The API client
is `frontend/src/api/counselor.js`; every POST in this flow sends a
`client_submission_id` generated via `crypto.randomUUID()` so the
offline queue can safely retry after reconnect.

### 1.3 Data model

The new flow writes only `core.Reflection`, `core.Order`, and
`core.MaintenanceTicket` rows. The seeded `counselor-self-reflection`
ReflectionTemplate (migration `core/0029`) drives both rendering and
validation. The legacy `bunklogs.StaffLog` / `CounselorLog` model is
**deprecated but still readable** — see §2.

---

## 2. Legacy bridge (Step 7_6g)

Crane Lake has been running on `StaffLog` since 2024 and the legacy
admin remains live during the rollout window. To keep both sides in
sync we ship **two complementary mechanisms**:

### 2.1 Dual-write signal

`bunk_logs.bunklogs.signals` registers a `post_save` receiver on
`StaffLog` (see `apps.BunklogsConfig.ready`). Every successful save
queues a `transaction.on_commit` callback that mirrors the row onto a
`core.Reflection` via `api.counselor.legacy_mapping.sync_staff_log_to_reflection`.

The receiver is **best-effort**: missing template, missing membership,
or a mid-mapper exception are logged at WARNING and swallowed so the
legacy admin path never fails because of the bridge.

A kill-switch setting `BUNKLOGS_DUAL_WRITE_REFLECTION = False`
disables the bridge entirely — useful for bulk import scripts that
already populate `core.Reflection` directly.

### 2.2 One-off backfill

`backend/bunk_logs/core/management/commands/backfill_counselor_logs.py`
walks every existing `StaffLog` row and synchronises it through the
same mapper. The command defaults to **dry-run**; pass `--apply` to
actually write.

```bash
# Dry run (no writes; prints planned counts)
python manage.py backfill_counselor_logs

# Apply the backfill
python manage.py backfill_counselor_logs --apply

# Scoped re-run after fixing a single counselor's mapping
python manage.py backfill_counselor_logs --apply --user-id 42

# Backfill a date range
python manage.py backfill_counselor_logs --apply \
    --since 2026-06-01 --until 2026-08-31
```

Output summarises `created` / `updated` / `unchanged` / `skipped`
counts and lists skip reasons (`no_person_for_user`,
`no_active_counselor_membership`, `no_counselor_template_configured`).

### 2.3 Idempotency

The bridge uses a deterministic `client_submission_id` derived as
`uuid5(NAMESPACE, "stafflog:{id}")` — see
`api.counselor.legacy_mapping.client_submission_id_for_staff_log`.

This means:

1. Re-running the backfill command never produces duplicates.
2. The dual-write signal upserts the same row each save fires; multiple
   saves of the same `StaffLog` result in exactly one Reflection.
3. A backfill followed by a stray legacy save (or vice versa) converges
   on the same Reflection without operator intervention.

### 2.4 Field mapping

The seeded counselor template declares five fields; `StaffLog` carries
eight. Mapping decisions live next to `sync_staff_log_to_reflection`
and are repeated here for searchability:

| `StaffLog` field | `Reflection.answers[...]` key | Notes |
|---|---|---|
| `day_off` (bool) | `day_off` | direct |
| `day_quality_score` (1-5) | `overall_day` | direct |
| `elaboration` (text) | `concern` | direct |
| — (new key) | `wins` | empty list (legacy form did not collect) |
| — (new key) | `improvements` | empty list |
| `support_level_score` (1-5) | `support_level_score` | extra key, preserved for audit |
| `values_reflection` (text) | `values_reflection` | extra key, preserved for audit |
| `staff_care_support_needed` (bool) | `staff_care_support_needed` | extra key, preserved for audit |
| `id` (int) | `_legacy_staff_log_id` | provenance pointer |

`Reflection.answers` is a `JSONField` — extra keys are silently kept by
the schema validator (it only checks fields declared in the schema).
The new mobile form never *renders* the extra keys, but they are
exported in admin / audit JSON.

---

## 3. Rollout plan

The bridge is designed to ship in three phases. The current branch
(`feat/7_6g_counselor_dual_write`) covers phases 1 and 2. Phase 3 is
explicitly **out of scope** for this PR and is tracked separately.

### Phase 1: dual-write on (this PR)

- Merge step 7_6g.
- Backend deploy auto-applies the bridge. `BUNKLOGS_DUAL_WRITE_REFLECTION`
  defaults to `True`. No frontend changes ride with this phase.
- Verify in production by saving a `CounselorLog` via the legacy admin
  and confirming a corresponding `core.Reflection` appears within a
  few seconds.

### Phase 2: backfill historical data

- On Render, open a one-off shell against `bunklogs-backend`:
  ```bash
  python manage.py backfill_counselor_logs --apply --batch-size 200
  ```
- The run prints incremental progress every 200 rows. Expected runtime
  for Crane Lake's ~6 months of history is < 10 minutes.
- Re-running is safe — the deterministic `client_submission_id` makes
  the second pass a no-op (`unchanged: N`).

### Phase 3: deprecate the legacy form (future PR — out of scope here)

When the new mobile flow has been live for at least one camp session
and supports all the legacy fields counselors used to fill in:

1. Mark `bunklogs.StaffLog.save()` with a `DeprecationWarning`.
2. Hide the legacy `CounselorLog` admin pages behind a feature flag.
3. After one more session of cooldown, drop the dual-write signal and
   schedule a follow-up PR to move `StaffLog` to read-only.

---

## 4. Testing

Backend coverage lives in
`backend/bunk_logs/api/tests/test_counselor_legacy_bridge.py`:

- Field mapping (incl. day-off shortcut and `junior_counselor` role).
- Mapper idempotency (re-run produces `unchanged`).
- Update path on `StaffLog` edits.
- Skip reasons (`no_person_for_user`, `no_active_counselor_membership`,
  `no_counselor_template_configured`).
- Management command dry-run vs `--apply`, date-range filter, replay,
  skip-reason reporting.
- Signal: on-commit mirror, update-on-resave, kill-switch,
  best-effort skip.

Frontend coverage for the new counselor flow lives across the per-page
test files in `frontend/src/pages/counselor/__tests__/`.

---

## 5. Troubleshooting

**The mirror Reflection is missing for a recent StaffLog row.**

Check the Django log for `Dual-write StaffLog->Reflection failed for
staff_log_id=...`. Common causes:

- The user has no `Person` row in the new model (run the staff import
  command, then re-save the StaffLog or run a scoped backfill via
  `--user-id`).
- The user has no active `counselor` / `junior_counselor` Membership in
  any program. Confirm in the admin.
- No counselor self-reflection template is configured for the org. The
  global seed (`organization IS NULL`, slug `counselor-self-reflection`)
  is sufficient — re-run migration `core/0029` if it's missing.

**Backfill skips everything with `no_counselor_template_configured`.**

The seeded template migration didn't run on this database. Run
`python manage.py migrate core` to re-apply.

**Duplicate rows in `core.Reflection` for a single StaffLog.**

Shouldn't be possible with the deterministic `client_submission_id`
constraint. If you see it, check that the `Reflection.program` FK is
the same on both rows; the unique constraint is keyed
`(program, client_submission_id)`. A counselor with active memberships
across multiple programs would resolve to the *newest* membership —
keep an eye on that during the multi-tenant expansion.

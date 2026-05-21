# Step 7_6: Counselor Flow

**Goal:** Implement the Counselor flow per Stories 1-9.

**Canonical product spec:** `docs/user_stories/01_counselor/*.md`

**Depends on:** 7_1 (visibility), 7_2 (state machine), 7_4 (audit), 7_5 (i18n).

**Scope of this step:**

1. Reuse and refactor: existing CounselorLog component (per `COUNSELOR_LOG_COMPLETION_SUMMARY.md`) is the existing self-reflection. Refactor to use `core.Reflection` model with `counselor` role template instead of standalone `CounselorLog` model. Migration: move existing data into Reflection records preserving content. Deprecate `CounselorLog` model per "Mark as deprecated" pattern from migration prompts 6_1.
2. Backend: API endpoints under `/api/v1/counselor/`:
   1. `GET /api/v1/counselor/dashboard/` — returns dashboard payload: bunk roster with reflection states (Story 3), self-reflection state (Story 5), open requests (Story 7-8), all-set state (Story 9).
   2. `GET /api/v1/counselor/camper-reflections/?date=<>` — bunk roster for the date.
   3. `POST /api/v1/counselor/camper-reflections/` — submit camper reflection.
   4. `PATCH /api/v1/counselor/camper-reflections/<id>/` — edit within window (Story 4).
   5. `POST /api/v1/counselor/self-reflection/` — submit self-reflection.
   6. `PATCH /api/v1/counselor/self-reflection/<id>/` — edit within window (Story 6).
   7. `GET /api/v1/counselor/self-reflection/history/` — history view.
   8. `POST /api/v1/counselor/camper-care-requests/` — submit camper-care request (Story 7).
   9. `POST /api/v1/counselor/maintenance-tickets/` — submit maintenance ticket (Story 8).
   10. `GET /api/v1/counselor/requests/` — list user's and co-counselors' requests (per C4).
3. Backend: server-side derivation of all-set state per Story 9 criterion 1. Cached for 30 seconds. Cache invalidates on reflection submission, edit, or status change.
4. Backend: rollover boundary logic centralized in `core.time_utils.get_today(org)` and used throughout. Camp org default 04:00, religious-school 00:00 (per Story 58).
5. Backend: enforce edit-window rule (Stories 4, 6) at API layer. Beyond window: 403 + clear error.
6. Frontend: implement Counselor dashboard at `frontend/src/pages/counselor/Dashboard.jsx`. Three sections per Story 2. All-set state per Story 9.
7. Frontend: implement `CamperReflectionList` and `CamperReflectionForm` at `frontend/src/pages/counselor/camper-reflections/`. Mobile-first, network-tolerant submission per Story 8 criterion 6.
8. Frontend: refactor self-reflection form to support day-off toggle per Story 5 criterion 3.
9. Frontend: implement requests submission flow per Stories 7 and 8. Combined dashboard view per Story 7 criterion 3. Photo capture per Story 8 criterion 3 using device-native camera/library.
10. Frontend: implement urgency selector per Story 8 criterion 1.v. Required reason when Urgent.
11. Frontend: use AudienceDisclosure (Step 7_1) on all forms. Use TranslationDisplay (Step 7_5) where relevant.
12. Tests:
    1. Backend: tests per acceptance criterion for each story. Particular attention to: cross-counselor edit accountability (Story 4 criteria 3, 5); all-set state derivation (Story 9 criterion 5).
    2. Frontend: Vitest tests for dashboard rendering, state transitions, form submissions. Playwright or Cypress end-to-end tests for the "submit camper reflection → return to list with state updated" flow.
13. Documentation: `docs/role_flows/counselor.md` developer-facing reference.
14. Step 7_6g (dual-write + backfill bridge): see `docs/role_flows/counselor.md` §2.
    Ships in phases — dual-write defaults on; backfill is a one-off `python manage.py backfill_counselor_logs --apply` once the bridge is live. Both paths share the same deterministic UUID5 idempotency key, so any order of operations converges on the same Reflection rows.

**Out of scope:**

- Maintenance ticket fulfillment side (Step 7_10).
- Camper Care order fulfillment side (Step 7_8).

**Commit scope: `feat(7_6_counselor_flow): ...`. PR title prefix: `7_6`.**

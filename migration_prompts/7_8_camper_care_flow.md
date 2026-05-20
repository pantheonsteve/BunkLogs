# Step 7_8: Camper Care Flow

**Goal:** Implement the Camper Care (Wellness) flow per Stories 18-23.

**Canonical product spec:** `docs/user_stories/03_camper_care/STORIES.md`

**Depends on:** 7_1, 7_2, 7_3, 7_4, 7_5, 7_7 (reuses Bunk Dashboard component).

**Scope of this step:**

1. Backend: create `core.Flag` model. Fields: `subject_camper` FK, `raised_by_membership` FK, `trigger_content_type` CharField, `trigger_content_id` UUID, `status` enum (Active/Followed Up/Resolved), `flagged_for_role` CharField (e.g., 'camper_care'), `created_at`, `resolved_at` nullable, `resolved_by_membership` FK nullable. State changes per Story 20 criterion 5 with audit events.
2. Backend: Specialist note flagging integration. When Specialist note submitted with `flag_for_camper_care=True`, create Flag pointing to the note (Step 7_9 ships the Specialist form, but flag wiring lives here).
3. Backend: API endpoints under `/api/v1/camper-care/`:
   1. `GET /api/v1/camper-care/dashboard/` — caseload tree, completion summary, flag count, attention badges (Story 18).
   2. `GET /api/v1/camper-care/flags/?status=<>` — Flagged campers workspace (Story 20).
   3. `POST /api/v1/camper-care/flags/<id>/follow-up/` (Story 20 criterion 5.i).
   4. `POST /api/v1/camper-care/flags/<id>/resolve/` (criterion 5.ii).
   5. `POST /api/v1/camper-care/flags/<id>/reopen/` (criterion 5.iii).
   6. `GET /api/v1/camper-care/orders/` — orders workspace (Story 22).
   7. `POST /api/v1/camper-care/orders/<id>/transition/` and bulk endpoint via state machine.
   8. `POST /api/v1/camper-care/notes/` — submit Camper Care note (Story 21).
   9. `PATCH /api/v1/camper-care/notes/<id>/` — edit within 24h window.
4. Backend: implement `caseload_campers` query helper (Step 7_3 dependency satisfied) used throughout.
5. Backend: order routing — team-shared per CC7. All Camper Care orders visible to all Camper Care members in the program.
6. Backend: Camper Care note visibility per CC5 (more restrictive than loose version): Camper Care, Health Center, Special Diets, LT, Admin. NOT Counselors or UH.
7. Frontend: implement Camper Care dashboard at `frontend/src/pages/camper-care/Dashboard.jsx`. Caseload tree, flag workspace entry, orders workspace entry, My reflection card.
8. Frontend: implement Flagged campers workspace at `frontend/src/pages/camper-care/Flags.jsx`. Three-state Flag model (Active/Followed Up/Resolved) per Story 20.
9. Frontend: implement Orders workspace at `frontend/src/pages/camper-care/Orders.jsx`. Three-section view (New/In Progress/Resolved) per Story 22. Bulk fulfillment per Story 23 criterion 5.
10. Frontend: implement Camper Care notes form using AudienceDisclosure component, with **Sensitive** checkbox dynamically updating the disclosure. Note section on Camper Dashboard via CamperDashboard component (Step 7_7).
11. Tests:
    1. Backend: flag lifecycle tests (Active → Followed Up → Resolved → Reopen).
    2. Backend: order routing tests (team-shared visibility).
    3. Backend: Camper Care note visibility tests confirming Counselor/UH do not see them (regression risk).
    4. Frontend: Vitest tests for Flag workspace, Orders workspace, Notes form.
12. Documentation: `docs/role_flows/camper_care.md`.

**Commit scope: `feat(7_8_camper_care_flow): ...`. PR title prefix: `7_8`.**

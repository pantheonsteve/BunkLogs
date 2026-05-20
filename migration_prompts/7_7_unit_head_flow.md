# Step 7_7: Unit Head Flow

**Goal:** Implement the Unit Head flow per Stories 10-17.

**Canonical product spec:** `docs/user_stories/02_unit_head/STORIES.md`

**Depends on:** 7_1, 7_2, 7_3 (supervision is critical here), 7_4, 7_5, 7_6.

**Scope of this step:**

1. Backend: API endpoints under `/api/v1/unit-head/`:
   1. `GET /api/v1/unit-head/dashboard/` — bunks under supervision with completion + attention badges (Story 10).
   2. `GET /api/v1/unit-head/bunks/<bunk_id>/?date=<>` — Bunk Dashboard payload (Story 11): flagged campers, off-camp campers, bunk concerns, score grid, orders, specialist reports.
   3. `GET /api/v1/unit-head/campers/<camper_id>/?date=<>&range=<>` — Camper Dashboard payload (Story 13): full reflection, scores, trend graph data, flags, specialist reports, camper care notes (visibility-filtered).
   4. `POST /api/v1/unit-head/self-reflection/` (Story 16) and `PATCH` for edits (Story 17).
   5. `GET /api/v1/unit-head/self-reflection/history/` — Story 17.
2. Backend: implement `bunks_for_uh` query helper (Step 7_3) and use throughout UH endpoints.
3. Backend: implement attention badge derivation: Help requested, Off-camp, Bunk concerns, Low completion. Low completion threshold from org-configured "expected by" time (Story 58).
4. Backend: implement Camper Dashboard component data API. This is the shared payload also used by LT (Step 7_12), Camper Care (Step 7_8), and Admin (Step 7_13). Visibility filtering applied per role.
5. Backend: bunk concerns surface — extract from Counselor self-reflection's optional "Bunk concerns" field (per UH2). When populated, surface in Story 11 criterion 1.iv.
6. Frontend: implement Unit Head dashboard at `frontend/src/pages/unit-head/Dashboard.jsx`.
7. Frontend: implement `BunkDashboard` component at `frontend/src/components/BunkDashboard.jsx` per Story 11. Used by UH; will be reused by Camper Care (Step 7_8), LT (Step 7_12), Admin (Step 7_13).
8. Frontend: implement `CamperDashboard` component at `frontend/src/components/CamperDashboard.jsx` per Story 13. Includes trend graph using Recharts (already in package.json). Used by all roles per visibility filtering.
9. Frontend: implement `ScoreGrid` component at `frontend/src/components/ScoreGrid.jsx` per Story 12. Mobile-friendly horizontal scroll with pinned camper names; consistent color scale.
10. Frontend: UH self-reflection form including optional "Bunk concerns" field per Story 16 criterion 7.
11. Tests:
    1. Backend: per acceptance criterion. Particular attention to: supervision resolution (Story 10 criterion 5); cross-camper data correctness in Camper Dashboard (Story 13).
    2. Frontend: Vitest tests for BunkDashboard, CamperDashboard, ScoreGrid components.
12. Documentation: `docs/role_flows/unit_head.md`.

**Commit scope: `feat(7_7_unit_head_flow): ...`. PR title prefix: `7_7`.**

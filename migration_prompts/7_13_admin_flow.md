# Step 7_13: Admin Flow

**Goal:** Implement the Admin flow per Stories 54-60.

**Canonical product spec:** `docs/user_stories/08_admin/STORIES.md`

**Depends on:** 7_1, 7_2, 7_3 (heavy), 7_4 (heavy), 7_5, 7_7 (reuses dashboards), 7_12 (template builder).

**Scope of this step:**

1. Backend: API endpoints under `/api/v1/admin/`. All require Admin role check.
   1. `GET /api/v1/admin/dashboard/` — Org snapshot + Attention required + Recent activity (Story 54).
   2. `GET /api/v1/admin/people/` and CRUD endpoints (Story 55).
   3. `GET /api/v1/admin/assignments/` and CRUD endpoints (Story 56).
   4. `GET /api/v1/admin/templates/` — full template library (Story 57).
   5. `GET /api/v1/admin/settings/` and PATCH for org settings (Story 58).
   6. `GET /api/v1/admin/programs/` and CRUD endpoints (Story 58).
   7. `POST /api/v1/admin/programs/<id>/end/` — End Program action with bulk Membership deactivation (per A3).
   8. `GET /api/v1/admin/search/?q=<>` — Global search (Story 59).
   9. `GET /api/v1/admin/audit/?content_type=<>&content_id=<>` — Audit trail viewer (Story 59 + Step 7_4).
   10. `POST /api/v1/admin/override-edit/` — Admin override path with required reason (Story 59 criterion 8).
2. Backend: Attention conditions surface per Story 54 criterion 5. Six conditions implemented as queryset filters surfaced via dashboard endpoint.
3. Backend: Recent activity feed per Story 54 criterion 6. Rate-limited to significant events; routine submissions/notes excluded.
4. Backend: Global search per Story 59 criterion 6 using PostgreSQL FTS. Includes People, Reflections, Notes (incl. sensitive), Orders/tickets, Templates. Scoped to active org. Sub-2-second target per A10.
5. Backend: Admin override actions write distinct audit events per Step 7_4 (`OVERRIDE_EDIT`, `OVERRIDE_CLOSE`, `OVERRIDE_RESOLVE`) with required reason.
6. Backend: backdated Supervision creation/modification per Story 56 criterion 4 — forward from correction date only. Historical content NOT reattributed. Validate at API level.
7. Backend: End Program transaction — deactivates all Memberships scoped to program, closes any open orders/flags, in single transaction (per A3 and Story 58 criterion 5).
8. Frontend: implement Admin dashboard at `frontend/src/pages/admin/Dashboard.jsx`. Visually distinct from operational role dashboards per Story 54 criterion 4.
9. Frontend: implement People management at `frontend/src/pages/admin/People.jsx` per Story 55. Bulk import flows (Campminder CSV, TBE roster CSV).
10. Frontend: implement Assignments management at `frontend/src/pages/admin/Assignments.jsx` per Story 56. Sub-tabs per assignment type with consistent two-pane UX.
11. Frontend: implement Templates surface at `frontend/src/pages/admin/Templates.jsx`. Wraps template builder from Step 7_12 with Admin's broader privileges + pending review surface.
12. Frontend: implement Programs/settings at `frontend/src/pages/admin/Settings.jsx` per Story 58.
13. Frontend: implement Global search at `frontend/src/components/admin/GlobalSearch.jsx`. Header-accessible search box; results grouped by content type.
14. Frontend: implement Audit trail viewer integration on every content detail view for Admin (using component from Step 7_4).
15. Frontend: implement "Viewing as Admin" indicator on operational role dashboards when accessed by Admin (per Story 59 criterion 2).
16. Frontend: implement explicit "Edit as Admin" override affordance with required reason field on content where override is permitted.
17. Tests:
    1. Backend: people CRUD + bulk import + invitation flow.
    2. Backend: assignment CRUD with conflict warnings.
    3. Backend: End Program transaction including Membership deactivation, open orders closing, audit logging.
    4. Backend: global search performance with realistic org-size data (e.g., 5 years of camp data).
    5. Backend: audit-view access logging (meta-audit).
    6. Backend: backdated assignment per Story 56 criterion 4 — confirms historical content not reattributed.
    7. Frontend: Admin dashboard, People, Assignments, Templates, Search component tests.
18. Documentation: `docs/role_flows/admin.md`.

**Commit scope: `feat(7_13_admin_flow): ...`. PR title prefix: `7_13`.**

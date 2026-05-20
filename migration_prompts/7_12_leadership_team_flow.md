# Step 7_12: Leadership Team Flow

**Goal:** Implement the Leadership Team flow per Stories 45-53 including the Tier 1 template builder.

**Canonical product spec:** `docs/user_stories/07_leadership_team/STORIES.md` (note Tier 1 scope statement at top)

**Depends on:** 7_1, 7_2, 7_3, 7_4, 7_5, 7_6 (reflection submission patterns), 7_7 (Bunk Dashboard + Camper Dashboard).

**Scope of this step:**

1. Backend: API endpoints under `/api/v1/leadership-team/`:
   1. `GET /api/v1/leadership-team/dashboard/` — supervised teams + attention badges + bunks-and-units entry (Story 45).
   2. `GET /api/v1/leadership-team/teams/<team_role>/?date=<>` — Team Dashboard (Story 46).
   3. `GET /api/v1/leadership-team/teams/<team_role>/members/<membership_id>/reflection/?period=<>` — individual reflection (Story 47).
   4. `GET /api/v1/leadership-team/teams/<team_role>/aggregate/?range=<>` — aggregate view (Story 48).
   5. `POST /api/v1/leadership-team/reflections/<id>/mark-attention/` — Story 46 criterion 5.
   6. `POST /api/v1/leadership-team/self-reflection/` — submit self-reflection.
   7. `PATCH /api/v1/leadership-team/self-reflection/<id>/` — edit within period.
2. Backend: template builder API under `/api/v1/leadership-team/templates/`:
   1. `GET /api/v1/leadership-team/templates/` — user's library + co-supervisor visible.
   2. `POST /api/v1/leadership-team/templates/` — create draft.
   3. `PATCH /api/v1/leadership-team/templates/<id>/` — update; creates new version per `parent_template`.
   4. `POST /api/v1/leadership-team/templates/<id>/publish/` — transition draft to published.
   5. `POST /api/v1/leadership-team/templates/<id>/clone/` — clone any visible template.
   6. `POST /api/v1/leadership-team/templates/<id>/archive/` — archive.
3. Backend: template assignment API:
   1. `POST /api/v1/leadership-team/assignments/` — assign template to target (role / individuals / tag group) with date range and cadence.
   2. `PATCH /api/v1/leadership-team/assignments/<id>/` — edit end date, extend.
   3. `GET /api/v1/leadership-team/templates/<id>/responses/?tab=<individual|aggregate>` — Story 53.
4. Backend: dynamic membership for role/tag assignments (Story 52 criterion 7). Static for individual assignments.
5. Backend: conflict resolution per Story 52 criterion 5.
6. Backend: implement attention conditions for dashboard cards: low completion (using configured expected-by time), concerning ratings (lowest scale value), sensitive content (per LT3 conditions).
7. Frontend: implement LT dashboard at `frontend/src/pages/leadership-team/Dashboard.jsx`. Per Story 45.
8. Frontend: implement Team Dashboard at `frontend/src/pages/leadership-team/TeamDashboard.jsx`. Per Story 46. Aggregate view tab per Story 48.
9. Frontend: implement individual reflection reader using existing component family per Story 47 criterion 6.
10. Frontend: implement template builder at `frontend/src/pages/leadership-team/TemplateBuilder/`. Per-language prompt editing with translation-gap indicators. Preview as respondent. Tier 1 scope only — no conditionals, branching, calculated fields, file upload, multi-page.
11. Frontend: implement template assignment dialog per Story 52.
12. Frontend: implement responses view at `frontend/src/pages/leadership-team/Responses.jsx`. Individual + Aggregate tabs per Story 53.
13. Backend: CSV export endpoints for aggregate (Story 48) and per-response (Story 53). Includes both languages where relevant per LT13.
14. Backend: system-provided base templates seeded per LT9. Initial set: counselor daily, kitchen_staff daily, specialist daily, leadership_team biweekly, unit_head daily, camper_care daily. Each in English with Spanish as second language placeholder. Loaded via seed command run on platform deployment.
15. Tests:
    1. Backend: template builder API tests for all CRUD + versioning + publishing.
    2. Backend: assignment API tests for dynamic vs. static membership, conflict resolution.
    3. Backend: responses view tests including aggregate computations across versions.
    4. Backend: CSV export tests with multilingual content.
    5. Frontend: template builder field-type rendering, save-as-draft, publish flow.
    6. Frontend: assignment dialog with conflict resolution.
    7. Frontend: responses view with individual filters + aggregate.
16. Documentation: `docs/role_flows/leadership_team.md` + `docs/template_builder.md`.

**Out of scope (Tier 2):**

- Conditional/branching logic, calculated fields, file upload, multi-page templates, skip logic, translation-request workflow, approval workflow, cross-org template library.

**Commit scope: `feat(7_12_leadership_team_flow): ...`. PR title prefix: `7_12`. This is the largest single step in Phase B; expect 2-3 sub-PRs if scope is too big to land in one.**

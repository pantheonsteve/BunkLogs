# Step 7_14: Madrich (TBE) Flow

**Goal:** Implement the Madrich flow per Stories 61-65.

**Canonical product spec:** `docs/user_stories/09_madrich/STORIES.md`

**Depends on:** 7_5, 7_11 (Kitchen Staff is the structural template), 7_12 (template builder).

**Scope of this step:**

1. Backend: most endpoints reuse Kitchen Staff patterns from Step 7_11 with `madrich` role template, `religious_school` program type, and weekly cadence. API surface under `/api/v1/madrich/` mirrors `/api/v1/kitchen-staff/`.
2. Backend: weekly period handling distinct from daily. `core.time_utils.get_current_period(template_cadence, org)` returns appropriate period bounds. Week boundary per MA1 (Monday-Sunday).
3. Backend: TBE 3-2-1 template seeded as system template (Step 7_12 ships the seed command). Template definition includes: 3 wins (text_list, min=3, max=3), 2 improvements (text_list, min=2, max=2), 1 question (text, required), 5 ratings (rating_group with 5 categories on 1-4 scale from Rachel's proposal).
4. Backend: Madrich-specific visibility per Story 64: Director + TBE Admin via Supervision relationship to `madrich` role in TBE program.
5. Backend: NO sensitive-note variants for Madrich. Standard visibility only.
6. Backend: Wednesday-evening reminder for unsubmitted weekly reflection per MA2. Scheduled via Celery Beat with day-of-week + time configuration.
7. Frontend: implement Madrich dashboard at `frontend/src/pages/madrich/Dashboard.jsx`. Mirrors Kitchen Staff dashboard with weekly cadence framing per Story 61 criterion 5.
8. Frontend: implement weekly reflection form at `frontend/src/pages/madrich/ReflectionForm.jsx`. TBE 3-2-1 template. AudienceDisclosure per Story 62 criterion 8.
9. Frontend: implement reflection history at `frontend/src/pages/madrich/History.jsx`. Weekly periods. No day-off submissions.
10. Frontend: no Hebrew/Spanish UI activated for TBE Tier 1 per scope statement. English only.
11. Tests:
    1. Backend: weekly period calculation tests (Monday-Sunday boundary).
    2. Backend: visibility tests confirming Director and TBE Admin see Madrich reflections; other roles do not.
    3. Backend: Wednesday-evening reminder dispatch test.
    4. Frontend: dashboard with weekly framing.
    5. Frontend: reflection form with 3-2-1 fields enforcing exact-count validation.
12. Documentation: `docs/role_flows/madrich.md`.

**Commit scope: `feat(7_14_madrich_flow): ...`. PR title prefix: `7_14`.**

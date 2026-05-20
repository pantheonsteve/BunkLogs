# Step 7_11: Kitchen Staff Flow

**Goal:** Implement the Kitchen Staff flow per Stories 37-44.

**Canonical product spec:** `docs/user_stories/06_kitchen_staff/STORIES.md`

**Depends on:** 7_1, 7_4, 7_5 (i18n foundation — heavy use here).

**Scope of this step:**

1. Backend: API endpoints under `/api/v1/kitchen-staff/`:
   1. `GET /api/v1/kitchen-staff/dashboard/` — minimal dashboard (Story 37).
   2. `POST /api/v1/kitchen-staff/reflection/` — submit reflection (Story 40). Translation pipeline kicks off via Step 7_5.
   3. `PATCH /api/v1/kitchen-staff/reflection/<id>/` — edit within rollover boundary (Story 41).
   4. `GET /api/v1/kitchen-staff/reflection/history/` — history view.
2. Backend: per Story 39 — template fetch returns localized prompts in user's preferred language with English fallback markers.
3. Backend: per Story 41 criterion 4 — edit handling when language preference changed since authorship. Reflection's `language` field unchanged unless user explicitly changes it.
4. Backend: integrate with translation pipeline (Step 7_5) for non-English submissions. Translation result viewable per Story 44 by leadership readers (Step 7_12).
5. Backend: leadership read view returns reflection with translation state per Step 7_5 criterion 13 and Story 44.
6. Frontend: implement Kitchen Staff dashboard at `frontend/src/pages/kitchen-staff/Dashboard.jsx`. Three sections per Story 37 criterion 3. NO operational signal.
7. Frontend: implement reflection form at `frontend/src/pages/kitchen-staff/ReflectionForm.jsx`. Renders in preferred language. AudienceDisclosure per Story 40 criterion 10.
8. Frontend: implement reflection history at `frontend/src/pages/kitchen-staff/History.jsx`. User's own content always in original language per Story 41 criterion 9.
9. Frontend: implement LanguagePicker integration in dashboard header (already exists from Step 7_5; wire up here).
10. Frontend: translation files for Kitchen Staff surfaces — English, Spanish. Hebrew content captured at data layer; UI in English per KS1.
11. Frontend: use TranslationDisplay component (Step 7_5) on leadership-readable views of Kitchen Staff reflections.
12. Tests:
    1. Backend: template fetch with language fallback per Story 39 criterion 4.
    2. Backend: edit handling with language preference change per Story 41 criterion 4-6.
    3. Backend: translation pipeline integration test (mock Anthropic; verify retry, timeout, GC).
    4. Backend: leadership read returns correct translation state per Story 44 criterion 3.
    5. Frontend: dashboard renders in Spanish for Spanish-preferring user.
    6. Frontend: ReflectionForm renders in Hebrew content (Story 38 criterion 3) with English UI.
    7. Frontend: TranslationDisplay state transitions.
13. Documentation: `docs/role_flows/kitchen_staff.md`.

**Commit scope: `feat(7_11_kitchen_staff_flow): ...`. PR title prefix: `7_11`.**

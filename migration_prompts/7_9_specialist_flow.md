# Step 7_9: Specialist Flow

**Goal:** Implement the Specialist flow per Stories 24-29.

**Canonical product spec:** `docs/user_stories/04_specialist/STORIES.md`

**Depends on:** 7_1, 7_4, 7_5, 7_8 (Flag model for the "flag for Camper Care" checkbox).

**Scope of this step:**

1. Backend: API endpoints under `/api/v1/specialist/`:
   1. `GET /api/v1/specialist/dashboard/` — minimal dashboard payload (recent notes top 10) per Story 24.
   2. `GET /api/v1/specialist/campers/?q=<>` — camper picker search (Story 25). Includes Recent group (last 7 days, max 8) and searchable All campers list.
   3. `POST /api/v1/specialist/notes/` — submit Specialist note (Story 26).
   4. `PATCH /api/v1/specialist/notes/<id>/` — edit within 24h window (Story 27).
   5. `GET /api/v1/specialist/campers/<camper_id>/` — Specialist-scoped Camper Dashboard variant (Story 28). Returns ONLY user's own notes + camper header; no other content.
   6. `POST /api/v1/specialist/self-reflection/` and `PATCH` for edits.
2. Backend: Specialist note submission with `flag_for_camper_care=True` creates Flag record (Step 7_8 model). Flag's `trigger_content_type='specialist_note'`, `trigger_content_id` = note ID. Flag's content shown in Camper Care workspace.
3. Backend: Specialist-scoped Camper Dashboard variant returns Specialist-only content. Visibility filtering at queryset level: query returns only notes authored by requesting Specialist for the specified camper.
4. Backend: enforce Specialist cannot retract a flag they raised per S5. Editing a note within the 24h window cannot un-flag.
5. Backend: cross-program camper picker (Story 25 criterion 7) — searches all programs the Specialist is a Member of.
6. Frontend: implement minimal Specialist dashboard at `frontend/src/pages/specialist/Dashboard.jsx`. Three top-level elements per Story 24 criterion 3.
7. Frontend: implement camper picker at `frontend/src/pages/specialist/CamperPicker.jsx`. Debounced, virtualized search. Performance target per Story 25 criterion 4.
8. Frontend: implement note form at `frontend/src/pages/specialist/NoteForm.jsx`. Includes Sensitive checkbox and Flag for Camper Care checkbox. AudienceDisclosure updates dynamically.
9. Frontend: implement Specialist-scoped Camper view at `frontend/src/pages/specialist/CamperView.jsx`. Renders only the user's own notes for the camper. Reuses the same data shape as Camper Dashboard but with the Specialist-only payload.
10. Frontend: implement Specialist self-reflection form, with optional Camper observation field linking to recent notes.
11. Tests:
    1. Backend: visibility tests confirming Specialist cannot see other Specialists' notes, Counselor reflections, etc.
    2. Backend: camper picker search performance test with 1,500 active campers.
    3. Backend: Flag creation on note submission with `flag_for_camper_care=True`.
    4. Frontend: Vitest tests for dashboard, picker, note form. Performance test on picker rendering.
12. Documentation: `docs/role_flows/specialist.md`.

**Commit scope: `feat(7_9_specialist_flow): ...`. PR title prefix: `7_9`.**

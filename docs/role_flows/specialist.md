# Specialist flow — developer reference

This document describes the **Specialist flow** introduced in migration
step `7_9` (Stories 24-29). It is the canonical developer-facing reference
for everything the Specialist role touches in the new multi-tenant stack.

If you are looking for the product spec (acceptance criteria, screens, copy),
see `docs/user_stories/04_specialist/STORIES.md`. The routing prompt lives
in `migration_prompts/7_9_specialist_flow.md`.

The Specialist role has **no legacy counterpart** — there is no Crane Lake
"specialist log" table to bridge. All data lives in the new multi-tenant
model from day one.

---

## 1. Surface area

### 1.1 Backend endpoints

All Specialist-scoped APIs live under `/api/v1/specialist/`:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/dashboard/` | Home: header, self-reflection state, and last 10 authored notes. Cached per-viewer for 30 s. |
| `GET` | `/campers/?q=` | Camper picker — returns `recent` (last 7 days, max 8) and `results` (all/search) sections. |
| `GET` | `/campers/<camper_id>/` | Specialist-scoped camper view: header + only notes authored by this specialist. |
| `POST` | `/notes/` | Create a specialist note (optionally flag for Camper Care). |
| `PATCH` | `/notes/<note_id>/` | Edit a specialist note within the 24-hour edit window. Cannot un-flag. |
| `GET` | `/notes/audience/` | Preview audience labels for a note given current field values. |
| `POST` | `/self-reflection/` | Submit today's specialist self-reflection (day-off support, optional translation). |
| `PATCH` | `/self-reflection/<reflection_id>/` | Edit within the edit window. |
| `GET` | `/self-reflection/history/` | Paginated history of own self-reflections. |

### 1.2 Backend file layout

```
backend/bunk_logs/api/specialist/
├── __init__.py
├── common.py           # ViewerContext, viewer_or_403, specialist_label, specialist_program_ids
├── dashboard.py        # GET /specialist/dashboard/
├── campers.py          # GET /specialist/campers/
├── camper_view.py      # GET /specialist/campers/<id>/
├── notes.py            # POST/PATCH /notes/ and GET /notes/audience/
└── self_reflection.py  # POST/PATCH/GET /self-reflection/
```

Tests live in `backend/bunk_logs/api/tests/test_specialist_endpoints.py`.

### 1.3 Frontend pages and components

```
frontend/src/pages/specialist/
├── Dashboard.jsx          # Story 24 — home screen
├── CamperPicker.jsx       # Story 25 — debounced search
├── NoteForm.jsx           # Stories 26-27 — create/edit
├── CamperView.jsx         # Story 28 — camper drill-down
└── SelfReflectionPage.jsx # Story 29 — daily self-reflection form

frontend/src/api/specialist.js  # all API calls for the above pages

frontend/src/pages/specialist/__tests__/
├── Dashboard.test.jsx
├── CamperPicker.test.jsx
└── NoteForm.test.jsx
```

Routes registered in `frontend/src/Router.jsx`:
- `/specialist` — Dashboard
- `/specialist/notes/new`
- `/specialist/notes/:noteId/edit`
- `/specialist/campers/:camperId`
- `/specialist/self-reflection/new`
- `/specialist/self-reflection/:reflectionId/edit`

---

## 2. Auth and tenancy

Access gate: `viewer_or_403` in `common.py` requires the request user to have
an **active** `Membership` with `role="specialist"` in the request
organization. Every response is scoped to the programs listed in that
membership's `program_ids` field.

Header tenant resolution uses the `X-Organization-Slug` request header
(standard across all new role flows).

---

## 3. Visibility model

Notes written by Specialists use `NoteType.SPECIALIST`. Audience resolution
follows `content_visibility.py`:

| Condition | Audience |
|---|---|
| `is_sensitive=False` | Counselor, Unit Head, Camper Care, Leadership Team, Admin |
| `is_sensitive=True` | Camper Care, Health Center, Special Diets, Admin |

The `GET /notes/audience/` endpoint lets the frontend preview this audience
before save (used in the `AudienceDisclosure` component).

---

## 4. Specialist note categories

Rather than extending the `Note.Category` enum (which would require a schema
migration), specialist notes use plain string values stored in the
`note.category` field (max 16 chars). The allowed values and their display
labels are:

| Value | Display label |
|---|---|
| `positive` | Positive observation |
| `concern` | Concern |
| `milestone` | Skill milestone |
| `behavioral` | Behavioral |
| `other` | Other |

Validation occurs in `SpecialistNoteCreateView` and `SpecialistNoteDetailView`.
The frontend uses `SPECIALIST_NOTE_CATEGORIES` from `src/api/specialist.js`.

---

## 5. Flag for Camper Care

When a note is created with `flag_for_camper_care: true`, the backend calls
`raise_flag_from_specialist_note` (defined in `core/flags.py`), which creates
a `Flag` record linked to the note's primary subject.

**Key invariant**: once a flag is raised it cannot be retracted via PATCH.
The backend rejects `PATCH` requests that attempt to set `flag_for_camper_care`
to `false` on a note whose flag is already `flag_raised=True`. The frontend
checkbox is disabled when `note.flag_raised=true`.

---

## 6. Edit window

Both notes and self-reflections enforce a 24-hour edit window enforced in
the PATCH views. Requests outside the window receive HTTP 403. The frontend
shows a banner ("Edit window closed") when the note's `created_at` is older
than 24 hours.

---

## 7. Dashboard caching

`GET /specialist/dashboard/` is cached per-viewer (cache key includes
`org.slug` and `person.id`) for 30 seconds using `django.core.cache`.
Any write that changes the dashboard data (note create/edit, self-reflection
submit/edit) calls `_bust_specialist_dashboard_cache` to invalidate the entry
immediately.

---

## 8. Specialist label derivation

The display label shown in the dashboard header (e.g. "Waterfront Specialist")
is derived from the `tags` field of the specialist's `Membership` record.
`specialist_label()` in `common.py` looks for a tag ending with `_specialist`
and formats it into title case. Falls back to "Specialist" if no matching
tag is found.

---

## 9. Camper picker — scoping

The picker (`GET /specialist/campers/`) returns only campers whose
`AssignmentGroupMembership.group.program_id` is in the specialist's program
list. The "Recent" section shows the up-to-8 campers this specialist wrote a
note about in the last 7 days; the "All campers" / "Results" section lists
(or filters) the full program-scoped roster.

---

## 10. Self-reflection template

`specialist_self_template()` in `common.py` queries `ReflectionTemplate` for
a record with `role="specialist"` that is active in one of the specialist's
programs. If no template is configured, the dashboard and self-reflection
endpoints return `state: "no_template"` and the frontend hides the
self-reflection card.

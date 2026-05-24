# Step 7_19: Notes Platform (Counselor + Unit Head v1)

**Goal:** Implement the Notes cross-role communication primitive per Stories 66-70, scoped to Counselor and Unit Head authors and audience members in v1 (per decision N4).

**Canonical product spec:** `docs/user_stories/10_notes_platform/*.md`

**Depends on:** 7_1 (visibility primitive), 7_3 (supervision relationship for UH audience resolution), 7_4 (audit trail), 7_5 (i18n foundation if Spanish content lands in notes), 7_6 (Counselor flow shipped), 7_7 (UH flow shipped).

**Estimated time:** 10–14 hours of agentic work.

**Scope of this step:**

1. Backend: new models in `core` app (or a new `notes` app — see Implementation note below):
   1. `Note` — fields: `id`, `organization` (FK, OrgScoped), `program` (FK), `author` (FK Person), `author_role_at_write` (CharField — captures the Membership role the author held at submission, for audit and display), `subject` (CharField max 200), `body` (TextField max 10000), `camper_reference` (FK Person nullable), `source_content_type` (CharField nullable — one of `'reflection_concern'`, `'specialist_note'`), `source_object_id` (UUID nullable), `created_at`, `archived_by` (M2M to Person through `NoteArchive`).
   2. `NoteAudienceCapture` — fields: `id`, `note` (FK Note), `person` (FK Person), `option_key` (CharField — captures which audience option resolved to this person, e.g. `'my_unit_head'`, `'specific_person'`, `'co_counselors_on_bunk'`), `bunk_id_at_capture` (FK nullable — for bunk-scoped audience options). One row per resolved-audience-Person. This is the captured audience per Story 66 criterion 9. Used for inbox visibility queries.
   3. `NoteReply` — fields: `id`, `note` (FK Note), `author` (FK Person), `author_role_at_write` (CharField), `body` (TextField max 10000), `created_at`. No edit; per decision N8.
   4. `NoteReadReceipt` — fields: `id`, `note` (FK Note), `person` (FK Person), `last_read_at` (DateTimeField), `last_read_entry_id` (UUID — id of the most recent Note or NoteReply the person had visibility to at last_read_at). Updated whenever a Person opens the thread.
   5. `NoteArchive` — through model for `Note.archived_by`. Fields: `note`, `person`, `archived_at`.

2. Backend: API endpoints under `/api/v1/notes/`:
   1. `GET /api/v1/notes/inbox/` — list notes where the requesting Person is in `NoteAudienceCapture` AND has not archived the note. Sorted by most-recent-activity (max of note `created_at` and any reply `created_at`) descending. Paginated, default 20.
   2. `GET /api/v1/notes/sent/` — list notes authored by the requesting Person and not archived by them. Same sort and pagination.
   3. `GET /api/v1/notes/archive/` — list notes archived by the requesting Person, whether sent or received.
   4. `GET /api/v1/notes/<id>/` — thread view: note + replies in chronological order, audience disclosure data, read receipts in `{read_count, audience_count}` form per Story 68 criterion 7 (no per-person identity reveal in v1).
   5. `POST /api/v1/notes/` — create a new note. Request body: `audience` (array of audience option objects, each with `option_key` and resolution context like `bunk_id` or `person_id`), `subject`, `body`, `camper_reference_id` (optional), `source_content_type` + `source_object_id` (optional, set automatically by cross-reference paths). Server resolves the audience options to a set of Person records per `audience_matrices.md`, captures the resolution in `NoteAudienceCapture`, and rejects with 400 if the resolved audience is empty after self-exclusion (per decision N1).
   6. `POST /api/v1/notes/<id>/replies/` — create a reply. Body: `body`. Audience is inherited; not specified by the client.
   7. `POST /api/v1/notes/<id>/archive/` — archive for the current user. Idempotent.
   8. `POST /api/v1/notes/<id>/unarchive/` — unarchive for the current user. Idempotent.
   9. `GET /api/v1/notes/unread-count/` — returns `{count: N}` of inbox notes with activity newer than the user's read receipt. Used by the sidebar badge per Story 67 criterion 10.

3. Backend: audience resolution module. New file `backend/bunk_logs/notes/audience.py` (or equivalent path). Implements the per-role audience matrices from `docs/user_stories/10_notes_platform/audience_matrices.md`. Each role's available options is a list of `(option_key, resolve_function)` pairs. Cross-cutting rules from the bottom of `audience_matrices.md` (self-exclusion, active Membership only, org-scoping, capture-don't-resolve, multi-program scoping) applied centrally. v1 supports only Counselor and UH author roles; other roles return a clear 403 with message "Notes not yet enabled for this role" if they POST to `/api/v1/notes/`.

4. Backend: composer audience options endpoint. `GET /api/v1/notes/audience-options/` — returns the list of audience option keys and human labels available to the requesting user based on their active Membership roles. The frontend composer renders the picker from this response. Resolution itself happens at POST time, not at picker render time — the picker only shows what's available; what the option resolves to is determined server-side.

5. Backend: visibility model integration. The Inbox query joins through `NoteAudienceCapture` and respects existing org-scoping. Cross-org isolation tests required. The audit trail (Step 7_4) records: note created, reply created, archived, unarchived. Edit events are NOT recorded for replies (replies cannot be edited per N8); the only "edit-like" operation is archive/unarchive.

6. Backend: cross-reference handlers.
   1. `POST /api/v1/notes/from-bunk-concern/` — Story 69 entry. Body: `concern_reflection_id`, `concern_field_key` (the field on the reflection that holds the concern text). Validates that the requester is authorized to view the concern (UH for the concerned bunk, LT, Admin). Returns a draft note payload pre-filled per Story 69 criterion 3, which the frontend uses to populate the composer. The actual note is created via the standard POST /api/v1/notes/ when the user submits.
   2. `POST /api/v1/notes/from-specialist-note/` — Story 70 entry. Body: `specialist_note_id`. Validates: requester is a Counselor with active Membership on the camper's bunk OR the Specialist who authored the note. Rejects if the specialist note is sensitive (per Story 70 criterion 9). Returns a draft note payload pre-filled per Story 70 criterion 4.
   3. Both endpoints return `{draft: {...prefilled fields...}}` not a created note. They are draft-prep endpoints, not submission endpoints.

7. Backend: source reference indicators on existing surfaces.
   1. When a Note's `source_content_type` is `reflection_concern`, the parent reflection's API serializer adds a `referencing_notes` field listing notes that reference this concern, filtered to those visible to the requester per visibility model (decision N7). Story 69 criterion 6.
   2. When a Note's `source_content_type` is `specialist_note`, the specialist note's API serializer adds the same `referencing_notes` field. Story 70 criterion 8.

8. Frontend: new components.
   1. `frontend/src/pages/notes/NotesPage.jsx` — the main Notes page with Inbox/Sent/Archive tabs. Per Story 67.
   2. `frontend/src/pages/notes/ThreadView.jsx` — single-thread view with reply composer. Per Story 68.
   3. `frontend/src/components/notes/NoteComposer.jsx` — the composer modal/page. Per Story 66. Used standalone (from NotesPage Compose button) and via cross-reference paths.
   4. `frontend/src/components/notes/AudiencePicker.jsx` — the audience selector inside the composer. Renders options from `GET /api/v1/notes/audience-options/`, supports multi-select, dedupes resolved recipients in the preview, integrates with the existing `AudienceDisclosure` component to render the resolved recipient list.
   5. `frontend/src/components/notes/NoteListItem.jsx` — shared row component for Inbox/Sent/Archive lists.
   6. `frontend/src/components/notes/SourceReferenceIndicator.jsx` — renders the source link with the no-transitive-access semantics from Story 68 criterion 11.
   7. `frontend/src/components/notes/ReferencingNotesIndicator.jsx` — renders the back-reference indicator on Bunk concerns and Specialist note views per Stories 69 criterion 6 and 70 criterion 8.

9. Frontend: routing. New routes `/notes`, `/notes/:noteId`. Both wrapped in the existing `AppLayout` (introduced in prompt 3.32) so the sidebar and header chrome render correctly.

10. Frontend: sidebar integration (amendment to `Sidebar.jsx` from prompt 3.32). Add a `Notes` link inside the MY WORK section, between `My reflections` and `File a reflection` (or as the last item in MY WORK if neither reflection link is rendered for this user). Gate: any authenticated user with at least one active Membership in a v1-enabled role (Counselor or Unit Head per decision N4). Show an unread count badge from `GET /api/v1/notes/unread-count/`. The badge polls on a 60-second interval while the user is active; no websocket in v1 per LT12.

11. Frontend: cross-reference affordances.
    1. On the existing Counselor self-reflection reader (which UH/LT/Admin see when reviewing a counselor's reflection), wrap the Bunk concerns field display with a `Start a Note from this concern` button visible to UH/LT/Admin (not the original author, per Story 69 criterion 2). Tapping calls `POST /api/v1/notes/from-bunk-concern/`, receives the draft payload, and opens the NoteComposer pre-filled.
    2. On the existing Specialist note viewer (on the camper profile), wrap the note with a `Reply with a Note` button visible to Counselors on the camper's bunk and to the Specialist who authored it (per Story 70 criteria 1-3). Tapping calls `POST /api/v1/notes/from-specialist-note/`, receives the draft, opens the composer.

12. Frontend: integration with the my-tasks queue. `TasksPage.jsx` (the queue page) already exists per prompt 3.19. Amend its data source to include a "Notes requiring response" section showing Inbox notes with unread replies. Each row in this section deep-links to `/notes/:noteId`. This is the Notes side of the unified queue concept.

13. Tests:
    1. Backend: model tests (creation, constraints, unique-together where applicable, FK cascade behavior on Person delete).
    2. Backend: API tests for every endpoint, covering: success path; permission failure (cross-org, non-v1-role POST); validation errors (empty audience, oversized body, missing required fields); pagination; archive idempotency.
    3. Backend: audience resolution unit tests covering Counselor and UH option matrices, with edge cases: cross-bunk counselor, end-dated Memberships, self-exclusion, multi-program Persons.
    4. Backend: visibility tests confirming a Person not in `NoteAudienceCapture` cannot read the note via any endpoint; cross-org isolation; sensitive Specialist note rejection for Story 70 cross-reference.
    5. Backend: audit trail tests for create, reply, archive, unarchive events.
    6. Backend: cross-reference draft endpoints — confirm pre-filled fields match the spec, confirm authorization checks.
    7. Backend: capture-don't-resolve semantics — a counselor added to a bunk after a note's submission does NOT see the note (per cross-cutting rule 4 in audience_matrices.md).
    8. Frontend: Vitest tests for NotesPage tabs, ThreadView, NoteComposer (including audience picker integration), SourceReferenceIndicator (including the disabled-link case for non-transitive access).
    9. Frontend: e2e test in Playwright covering the Story 69 happy path (UH reads a concern, starts a note, counselor receives it, counselor replies, UH sees reply on refresh).

14. Documentation: `docs/role_flows/notes.md` — developer-facing reference describing the models, audience resolution algorithm, capture semantics, and cross-reference flow. Link to `docs/user_stories/10_notes_platform/*.md` as the canonical product spec.

15. Migration: a single Django migration adding all five models. Includes indexes on:
    - `NoteAudienceCapture(person, note)` — inbox query
    - `Note(author, created_at)` — sent query
    - `NoteReply(note, created_at)` — thread render
    - `NoteReadReceipt(person, note)` — unread count derivation
    - `Note(source_content_type, source_object_id)` — referencing-notes lookup on reflections and specialist notes

**Implementation note on app placement:** The models are large enough and the visibility logic distinct enough that a new `notes` Django app is justified. Alternative: house in `core` if app proliferation is a concern. The migration prompt is agnostic; pick whichever fits the repo's existing convention better and document the choice in `docs/role_flows/notes.md`.

**Out of scope (deferred to v2 / later prompts):**

- Notes for any role other than Counselor and Unit Head (decision N4).
- Status field on notes (decision N5).
- Thread locking (decision N6).
- Reply editing (decision N8).
- Attachments on notes (out of scope per README).
- Push notifications outside the app (out of scope per README).
- Live thread updates / websocket (LT12 — manual refresh only in Tier 1).
- Per-person read receipts in the UI (Story 68 criterion 7 — Tier 1 shows count only).
- Cross-references from any source content type other than `reflection_concern` and `specialist_note`.

**Commit scope: `feat(7_19_notes_platform): ...`. PR title prefix: `7_19`.**

## Verification

- Backend: `pytest backend/bunk_logs/notes/` (or wherever the new app lives) must exit 0. Full `pytest` suite must also pass.
- Backend: `ruff check` clean on new code.
- Frontend: `cd frontend && npm test` must pass including the new Vitest suites.
- Frontend: `cd frontend && npm run build` must succeed.
- Frontend: `cd frontend && npm run lint` must pass.
- Manual smoke test on staging:
  1. Log in as a counselor. Verify Notes appears in the sidebar.
  2. Compose a note to "My Unit Head" with subject and body. Submit.
  3. Log in as the UH. Verify the note appears in Inbox with unread indicator.
  4. Open the thread. Reply.
  5. Log back in as the counselor. Verify the reply appears and the read indicator updates.
  6. Counselor submits a self-reflection with a Bunk concern.
  7. UH opens the reflection, taps "Start a Note from this concern", composes, submits.
  8. Counselor receives the cross-referenced note with the source indicator. Tapping the indicator opens the original concern.
- PR review: confirm decision-numbered references in the story files match what shipped (N1 through N9).

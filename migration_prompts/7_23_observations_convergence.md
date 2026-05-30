# Step 7_23: Observations — Converge the Note Systems

**Goal:** Collapse the platform's three overlapping note concepts into a single
**Observation** entity: subject-anchored (one or more subjects), peer-to-peer,
threaded, audience-tagged for alerting, and access-controlled by the supervisory
hierarchy layered with an org-configurable sensitivity gate. Retire the
no-subject peer-to-peer notes path entirely. Rename the per-subject dashboard
surface from "Subject" to **Profile**.

**Canonical product spec:** `docs/user_stories/10_notes_platform/*.md` (update in
this step) and the new `docs/role_flows/observations.md` written here.

**Depends on:** 7_1 (visibility primitive), 7_3 (Supervision), 7_4 (audit
trail), 7_5 (i18n — Observations carry a `language` and auto-translate like
notes/reflections), 7_8 (Camper Care notes), 7_9 (Specialist notes), 7_19
(Notes platform — this step supersedes it). 3.20/3.21 SubjectNote + subject
dashboard work is the other direct input.

**Estimated time:** 24–32 hours. **Split into the five PRs described under
"PR breakdown" — do not ship as one diff.**

---

## Strategic framing

Three models do overlapping work today:

1. `core.SubjectNote` — immutable observations about one subject, 4-level
   `visibility` enum, amendments, author/read permission modules, per-subject +
   global feeds, and a `NotesPanel` already on the subject dashboard.
2. `core.Note` — typed (`camper_care` / `specialist` / `maintenance`) notes
   about one subject, written via the `camper-care/notes/` and `specialist/notes/`
   endpoints (which already carry their own audience pickers).
3. `notes.Note` (Step 7_19) — threaded, audience-captured, read-receipted,
   archivable notes with an optional `camper_reference` subject.

Each has a piece of the target design but none has all of it. The convergence
takes SubjectNote's subject-anchoring + immutability + Profile placement, fuses
in the notes platform's threading + recipient capture + read-receipt badge, and
widens subject from one to many. The result is one model, one permission path,
one inbox.

**Absorb:** `core.SubjectNote` (all rows); `core.Note` rows with
`note_type in ('camper_care','specialist')`; `notes.Note` rows **with** a
non-null `camper_reference`.

**Leave alone:** `core.Note` rows with `note_type='maintenance'` (anchored to a
location/ticket, not a subject); Camper Care `Order`s; `MaintenanceTicket`s;
all `Reflection`s. These are NOT observations.

**Retire:** `notes.Note` rows with a null `camper_reference` (pure peer-to-peer).
Export to a one-time JSON archive for retention, then do not migrate them.

---

## The access model (implement exactly this)

An Observation has: one or more **subjects** (Persons it is about), an
**author**, zero or more explicitly tagged **recipients**, a **sensitivity
level**, an immutable **body** (corrections via amendment), threaded
**replies**, and per-person **read receipts**.

**Who can read an Observation** =

```
( viewer is the author )
OR ( viewer is an explicitly tagged recipient )
OR ( viewer holds a role whose supervisory hierarchy covers ANY tagged subject )
```

…**intersected with** the sensitivity gate:

```
AND ( viewer's role/capability clears the Observation's sensitivity level,
      per the org's sensitivity→role map )
```

Hierarchy floor (the "covers a subject" leg), reusing existing primitives:

- **Author** → always (even after role change).
- **Counselor / Junior Counselor** → subjects in bunks they author on
  (`AssignmentGroupMembership role_in_group='author'`).
- **Unit Head** → subjects in the bunks/groups under their `Supervision`
  (`Supervision.objects.bunks_for_uh` + descendant walk).
- **Camper Care** → subjects in the units/groups they are assigned to via
  `Supervision` (BUNK / ASSIGNMENT_GROUP targets, descendant-expanded).
- **Leadership Team / Admin** → every subject in the org.
- **Health Center / Special Diets** → only via the sensitivity map (they are the
  roles an org typically grants higher sensitivity tiers to); no blanket
  hierarchy floor unless org-configured.

This is the same shape as `subject_note_read.subject_note_read_q` and
`visibility._supervision_authored_q`; extend those rather than inventing a new
walk. The only structural change is **multi-subject**: "covers the subject"
becomes "covers ANY tagged subject," so the read `Q` ORs across the M2M.

**Sensitivity gate (the layer on top):**

- `Observation.sensitivity` is a small ordered enum. Reuse today's four levels
  renamed as sensitivity tiers: `normal` (was `team`), `sensitive` (was
  `supervisors_only`), `domain` (was `domain_only`), `confidential` (was
  `admin_only`).
- Org config: `Organization.settings["observations"]["view_by_capability"]`
  maps capability → set of tiers viewable. **Code default mirrors today's
  `NOTE_VIS_BY_CAP`** so behavior is unchanged until an org overrides it:
  `admin: all four`, `program_lead: normal+sensitive+domain`,
  `domain_specialist: normal+sensitive+domain`, `supervisor: normal+sensitive`,
  `participant: ∅`.
- **Authoring-time gate (Story: sensitivity can't outrun the recipient):** when
  composing, the recipient candidate list is filtered to people whose
  role/capability clears the selected sensitivity tier. The POST endpoint
  re-validates server-side and rejects (400) any recipient who does not clear
  the tier. Because of this gate, the "tagged recipient" read leg can never
  bypass sensitivity.

**Cross-unit:** allowed. A non-sensitive Observation tagging campers in two
units is visible to either unit's hierarchy. A sensitive one is gated to
sensitivity-cleared roles regardless of unit. No unit-boundary restriction on
authoring.

---

## PR breakdown

Ship as five reviewable PRs, each green before the next.

### PR1 — `Observation` model + data migration (no API/UI yet)

1. House the converged models in the `notes` app (it already owns threading /
   receipts / archive). Document the choice in `docs/role_flows/observations.md`.
   New models:
   - `Observation` — `organization` (OrgScoped), `program`, `author` (Person),
     `author_role_at_write` (CharField), `body` (TextField max 10000),
     `context` (CharField max 64, carried from SubjectNote), `sensitivity`
     (CharField enum above, default `normal`), `subject_visible` (bool, carried
     from SubjectNote), `language` (Person.LANGUAGE_CHOICES), `amendment_of`
     (self-FK, immutable-with-amendments per SubjectNote), `source_content_type`
     + `source_object_id` (carried from notes.Note for reflection_concern /
     specialist cross-refs), `created_at`, `updated_at`,
     `archived_by` (M2M through `ObservationArchive`).
   - `ObservationSubject` — through table: `observation`, `subject` (Person),
     unique together. (M2M `Observation.subjects`.)
   - `ObservationRecipient` — captured recipient list: `observation`, `person`,
     `option_key` (how they were tagged — keep the notes-platform field for
     audit). Drives the inbox + the read leg. Unique `(observation, person)`.
   - `ObservationReply` — `observation`, `author` (Person),
     `author_role_at_write`, `body` (max 10000), `created_at`. No edit.
   - `ObservationReadReceipt` — `observation`, `person`, `last_read_at`,
     `last_read_entry_id`. Unique `(observation, person)`.
   - `ObservationArchive` — through model: `observation`, `person`,
     `archived_at`. Per-user archive.

2. Indexes: `ObservationSubject(subject, observation)`,
   `ObservationRecipient(person, observation)`, `Observation(author, created_at)`,
   `ObservationReply(observation, created_at)`,
   `ObservationReadReceipt(person, observation)`,
   `Observation(source_content_type, source_object_id)`,
   `Observation(organization, sensitivity, created_at)`.

3. Data migration (idempotent, dry-run-first; gated behind `--apply`):
   - `core.SubjectNote` → `Observation` 1:1. `subject` → single
     `ObservationSubject`. `visibility` → `sensitivity` (team→normal,
     supervisors_only→sensitive, domain_only→domain, admin_only→confidential).
     `amendment_of` chains preserved. No recipients (none existed); read stays
     purely hierarchy+author. `is_sensitive=True` rows clamp to at least
     `sensitive`.
   - `core.Note` (`camper_care`, `specialist`) → `Observation`. `subject` →
     `ObservationSubject`. `note_type` → `context` (e.g. `camper_care`,
     `specialist`) so the origin is still legible. Map `is_sensitive`/category
     to a sensitivity tier (camper_care medical/family → `domain`;
     others → `sensitive` if `is_sensitive` else `normal` — document the table).
     Migrate any existing audience rows from those flows into
     `ObservationRecipient`.
   - `notes.Note` WITH `camper_reference` → `Observation`. `camper_reference` →
     `ObservationSubject`. `NoteAudienceCapture` → `ObservationRecipient`.
     `NoteReply`/`NoteReadReceipt`/`NoteArchive` → their Observation analogs.
     `subject`(title) text prepended to body or dropped — document choice.
     Default `sensitivity=normal` (these had no sensitivity concept).
   - `notes.Note` WITHOUT `camper_reference` → **export to
     `observations_retired_peer_notes.json`, do NOT migrate.**

4. Tests: model constraints, multi-subject M2M, amendment chains, the migration
   (counts in == counts out per source, sensitivity mapping table, dry-run
   writes nothing, idempotent re-run).

`feat(7_23_observations_convergence): add Observation model and migrate note sources`

### PR2 — Permission layer

1. New `core/permissions/observation_read.py` extending
   `subject_note_read_q` to: (a) OR across `subjects` (multi-subject);
   (b) add the tagged-recipient read leg; (c) apply the org sensitivity map as
   an intersecting filter. Author leg unchanged.
2. New `core/permissions/observation_authoring.py` — reuse
   `authorable_subject_queryset` / `max_author_scope` for *who can author about
   whom*; add `recipients_clearing_sensitivity(viewer, org, sensitivity)`
   returning the Person queryset eligible to be tagged at a given tier.
3. Sensitivity map helpers: `view_by_capability_for_org(org)` (defaults +
   settings overlay, mirrors `author_by_role_for_org`), and
   `capability_clears(capability, sensitivity, org)`.
4. Tests: each hierarchy leg; multi-subject OR; recipient-grant leg; sensitivity
   intersection (a supervisor who covers the subject still can't read a
   `confidential` note); author-always; cross-org isolation; the authoring gate
   rejecting an under-cleared recipient.

`feat(7_23_observations_convergence): layered observation read + sensitivity permissions`

### PR3 — API

Mount under `/api/v1/observations/`, modeled on `notes_platform/views.py`:

- `GET /observations/inbox/` — Observations where the viewer is a recipient,
  not archived, sorted by last activity. (This is the badge source.)
- `GET /observations/unread-count/` — `{count}` for the nav badge: recipient
  Observations with activity newer than the viewer's read receipt.
- `GET /observations/<id>/` — thread view (body, subjects, recipients summary,
  replies, read summary as `{read_count, audience_count}`); updates read receipt.
- `POST /observations/` — create. Body: `subject_ids[]` (≥1, validated against
  `authorable_subject_queryset`), `recipient_ids[]` (validated against
  `recipients_clearing_sensitivity`), `body`, `context`, `sensitivity`,
  `subject_visible`, optional source cross-ref. Captures `ObservationSubject` +
  `ObservationRecipient`. Reject 400 on: no subject, unauthorized subject,
  under-cleared recipient, oversized body.
- `POST /observations/<id>/replies/` — reply (visibility inherited; re-check
  read access).
- `POST /observations/<id>/amend/` — author/admin amendment (carry SubjectNote
  semantics).
- `POST /observations/<id>/archive/` + `/unarchive/` — per-user, idempotent.
- `GET /observations/recipient-candidates/?sensitivity=<tier>` — people the
  viewer may tag at that tier (powers the composer; re-filters on tier change).
- `GET /observations/subjects/?q=` — writeable-subject search (port
  `SearchableSubjectsView`).
- Profile feed: fold Observations into the subject dashboard payload
  (`dashboards/subject.py`) via `observation_read` so the Profile shows every
  Observation the viewer may read about that person — replacing the current
  `SubjectNote` notes block.
- Audit (7_4): created / reply / amend / archive / unarchive, `content_type='observation'`.

Deprecate the entire `/api/v1/notes/...` surface and the
`/subjects/<id>/notes/`, `/subject-notes/...`, `camper-care/notes/`,
`specialist/notes/` write paths: repoint them to the Observations API or return
410 with a pointer. Keep read-only shims only if a frontend caller still needs
them mid-migration; remove in PR5.

Tests: every endpoint — success, the three rejection paths, pagination, archive
idempotency, cross-org, recipient-grant visibility, sensitivity gate, the
capture-don't-resolve semantic (a counselor added to a bunk *after* an
Observation can still read it via hierarchy, but is NOT retroactively a
recipient).

`feat(7_23_observations_convergence): observations API + profile feed`

### PR4 — Frontend

- `ObservationComposer` (evolve `SubjectNoteComposer`): **multi-subject** picker
  (chips), **recipient** picker bound to `recipient-candidates/?sensitivity=`,
  **sensitivity** selector that re-filters recipients on change, context tag,
  `subject_visible` toggle. Reuse `AudiencePicker` patterns from the notes
  platform.
- `ObservationThread` (port `ThreadView`): body, subjects, replies, reply box.
- Profile (renamed `SubjectDetail`): the `NotesPanel` becomes the Observations
  panel — read any visible Observation inline, open the thread, reply.
- Nav badge: poll `observations/unread-count/` (60s, as 7_19), wire into the
  sidebar `MY WORK` section; clicking lands on the Observations inbox.
- Inbox page (port `NotesPage`) showing recipient-tagged Observations.
- Vitest: composer (multi-subject + sensitivity-filtered recipients),
  thread/reply, Profile panel, badge.

`feat(7_23_observations_convergence): observations composer, thread, profile, inbox badge`

### PR5 — Rename + retire + cleanup

- Rename the dashboard surface "Subject" → **Profile** everywhere user-facing:
  route `/dashboards/subject/<id>` → `/profile/<id>` (keep a redirect),
  page/title/nav copy, `SubjectDetail`→`ProfileDetail` (component rename only;
  keep test-ids stable or update tests). Backend route name may stay; update
  labels and docs.
- Remove the deprecated note endpoints and the `notes.Note` /
  `core.SubjectNote` / `core.Note`(cc+specialist) write paths and dead frontend.
  Leave `core.Note`(maintenance) intact.
- Mark `core.SubjectNote` and the converged `core.Note`/`notes.Note` paths
  read-only/deprecated (don't drop tables this step — drop in a later cleanup
  prompt after a stable window, per the 6_x pattern).
- Update `docs/user_stories/10_notes_platform/*` to the Observations model and
  write `docs/role_flows/observations.md` (models, the read formula, sensitivity
  map + authoring gate, migration provenance).

`feat(7_23_observations_convergence): rename Subject dashboard to Profile and retire legacy note paths`

---

## Out of scope (non-goals)

- Dropping legacy tables (separate cleanup prompt after a stable window).
- Converging Maintenance notes, Camper Care orders, Maintenance tickets, or
  Reflections.
- Migrating no-subject peer-to-peer notes (exported, then retired).
- New sensitivity tiers beyond the four mapped from the existing enum.
- Websocket/live thread updates (manual refresh, as 7_19).
- Per-person read-receipt identities in the UI (count only, as 7_19).
- Notifications outside the app (email/push).
- Changing Reflection visibility logic (only *reuse* its helpers).

## Sequencing

This touches the permission core, so keep it **off the June 5 Crane Lake
critical path**. Earliest safe start is after Wave 3 ships and Crane Lake summer
is stable. PR1 (model + migration, no behavior change) can land early behind the
existing surfaces; PR2–PR5 follow once summer load is off.

## Verification

- `pytest backend/bunk_logs/notes/` and `backend/bunk_logs/core/permissions/` exit 0; full `pytest` green.
- `ruff check` clean on new code.
- `cd frontend && npm test`, `npm run lint`, `npm run build` all pass.
- Migration dry-run report reviewed; `--apply` on a staging prod-dump; counts
  reconcile per the source→Observation table; spot-check 30 migrated rows across
  all four sources.
- Manual smoke on staging: counselor writes an Observation about their camper,
  tags the Unit Head as recipient → UH badge increments, UH opens + replies →
  counselor sees reply; counselor tries to tag a `confidential` Observation to a
  peer → recipient not offered / rejected; LT sees a cross-unit sensitive
  Observation a counselor cannot; every camper's Profile shows the Observations
  the viewer may read.
- PR titles prefixed `7_23`; commits scoped `feat(7_23_observations_convergence): …`.

## Implementation notes

- Reuse, don't reinvent: `subject_note_read.subject_note_read_q`,
  `visibility._supervision_authored_q`, `visibility.author_group_ids_with_descendants`,
  `subject_note_authoring.authorable_subject_queryset`, and the entire
  `notes_platform` view/serializer set are your templates.
- The recipient capture intentionally mirrors `NoteAudienceCapture` (keep
  `option_key`) so the audit story and any future role-matrix tagging carry over.
- Keep `Observation` org-scoped via `OrgScopedManager` + `all_objects`, exactly
  like the models it replaces.

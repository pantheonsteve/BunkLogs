# Specialist Flow — Stories 24-29

## Story 24: Sign in and land on minimal focused dashboard

### Acceptance criteria

1. Sign-in per Story 1.
2. Post-login is Specialist dashboard, scoped to active program(s) and role.
3. Exactly three top-level elements: **Write a camper note** entry (Story 25), **My reflection** card (per Story 16 pattern using `specialist` template), **My recent notes** (chronological, top 10 with Show older expansion).
4. Header: user name, role label (e.g., "Waterfront Specialist" from Membership tag), active program.
5. Role label reflects Membership: specialist with `specialist:waterfront` tag displays "Waterfront Specialist." No sub-type tag displays "Specialist."
6. NO operational signal: no bunk lists, completion counts, flag aggregates, order workspaces, caseload trees.
7. My recent notes: camper name, date, category if set, one-line preview, sensitivity indicator if applicable. Tap opens camper's Camper Dashboard filtered to user's contributions per Story 28.
8. Multiple Specialist sub-roles: primary sub-type label displayed; dashboard doesn't switch behavior. Notes attributed to user, not specific sub-role.

### Decisions

- S1: Cross-membership Specialist + Counselor (role switcher) deferred to Tier 2 unless common.

## Story 25: Search and select any camper

### Acceptance criteria

1. **Write a camper note** opens camper picker scoped to all campers with active Memberships in any Program(s) the user is also a Member of.
2. Picker layout: **Recent** section (last 7 days noted, max 8) + **All campers** section (alphabetical by last name).
3. Search matches first name, last name, preferred name, bunk name. Case-insensitive, partial token match.
4. Search debounced (250ms), virtualized; responsive at 1,500 active campers on mid-tier Android 4G.
5. Each result row: photo or initials, full name (preferred name in parens if different), bunk, age or grade.
6. Selecting camper opens note form (Story 26) pre-selected.
7. Picker excludes campers from programs user is not Member of (multi-tenant boundary enforced server-side).
8. Long-term withdrawn campers excluded. Off-camp-today campers remain selectable (legitimate recap case).
9. Zero results: *"No campers match [query]. Try searching by first name, last name, or bunk."*

### Decisions

- S2: Multi-select for batch noting out of Tier 1.
- S3: Group/session-level notes out of Tier 1.

## Story 26: Write a camper note

### Acceptance criteria

1. Form shows selected camper at top with "Change" affordance back to picker.
2. Fields: **Body** (required, plain text), **Category** (optional enum: Positive observation/Concern/Skill milestone/Behavioral/Other), **Sensitive** (boolean, default unchecked), **Flag for Camper Care** (boolean, default unchecked), timestamp/author auto-captured.
3. Target-length hint near body: *"A sentence or two is fine."* No character cap.
4. Submit button remains visible above mobile keyboard. No scroll past Submit to reach Body.
5. AudienceDisclosure component (see visibility model) at top of form:
   - Unchecked Sensitive: *"This note will be visible to: Counselor, Unit Head, Camper Care, Leadership Team, Admin."*
   - Sensitive checked: *"This note will be visible to: Camper Care, Health Center, Special Diets, Admin."*
6. Submission shows confirmation toast, returns to dashboard, prepends to My recent notes.
7. **Flag for Camper Care** raises flag in Camper Care flag workspace (Story 20) with user as source, note body as trigger context. Flag links to note; resolving flag doesn't affect note; note cannot be deleted.
8. Network-tolerant per Story 8 criterion 6. Pending state visible on queued notes.
9. Form follows user's preferred language per i18n layer.

### Decisions

- S4: No deletion; retraction via follow-up.
- S5: Specialist cannot retract a flag they raised; Camper Care resolves.

## Story 27: Update own notes within edit window

### Acceptance criteria

1. Note within 24 hours of authoring displays Edit affordance.
2. 24-hour window measured from original submission timestamp, not last edit.
3. Edit opens same form (Story 26) populated.
4. User can change Body, Category, Sensitive.
5. User cannot change: camper, author, original submission timestamp, Flag for Camper Care state once flag raised.
6. Edit preserves original submission timestamp; records last-edited-at separately. Both visible in detail: *"Submitted [time]. Edited [time]."*
7. After 24 hours, read-only to author. No Edit affordance.
8. Cannot edit other Specialists' notes.
9. Edit history visible only to Admin per audit trail spec.

## Story 28: See only own notes

### Acceptance criteria

1. My recent notes contains only notes authored by user.
2. Camper picker (Story 25) returns campers; no indication of other roles' note counts.
3. Opening camper via own note renders Specialist-scoped Camper Dashboard variant: **Header** (camper info), **My notes about this camper** (chronological, full body), and nothing else — no trend graph, no other roles' notes, no reflections, no flags.
4. Specialist-scoped Camper Dashboard does NOT render sections other roles see. Server-side filtering, not client-side hiding.
5. Direct URL to UH/LT camper view returns 403-equivalent: *"You don't have access to this view."*
6. Own notes from prior sessions/summers accessible. Date-range filter on "My notes about this camper."
7. My recent notes 10-entry cap expands via Show older for full historical authorship in active program.

### Decisions

- S6: Search across own historical notes out of Tier 1.

## Story 29: Submit and update Specialist self-reflection

### Acceptance criteria

1. **My reflection** card per Story 16 pattern using `specialist` template.
2. Cadence template-defined. Default Tier 1: daily. Configurable per program.
3. Drafts via local auto-save.
4. Form renders in preferred language per i18n.
5. Edit window: until rollover boundary; locked after.
6. History view reverse-chronological, read-only.
7. Visibility (per visibility model): user, Leadership Team, Admin. NOT visible to peers, NOT visible to UH (per S7).
8. Optional **Camper observation** field on template referencing campers user noted on today. When populated, references appear as links from reflection's history view back to camper notes. Pointer, not duplicate.

### Decisions

- S7: Specialist self-reflection NOT visible to UH.

# Camper Care (Wellness) Flow — Stories 18-23

## Story 18: Sign in and see my full caseload

**As a Camper Care staff member, I want to see every unit and bunk in my caseload.**

### Acceptance criteria

1. Sign-in per Story 1.
2. Post-login is the Camper Care dashboard, scoped to user's active program and caseload.
3. Primary section: caseload displayed hierarchically. Assigned Units expand to show Bunks on caseload.
4. Each Unit row: name, total bunks/campers on caseload, today's reflection completion ("[n] of [m]").
5. Each Bunk row: name, counselors, today's completion, Camper-Care attention badges.
6. Units default expanded; collapse persists per session, not across logins.
7. Attention badges: **Flagged for Camper Care** (unresolved), **Pending order** (open Camper-Care order), **Low completion**.
8. Bunks with any badge sort to top within Unit; others alphabetical.
9. Tapping Bunk opens Bunk Dashboard (Story 11, same component as UH).
10. **My reflection** section per Story 16's pattern using `camper_care` template.
11. Top-level **Flagged campers** entry above caseload tree, with unresolved count badge.
12. Top-level **Orders** entry alongside Flagged campers.

### Decisions

- CC1: Caseload modeled as Supervision records with `target_type=BUNK`.
- CC2: Overlapping caseloads permitted; bunk appears on multiple Camper Care members' dashboards.

## Story 19: Track reflection submissions across caseload

### Acceptance criteria

1. Dashboard header: caseload-wide summary "[n] of [m] reflections submitted across your caseload."
2. Summary breaks down by Unit (criterion 4 of Story 18) and Bunk (criterion 5).
3. Date selector switches entire dashboard to prior date. Today default. No future dates.
4. Date switch updates all counts, badges, flagged counts to that date's state.
5. Bunk with zero expected submissions (overnight trip, full absence) renders count as "—" with tooltip.
6. No action affordances on completion gaps. Camper Care reads, doesn't message counselors.

## Story 20: Triage campers flagged for Camper Care help

### Acceptance criteria

1. **Flagged campers** entry opens workspace listing all active unresolved flags for caseload campers.
2. Each entry: camper name, bunk/unit, flag source (Counselor/UH/Specialist), author name + timestamp, trigger context preview, status (Active/Followed Up/Resolved).
3. Today's flags in "Today" sub-section at top; older unresolved in "Carried over" sub-section, oldest first.
4. Tapping a flag opens camper's Camper Dashboard with flag context anchored at top.
5. Flag detail supports three transitions: **Mark Followed Up** (interim, optional note), **Mark Resolved** (terminal, required closing note), **Reopen** (from Resolved/Followed Up, required reason).
6. Resolved flags hidden by default; "Show resolved" toggle reveals last 30 days.
7. Full flag history (raised → followed up → resolved → reopened) visible on flag detail and on camper's Camper Dashboard timeline.
8. Zero active flags: explicit empty state, not empty container.

### Decisions

- CC3: Camper Care only can resolve. Original raiser can add follow-up but not close.
- CC4: No severity dimension on flags.

## Story 21: Add notes to a camper's profile

### Acceptance criteria

1. Camper Dashboard displays **Camper Care notes** section visible to: Camper Care, Health Center, Special Diets, Leadership Team, Admin. NOT visible to Counselors or Unit Heads (per CC5).
2. Authoring a note: **Body** (required), **Category** (required enum: Medical/Family/Social/Behavioral/Other), **Sensitive** (boolean, default unchecked), timestamp/author auto-captured.
3. Non-sensitive notes visible per criterion 1's audience list.
4. Sensitive notes visible only to: Camper Care, Health Center, Special Diets, Admin. Other audiences see placeholder per visibility model.
5. Notes in reverse-chronological order. Author and timestamp always visible.
6. User can edit own notes within 24 hours of authoring (window measured from original submission, not last edit). After 24 hours, read-only.
7. User cannot edit notes by other Camper Care members. Follow-up context via new note.
8. Notes cannot be deleted. Retraction via follow-up.
9. Notes persist across sessions and years. Date-range filter accessible.
10. AudienceDisclosure component (see `../00_cross_cutting/visibility_model.md`) displayed on form, updating dynamically when **Sensitive** is toggled.

### Decisions

- CC5: Non-sensitive Camper Care notes scoped to Camper Care + LT + Admin (more restrictive than loose version). Counselors and UH do not read.
- CC6: Note attachments out of Tier 1.

## Story 22: See incoming Camper Care orders

### Acceptance criteria

1. **Orders** entry opens Camper Care orders workspace.
2. Three sections in order: **New** (visually most prominent), **In Progress**, **Resolved** (collapsed by default with count).
3. Each row: camper name, bunk/unit, item, submitting counselor, submission time with age indicator past configured threshold, optional submitter note preview.
4. Tapping order opens detail view (Story 23).
5. Workspace scope: **all** Camper Care orders for program (not caseload-scoped per CC7).
6. Filter at workspace top: All / My caseload only / By bunk / By item.
7. Resolved section, when expanded, supports date range filter.

### Decisions

- CC7: Team-shared orders for Tier 1.
- CC8: No fulfilled-order auto-archive; date filter handles visibility.

## Story 23: Update order progress through lifecycle

### Acceptance criteria

1. Order detail view shows: order header, submitter note if present, **Activity** (chronological status changes + notes per the state machine — see `../00_cross_cutting/order_state_machine.md`), action affordances per current status.
2. Status transitions per the state machine.
3. User can add interim note to In Progress order without changing status. Interim notes in Activity.
4. 5-minute correction window for status changes per state machine.
5. Bulk fulfillment: select multiple In Progress orders, mark Fulfilled with shared closing note.
6. Submitting counselor sees updated status on next dashboard load. No notification.
7. Counselor view of same order shows status history but no action affordances.
8. **Unable to Fulfill** is terminal but reopenable per state machine.

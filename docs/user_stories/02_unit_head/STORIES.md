# Unit Head Stories — Consolidated

## Story 10: Sign in and see all bunks under my supervision

**As a Unit Head, when I log in I want to see every bunk that the counselors I supervise are assigned to, with completion and attention signals so I can prioritize.**

### Acceptance criteria

1. Sign-in follows Story 1's pattern.
2. The post-login screen is the Unit Head dashboard.
3. The dashboard's primary section lists every bunk where at least one Counselor under the user's supervision is currently assigned.
4. Each bunk row shows: bunk name, assigned counselor names, today's camper reflection completion ("[n] of [m] submitted"), and attention badges.
5. The supervision relationship resolves from the Supervision primitive (see `../00_cross_cutting/supervision_relationship.md`): a UH supervises Counselors directly; Bunks surface transitively via the Counselors assigned to them.
6. Attention badges (per UH1): **Help requested**, **Off-camp campers**, **Bunk concerns**, **Low completion** (under 50% of expected by org-configured "expected by" time).
7. Bunks with any attention badge sort to the top, in the order: Help requested → Bunk concerns → Off-camp → Low completion. Other bunks alphabetical.
8. Tapping a bunk opens that bunk's dashboard (Story 11).
9. If the user supervises bunks across multiple units, all qualifying bunks appear in the same list with unit name visible on each row.
10. A separate dashboard section, **My reflection**, displays today's self-reflection state per Story 16.

## Story 11: Open a bunk dashboard

**As a Unit Head, when I open a bunk I want to see flags, concerns, scores, orders, and specialist reports in a single scannable view.**

### Acceptance criteria

1. The Bunk Dashboard displays sections in this order: **Header** (bunk name, date, counselors, date selector), **Help requested**, **Off-camp today**, **Bunk concerns**, **Camper score grid** (Story 12), **Today's orders** (Story 14), **Specialist reports** (Story 15).
2. Each section is collapsible. An empty section collapses to a single-line summary: *"[Section name] — none today."*
3. The date selector defaults to today; can navigate to prior dates. Future dates not selectable.
4. The "Back" affordance returns to the UH home with bunk list scroll position preserved.
5. The Bunk Dashboard is read-only for UH at this level. Drill-in views (13, 14, 15) are also read-only.
6. Sections deriving from per-camper content reflect the bunk roster as of the selected date.

## Story 12: Read the daily score grid

**As a Unit Head, I want a color-coded table of every camper's scores so I can spot patterns and outliers quickly.**

### Acceptance criteria

1. The score grid renders one row per camper currently rostered in the bunk on the selected date.
2. The grid renders one column per scored dimension defined in the camper reflection template version active on the selected date.
3. Each cell shows the score value with a background color from a fixed scale that's consistent across all UH and supervisor views. Missing scores render visually distinct from low scores.
4. Camper names occupy the leftmost column and remain visible during horizontal scroll.
5. A color legend is visible on the screen.
6. Tapping a camper row opens the Camper Dashboard (Story 13).
7. Dimension columns appear in template-defined order; UH cannot reorder.

## Story 13: Open a camper's full daily reflection with trend

**As a Unit Head, I want to see today's full reflection for one camper alongside their score trend.**

### Acceptance criteria

1. The Camper Dashboard displays: **Header**, **Trend graph** (one line per scored dimension), **Today's reflection** (full text in template field order), **Today's scores**, **Today's flags**, **Specialist reports**, **Camper Care notes** (with sensitive notes per visibility model).
2. Trend graph defaults to current session date range; controls: This week / Last 4 weeks / Full session / Custom.
3. Trend graph supports toggling individual dimensions via legend; all visible by default.
4. Missing-data days appear as gaps, not zeros.
5. Tapping a prior date on the graph navigates the entire Camper Dashboard to that date.
6. Back affordance returns to Bunk Dashboard with score grid scroll position preserved.
7. The Camper Dashboard is a shared component reused across UH, LT, Admin, Camper Care. Visibility filtering happens server-side (see `../00_cross_cutting/visibility_model.md`).

## Story 14: See today's bunk orders

**As a Unit Head, I want to see camper-care and maintenance requests submitted from my bunks today.**

### Acceptance criteria

1. The Bunk Dashboard's Orders section lists all requests submitted for the bunk on the selected date.
2. Each row shows: type (Camper Care / Maintenance, visually distinguishable), submitter (counselor), subject, status, urgency (for Maintenance, when present), submission time, photo thumbnail (when attached).
3. Combined list sorted by submission time descending.
4. Section header summary: "[n] open • [m] in progress • [k] resolved."
5. Tapping an order opens its detail view read-only for UH.
6. Carried-over open orders from prior dates appear in a "Carried over from prior days" sub-section above today's new orders.

## Story 15: Read specialist reports about campers

**As a Unit Head, I want to see what specialists have logged about my campers.**

### Acceptance criteria

1. Specialist Reports section lists notes authored by Specialists about campers currently in this bunk.
2. Each entry: camper name, specialist name + role, date authored, full body (if short) or preview with "Read more" (if long).
3. Today's reports in a "Today" sub-section at top; prior dates in "Recent" sub-section, 14-day cap with "Show older" expansion.
4. Notes marked **sensitive** do not appear; UH sees placeholder per visibility model: *"1 sensitive note (Camper Care)"*. Placeholder count is per-camper.
5. Tapping a note opens full text without leaving Bunk Dashboard context.
6. Tapping camper name opens that camper's Camper Dashboard (Story 13).
7. Multiple notes about same camper appear as separate entries.

## Story 16: Submit my Unit Head self-reflection

**As a Unit Head, I want to submit my own daily reflection from my dashboard.**

### Acceptance criteria

1. UH dashboard's **My reflection** section shows today's state.
2. Uses the `unit_head` role template. Cadence and prompts are template-defined.
3. Section's "today" interpretation respects the org rollover boundary.
4. Tapping section opens the form, rendered in user's preferred language.
5. Form supports drafts via local auto-save.
6. Submission returns to dashboard with section in **submitted** state.
7. UH self-reflection may include optional **Bunk concerns** field referencing one or more bunks; when populated, concerns surface on relevant Bunk Dashboard's Bunk Concerns section (UH2).
8. If template defines non-daily cadence, section displays active reflection period (e.g., "Week of [dates]") and section's complete state covers the whole period.

## Story 17: Edit today's UH reflection; view history read-only

**As a Unit Head, I want to update today's reflection but have past reflections locked.**

### Acceptance criteria

1. Today's UH reflection displays "Edit" affordance in dashboard section and detail view.
2. Edit window: editable until rollover boundary; locked after.
3. History view lists prior submissions reverse-chronological, showing period covered, preview line.
4. Each prior submission opens read-only. No Edit affordance.
5. History shows gaps: days/periods with no submission appear with "no reflection submitted" indicator. Personal day-off submissions clearly indicated.
6. UH reflections from other UHs in the same org are NOT visible (UH6).
7. UH reflection contributing bunk concerns shows which bunks were referenced and links back to those Bunk Dashboards.

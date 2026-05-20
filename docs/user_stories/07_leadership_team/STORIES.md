# Leadership Team Flow — Stories 45-53

## Template builder Tier 1 / Tier 2 scope

**Tier 1:**
- Field types: text, textarea, text_list, rating_group, multiple_choice, single_choice
- Per-field localization (English required; Spanish, Hebrew optional with translation-gap indicators)
- Template-level settings: name, cadence, target role(s), target language(s)
- Versioning via `parent_template`
- Preview-as-respondent
- Save as draft / publish
- Clone from existing
- Archive (no delete) once responses exist

**Out of Tier 1:**
- Conditional/branching logic
- Calculated fields
- File upload fields
- Multi-page/wizard templates
- Skip logic / required-field dependencies
- Translation-request workflow (native-speaker review)
- Template approval workflow
- Cross-org template library

## Story 45: Sign in and see every team I supervise

### Acceptance criteria

1. Sign-in per Story 1.
2. Post-login is Leadership Team dashboard, scoped to active program.
3. Primary section **Teams I supervise**: one card per team via Supervision relationship.
4. Each team card: team name, member count, today's completion ("[n] of [m]"), co-supervisors when applicable (*"Also supervised by Alyson, Carl"*), attention badges.
5. Attention badges: **Low completion** (<50% by configured time), **Concerning ratings** (lowest scale value present in current period), **Sensitive content** (sensitive Specialist/Camper Care notes flagged for leadership attention in supervised scope).
6. Sort: attention badge first (low completion → concerning ratings → sensitive content), then alphabetical.
7. Tap card opens Team Dashboard (Story 46).
8. **My reflection** section per Story 16 using `leadership_team` template with template-defined cadence.
9. **Bunks and units** section (Story 49).
10. **Templates and assignments** section (Stories 51, 53).
11. Each team card fetched independently. Slow fetch doesn't block others. Inline retry on failure.

### Decisions

- LT2: Explicit-supervision-only visibility.
- LT3: Many-to-many co-supervisor model.

## Story 46: Open Team Dashboard

### Acceptance criteria

1. Team Dashboard sections: **Header** (team name, supervisors, member count, current reflection period, date selector), **Submission status** (grouped submitted/not submitted/day-off), **Flagged reflections** (current period low ratings + user-flagged + "needs attention" markers), **Member list** (row per active member with status, preview line in reader's preferred view per Story 44 criterion 6, entry to Story 47).
2. Date/period selector defaults to current. Navigate to prior. No future.
3. No-submission members visually distinct from submitted. Off-duty in "Day off / off-duty" sub-section, counted complete.
4. Tap member opens reflection in full per Story 47.
5. Mark specific reflection as "needs attention" from member list — UI annotation visible to user and other supervisors of same team. Does NOT change reflection or notify author.
6. Multilingual content: non-English shows English translation as preview line. Small language indicator per row ("ES", "HE"). Reader's preferred view setting applies.
7. Member list filters: by submission status, by language of authorship, by flag.
8. "Switch to Aggregate" toggle opens Story 48 view.

### Decisions

- LT4: Concerning ratings = lowest scale value triggers automatic flag.

## Story 47: Read individual staff member's reflection

### Acceptance criteria

1. Individual reflection view: **Header** (name, role, team membership, language preference indicator), **Trend graph** (line chart self-rating scores over time, one line per dimension; default 14 days for daily-cadence or 8 periods for non-daily), **Submission metadata** (period, submission timestamp, last-edited if edited, language of authorship), **Reflection content** (template field order), **Translation panel** (for non-English per Story 44).
2. Trend graph: toggle individual dimensions via legend; all visible by default.
3. Read-only for LT. No edit affordances. No comment/note against reflection itself.
4. Back returns to Team Dashboard with filter/scroll state preserved.
5. Edit history not visible to LT. "Edited [time]" indicator surfaces edits; prior content does not. Admin has full edit history (Story 59).
6. Uses Camper Dashboard component family for structural consistency.

### Decisions

- LT5: LT private note on reflection not in Tier 1.

## Story 48: See aggregate views and trends

### Acceptance criteria

1. Aggregate view via Story 46 criterion 8: **Completion rate over time** (line chart percentage submissions per period), **Average rating over time** (line per dimension defined by team's active template version; version boundaries shown with visual marker; dimensions only in some versions plot only over their valid range), **Submission language breakdown** (donut/stacked bar of language distribution for multilingual teams).
2. Date range: This week / Last 4 weeks / Full session / Custom. Default Last 4 weeks.
3. Language honored: averages computed against original-language ratings (language-agnostic). Free-text-driven aggregates (Tier 2) against English translations with "translated content included" indicator.
4. Read-only.
5. CSV export: one row per submission in range, all template fields + metadata (timestamp, author, authorship language, translated content alongside original where applicable).
6. CSV respects LT user's visibility — only supervised teams.
7. Reuses trend graph component family from Story 13/47 with team-scoped data.

### Decisions

- LT6: Free-text theme aggregation out of Tier 1.

## Story 49: Cross over to camper-facing side with full visibility

### Acceptance criteria

1. **Bunks and units** section: hierarchical Unit/Bunk view, org-wide (not filtered by supervisor assignment).
2. Each Unit row: name, bunk count, today's completion across unit, attention indicators.
3. Each Bunk row: name, counselors + UH, today's completion, attention indicators (Story 10 model).
4. Tap Bunk opens Bunk Dashboard (Story 11, same component as UH).
5. Tap Camper opens Camper Dashboard (Story 13).
6. LT has UH-equivalent visibility PLUS: sensitive Camper Care notes, sensitive Specialist notes (per consolidated visibility model).
7. Dashboard header on bunk/camper screens: *"Viewing as Leadership Team"*.
8. Strictly read-only on camper-facing side: no editing reflections, no transitioning orders, no resolving flags, no authoring Camper Care/Specialist notes.
9. Direct URL edit attempts return same "you don't have access" state as Story 28 criterion 5.

## Story 50: Submit and edit LT reflection

### Acceptance criteria

1. **My reflection** card per Story 16 using `leadership_team` template.
2. Cadence template-defined. Default biweekly. Configurable per program.
3. Card displays current reflection period (e.g., "Week of May 13-26") and submission status for period.
4. Card does NOT show daily incompleteness states for non-daily cadence. Framing "current period: not yet submitted."
5. Tap opens form, renders in preferred language.
6. Drafts via local auto-save.
7. Edit window: current period; locked after.
8. History view reverse-chronological, period covered, submission timestamp, preview line.
9. Prior submissions read-only.
10. Visibility per consolidated model: user, other LT members in same org, Admin. NOT visible to UH, Counselors, operational roles.
11. **Private** toggle on form: when checked, restricts to author + Admin only. Other LT members do not see private.

## Story 51: Create new reflection template

### Acceptance criteria

1. **Templates and assignments** entry opens user's template library: own (Draft/Published/Archived), co-supervisors' templates (visible, cloneable, not editable).
2. **Create new template** action opens template builder.
3. Builder displays: **Template settings panel** (name, slug auto-generated/editable, description, cadence enum, target role(s), supported languages), **Field list** (drag-orderable with add/edit/delete), **Field editor** (per field: type, key, prompts per language, validation), **Preview pane** (renders as respondent, language selector switches preview).
4. Field types per Tier 1 scope.
5. Per-field config: **Key** (required, unique within template, machine-readable), **Prompts per language** (English required; Spanish, Hebrew optional with translation-gap indicators), **Required** (boolean), **Validation** (field-type-specific), **Help text per language** (optional).
6. Template-level: cadence determines period boundaries, target role(s) from existing taxonomy, supported languages subset of {English, Spanish, Hebrew} Tier 1. Templates not visible to users with preferences outside set (fallback to most-preferred available).
7. Lifecycle: **Save as draft** (private to author + co-supervisors), **Publish** (assignable; edits create new version via `parent_template`; prior versions retain existing reflections), **Archive** (removes from new assignment, preserves reflections, cannot reactivate), no delete with responses.
8. **Clone from existing** any visible template as starting point. Clone is fresh draft, no version relationship.
9. Builder warns on common mistakes: publishing without translations for declared languages, required fields with no prompts in supported language, renaming field key on published template (breaking change).

### Decisions

- LT7: Co-supervisors see and clone, not edit.
- LT8: No approval workflow Tier 1.
- LT9: System-provided base templates shipped with platform.

## Story 52: Assign template to team and schedule rollout

### Acceptance criteria

1. Published template's detail view: **Assign** action opens dialog.
2. Dialog captures: **Target** (by role / individual members / tag group), **Date range** (required start, optional end), **Cadence** (defaults to template's, overridable), **Replaces existing** (checkbox when overlap with active same-role template).
3. Preview: *"This will be assigned to [n] members starting [date]"*, names visible on hover/expansion.
4. Reversible: before responses, full unassign/delete. After responses, end (set past end_date) but not delete.
5. Conflict resolution: overlap with existing same-role-and-date scope, dialog requires choice: Replace existing (existing ends day before new) / Run both / Cancel new.
6. Assigned template visible in member's reflection dashboard from start date forward at configured cadence.
7. Dynamic membership: role/tag assignment includes Memberships added after start date if matching.
8. Static membership: individual assignment does NOT auto-expand. New Memberships not added retroactively.
9. Edit end date or extend; other fields immutable once responses exist.
10. View response data (Story 53) from assignment's detail view.

### Decisions

- LT10: Multi-team assignment of single template supported.
- LT11: Cross-program assignment out of Tier 1.

## Story 53: View responses to assigned template

### Acceptance criteria

1. Template's **Responses** view from template detail or assignment. Two tabs: **Individual**, **Aggregate**.
2. Individual tab: one row per response. Each: respondent name, role, submission date, language of authorship, one-line preview (English translated where applicable).
3. Individual filters: date range, respondent (multi-select), language of authorship, rating threshold ("show only responses with any rating ≤ 2"), has free-text content (vs. ratings-only).
4. Tap response opens full per Story 47.
5. Aggregate tab uses same component family as Story 48: completion rate over time, average rating per dimension, language distribution, response volume per period.
6. Aggregate supports same date-range controls as Story 48.
7. CSV export both tabs: Individual (flat row-per-response), Aggregate (time-series with period boundaries).
8. Scope per-assignment by default. "Combine assignments of this template" toggle aggregates across multiple assignments of same template.
9. Read-only.
10. Empty state for no-responses: *"No responses yet. First response due [date]."*

### Decisions

- LT12: Manual refresh for Tier 1.
- LT13: CSV export includes free-text both languages when relevant.

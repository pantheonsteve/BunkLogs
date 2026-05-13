# Prompt 3.20 — Coverage and color-pattern dashboards

**Wave:** 3 (Crane Lake Summer 2026 Build) — Shared-roster observation pattern
**Estimated time:** 10-12 hours
**Prerequisite:** Prompts 3.17, 3.18, 3.19 complete.

**Use the context prompt at the top of `bunklogs-migration-prompts.md` before this session.**

---

```
Build the dashboards that visualize trends and coverage across rosters. The signature view is a per-subject-per-day grid with cells colored by rating value — the "color patterns" pattern recognition supervisors use to spot a camper trending downward or a bunk where ratings are slipping. Plus completion heatmaps, author attribution rollups, and a refined permission model.

CONTEXT:
The dashboards from 3.16 work for self-reflection templates. They don't have the right shape for shared-roster observation. This prompt extends 3.16's TemplateDashboard infrastructure with three new visualizations and a permission rework that respects the author/subject/supervisor relationships introduced in 3.17.

Tasks:

1. Refine the permission model for dashboard visibility, replacing or extending the simple role-based scoping from 3.16. Add a helper `core/permissions/visibility.py::reflections_visible_to(user, queryset=None)`:

   For a user, return a queryset of Reflections they can see:
   - Reflections they authored (always)
   - Reflections about themselves IF the template's subject_visible=True
   - Reflections about subjects in any AssignmentGroup where the user is an author
   - Reflections in any AssignmentGroup that is a descendant of an AssignmentGroup where the user is an author (parent groups see children — unit head sees bunks, division head sees units)
   - All reflections in their org if user has Membership.role='admin' or User.is_superuser
   
   Implement as a single queryset filter using Q objects. Avoid N+1 lookups; bulk-resolve assignment-group membership at the start of the query.
   
   Add tests for each visibility path. Test the descendant case explicitly (unit head sees Bunk Maple's logs even though they're not directly an author of Bunk Maple).

2. Build a Coverage Dashboard at /dashboards/coverage:
   - Audience: org admins, supervisors (anyone author of a group with children), unit heads, leadership team
   - Top-level: organization-wide completion rate for all active shared-roster templates today/this-period
   - Group breakdown: heatmap-style table where rows are AssignmentGroups, columns are days (last 14 days), cells are colored by completion percentage:
     * Dark green (100%)
     * Light green (90-99%)
     * Yellow (70-89%)
     * Orange (40-69%)
     * Red (1-39%)
     * Gray (0%)
     * Dim gray with diagonal lines (no roster data — group inactive on that day)
   - Click a row to see per-subject coverage detail for that group
   - Filter: by group_type, by template, by date range
   
   API: GET /api/v1/dashboards/coverage/?group_type=&template=&date_start=&date_end=
   Returns: per-group, per-day completion data scoped by reflections_visible_to
   
   Performance target: <800ms for a full camp's data over 14 days. Pre-aggregate completion if needed using a daily Celery task that writes to a `CoverageSnapshot` cache table — but only build that cache if the live query is too slow. Try the live query first.

3. Build a Subject Trend Grid at /dashboards/subject-trends/{group_id}:
   - Audience: supervisors of that group (per visibility rules)
   - Layout: rows are subjects (campers in the bunk), columns are days, cells are colored by primary_rating or category_ratings average for that day
   - Color scale uses a 1-N rating scale matched to the template's scale (so 1-4 rating gets 4 colors, 1-5 rating gets 5 colors)
     * Rating 1 = red
     * Rating 2 = orange
     * Rating 3 = yellow
     * Rating 4 = green
     * Rating 5 = dark green (if 5-point scale)
     * No reflection that day = gray
   - When the template uses category_ratings: cells use the average across categories OR the user can pick which category to view via a dropdown above the grid
   - Hover/tap a cell: tooltip shows the rating, who authored, link to the full reflection
   - Click a subject row label: drill into per-subject view (next item)
   
   This is the signature "color patterns" view. Get the visual right; reference established heatmap conventions (think: github contribution graph but with diverging color scale instead of sequential).
   
   API: GET /api/v1/dashboards/subject-trends/?assignment_group={id}&template={id}&date_start=&date_end=&category={key|null}
   Returns: per-subject, per-day rating values plus reflection IDs for tooltip linkage

4. Build a Per-Subject Detail view at /dashboards/subject/{person_id}:
   - Shows all reflections about a single subject across all templates (within visibility scope)
   - Time-series chart for each rating field (primary_rating or per-category)
   - List of recent text responses (wins, concerns, narrative entries) with author attribution
   - "Concerning patterns" section: surfaces any reflection with a rating of 1 in the last 14 days, or a downward trend (statistical: linear regression slope < threshold over a 7-day window — use scipy if not already in deps; otherwise simple "is most recent week lower than prior week" comparison)
   - Cross-template view: a camper's logs from counselors, wellness team, and special diets all visible together
   
   API: GET /api/v1/dashboards/subject/{person_id}/?date_start=&date_end=
   Includes all visible reflections about this subject, grouped by template

5. Build an Author Attribution view at /dashboards/authors/{group_id}:
   - For supervisors: shows which authors are pulling weight in a shared-roster context
   - Layout: rows are authors, columns are days, cells show count of reflections submitted that day
   - Color cells by relative contribution within the group (no contribution from a counselor on a day they were on duty might warrant a check-in)
   - Summary stats: most active author, lowest contribution, average per author
   
   This is a sensitive view — surface it only to org admins and direct supervisors, not to peer authors. Don't let counselors see each other's contribution counts as a routine view; that's a supervisor's tool.

6. Refactor 3.16's TemplateDashboard to use the new visibility helper. Replace existing role-based scoping (which assumed self-reflection only) with reflections_visible_to. The dashboard should now correctly handle shared-roster templates without code changes specific to that pattern.

7. Update the CSV export from 3.16 to include the new fields:
   - subject_name, subject_id, author_name, author_id, assignment_group_name, assignment_group_type
   - For each reflection row, add these alongside the existing field-level columns
   - Respect reflections_visible_to scoping

8. Add a "Concerns inbox" at /dashboards/concerns:
   - Aggregates reflections containing dashboard_role='open_concern' fields with non-empty values
   - Filtered to subjects/groups the viewer can see
   - Mark-as-read state per user (new model `ConcernReadState` with user, reflection, read_at)
   - Filters: unread, all, by template, by subject, by date
   - This generalizes the LT dashboard's "open questions" widget from 3.6 into a full inbox

9. Performance considerations:
   - The subject trend grid for a 14-day window of a 12-camper bunk is 168 cells — trivial
   - Camp-wide coverage heatmap for 30 bunks over 14 days is 420 cells — still fine
   - Where it gets heavy: the "all subjects across all groups across all templates" view. Don't build that as a single render; force selection of a group or template.
   - Use database aggregation (annotate, GROUP BY) rather than loading reflections into Python; the queries should return pre-aggregated structures

10. React component organization:
    - frontend/src/dashboards/coverage/CoverageDashboard.tsx
    - frontend/src/dashboards/coverage/GroupCoverageHeatmap.tsx
    - frontend/src/dashboards/trends/SubjectTrendGrid.tsx (the signature color-pattern view)
    - frontend/src/dashboards/trends/TrendCell.tsx (single colored cell with tooltip)
    - frontend/src/dashboards/subject/SubjectDetail.tsx
    - frontend/src/dashboards/authors/AuthorAttribution.tsx
    - frontend/src/dashboards/concerns/ConcernsInbox.tsx
    - Reuse existing widget components from 3.16 where possible
    
    Color scales should be defined once in frontend/src/dashboards/colors.ts and imported, so both heatmap and trend grid use consistent palettes. Make the palette colorblind-aware: use a viridis-adjacent or red-yellow-green palette that's distinguishable for deuteranopia (the most common form of color blindness). Test in a colorblind simulator.

11. Tests:
    - reflections_visible_to returns correct sets for each user role
    - Descendant visibility works (unit head sees bunks)
    - subject_visible flag honored correctly
    - Coverage heatmap returns correct percentages
    - Subject trend grid shows correct rating colors per cell
    - Per-subject detail aggregates across templates correctly
    - Trend detection (downward pattern) flags expected cases and doesn't false-positive on normal variance
    - Author attribution view scoped to supervisors only
    - Concerns inbox filters correctly, mark-as-read persists
    - CSV export includes new fields and respects visibility
    - All charts render with realistic seeded data
    - Dashboard refactor doesn't break existing 3.16 tests

12. Accessibility:
    - Color-only encoding is not allowed — every cell has a tooltip with the numeric value
    - Heatmaps include a legend explaining the color scale
    - Tab order and keyboard navigation work for all grids
    - aria-label on cells: "Sarah Levin, June 14, rating 3 of 4, logged by Counselor Mike"

13. Update docs/dashboards.md (from 3.16) with:
    - The full set of dashboards now available
    - When to use coverage vs subject trends vs subject detail
    - The visibility model and how to extend it
    - The color scale conventions
    - Performance notes and when to consider pre-aggregation

Acceptance criteria:
- Coverage Dashboard renders correctly for org admins
- Subject Trend Grid shows the color patterns supervisors will use to spot trends
- Per-Subject Detail aggregates cross-template reflections about a single camper
- Author Attribution scoped to supervisors only
- Concerns Inbox surfaces flagged items with mark-as-read state
- reflections_visible_to correctly enforces author/subject/supervisor model
- 3.16's existing dashboards continue to work after refactor
- All views perform under target latency with realistic data
- Tests pass, linter passes, build succeeds
- Documentation updated
- Manual smoke test on staging with seeded Crane Lake-shaped data: a unit head sees their bunks, a counselor sees their bunk only, an org admin sees everything
- Commit structure: 1) reflections_visible_to + tests, 2) refactor 3.16 to use it, 3) Coverage Dashboard, 4) Subject Trend Grid (the big one), 5) Per-Subject Detail, 6) Author Attribution, 7) Concerns Inbox, 8) CSV export update, 9) docs

Out of scope:
- Predictive trend analytics ("this camper is likely to disengage based on rating trajectory") — that's a research project, not a v1 dashboard
- Cross-program longitudinal views (Tier 3 territory)
- Customizable dashboard layouts per user
- Real-time updates (page-load-fetch is fine; supervisors aren't sitting on dashboards waiting for live updates)
- Mobile-optimized supervisor views (these are desktop-first; supervisors typically review at a computer)
- Notifications when concerns are filed (a candidate for Wave 4 once we observe how supervisors actually use the inbox)
```

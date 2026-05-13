# Prompt 3.16 — Dashboard role rendering and template-aware widgets

**Wave:** 3 (Crane Lake Summer 2026 Build) — Form Builder addition
**Estimated time:** 8-10 hours
**Prerequisite:** Prompts 3.13, 3.14, 3.15 complete. Best run after at least one real template (with role-tagged fields) has been seeded with real content from Brent.

**Use the context prompt at the top of `bunklogs-migration-prompts.md` before this session.**

---

```
Refactor the existing dashboards (Leadership Team from 3.6, Wellness from 3.7) to read dashboard_role tags from the active template's schema and render appropriate widgets. Build generic widgets for fields without role tags.

CONTEXT:
The form builder lets admins create arbitrary templates. The dashboards must adapt automatically. Role-tagged fields get the polished widgets we already use for Crane Lake's daily logs. Untagged fields get generic widgets so every template gets *some* useful dashboard out of the box.

Tasks:

1. Define the role-to-widget mapping in `frontend/src/dashboards/widgetMap.ts`:
   - primary_rating -> RatingHeadlineWidget (large number with trend arrow vs prior period)
   - category_ratings -> CategoryRadarWidget (radar chart, one axis per category, average rating)
   - wins -> HighlightFeedWidget (recent wins items, paginated)
   - improvements -> ImprovementFeedWidget (similar but framed as growth)
   - open_concern -> ConcernQueueWidget (unread queue with mark-as-read; supervisor can drill into Person)

2. Define generic widgets keyed by field type for untagged fields:
   - text/textarea -> TextResponseListWidget (recent responses, truncated, click to expand)
   - text_list -> ItemCloudWidget (frequency-weighted item list)
   - single_rating -> RatingDistributionWidget (small bar chart of rating distribution)
   - rating_group (untagged) -> RatingTableWidget (rows = categories, columns = rating values, cells = counts)
   - single_choice/multiple_choice -> ChoiceBarChartWidget
   - yes_no -> YesNoBreakdownWidget (donut + count)
   - date/number -> small histogram or sparkline as appropriate
   - section_header/instructions -> not rendered (meta fields)

3. Build a `TemplateDashboard` component that:
   - Takes a template ID and a date range
   - Fetches template schema and aggregated reflection data for the range (single endpoint: GET /api/v1/dashboards/template/{id}/?period_start=&period_end=)
   - Renders role-tagged widgets first (in template field order)
   - Renders generic widgets second, in a "More fields" disclosure
   - Header summary always shown: completion rate, response count, person count

4. Build the aggregation endpoint /api/v1/dashboards/template/{id}/:
   - Aggregates data per-field, returning a structure matched to the widget contract
   - For rating_group: per-category mean, distribution, and trend vs prior period of same length
   - For text/textarea: recent items (paginated), with submitted_by filtered by current user's permissions
   - For text_list: frequency-counted items
   - For yes_no: counts and percentages
   - Permissions: scoped by role (LT users see their unit, wellness sees wellness reflections, admins see all)

5. Refactor existing dashboards to use TemplateDashboard:
   - LT dashboard becomes a TemplateDashboard view filtered to leadership_team-role templates
   - Wellness dashboard becomes a TemplateDashboard view filtered to wellness-role templates
   - Counselor self-tracking from prompt 3.11 stays as-is (it's a different shape — personal completion tracking, not aggregation)

6. Add a "Dashboard preview" mode in the template editor (prompt 3.15) — a button in the editor header that opens a modal showing what the dashboard would look like with the current schema and synthetic sample data. Helps admins see the consequence of dashboard_role tagging choices.

7. CSV export endpoint at GET /api/v1/dashboards/template/{id}/export/?period_start=&period_end=&format=csv:
   - One row per Reflection
   - Columns: person name, period_end, language, then one column per field (using field key)
   - text_list fields exported as semicolon-joined string
   - rating_group exported as one column per category (suffixed with category key)
   - Respects permission scoping
   - File download with sensible filename

8. Tests:
   - widgetMap returns correct widget for each role and type
   - Aggregation endpoint produces correct counts/means with seeded test data
   - Aggregation respects permissions (wellness user can't see counselor reflections from other unit)
   - Generic widgets render for untagged fields
   - Role-tagged widgets render when tags present
   - Dashboard preview modal in editor shows synthetic data correctly
   - CSV export produces parseable output with correct columns
   - Existing LT and Wellness dashboard tests still pass after refactor

9. Update docs/dashboards.md describing the role-to-widget contract and how to extend it (add a new dashboard_role + widget pair).

Acceptance criteria:
- All five dashboard_role values render their widgets correctly
- Generic widgets render for untagged fields
- Refactored LT/Wellness dashboards work identically to before for current templates
- New TBE dashboard (when TBE template is loaded) renders the 3-2-1 + 5 ratings layout cleanly without any custom code
- Permission scoping holds across all aggregation queries
- CSV export works
- Editor's dashboard preview is useful for admins
- Tests pass, linter passes, build succeeds
- Documentation written
- Commit history is structured (suggest: widget map + generic widgets, role widgets, aggregation endpoint, dashboard refactor, CSV export, editor preview integration, docs)

Out of scope:
- Custom drag-and-drop dashboards (v3 feature)
- Cross-template reporting (waits for FieldKey usage to mature in production)
- Real-time updates (current pattern is page-load fetch; that's fine for v1)
- Saved dashboard views / bookmarks
```

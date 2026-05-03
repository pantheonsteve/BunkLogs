Build the Leadership Team dashboard. LT users see unit-level views with completion status and themes — but only have access to year-round team data per Alyson's note.

Tasks:
1. Create route /team/dashboard or similar.
2. Route guarded: only Memberships with role='leadership_team' or 'admin' can access.

3. Dashboard sections:
   - **Unit health overview**: For each unit the user has access to, show:
     * Total staff
     * Completion rate this period
     * Average rating per category (rolled up from individual reflections)
     * Trend indicator (up/down vs prior period)
   - **Concerning patterns**: Reflections with low ratings (1-2) flagged for attention
   - **Open questions**: The "1 question/concern" field surfaced from recent reflections
   - **Year-round team filter**: toggle to show only year-round vs. seasonal staff

4. API support:
   - Add /api/v1/dashboards/team/ endpoint
   - Returns aggregated data scoped to the LT user's accessible units
   - Respects "year-round only" filter

5. Use existing chart/visualization libraries already in project. Simple table-based summaries are fine for v1.

6. Tests:
   - LT user sees their units
   - LT user does NOT see other units
   - Year-round filter works
   - Aggregations are correct
   - Permission gate enforced (regular counselors get 403)

Acceptance criteria:
- Dashboard renders with correct data
- Permissions enforced
- Tests pass (backend and frontend)
- Smoke test in dev with seeded data
- Commit with message: "Add Leadership Team unit health dashboard"
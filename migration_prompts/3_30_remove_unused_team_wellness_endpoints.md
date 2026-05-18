# Prompt 3.30 — Remove unused team/wellness backend endpoints

**Wave:** 3 (Crane Lake Summer 2026 Build) — UI cleanup
**Estimated time:** 1-2 hours
**Prerequisite:** Prompt 3.29 complete.

**Use the context prompt at the top of `migration_prompts/0_0_context_prompt.md` before this session.**

---

```
The 3.20 era shipped two role-bespoke aggregation endpoints --
TeamDashboardView at /api/v1/dashboards/team/ and WellnessDashboardView
at /api/v1/dashboards/wellness/. The frontend never consumed them. The
3.20 trends/concerns/subject/coverage refactor and the eventual
TemplateDashboard component replaced the use case: the leadership and
wellness pages now hit /api/v1/templates/?is_active=true, filter
client-side by role, and render the generic TemplateDashboard over the
selected template id. Net effect: ~1500 lines of view code + tests with
no callers.

CONTEXT (verified before writing this prompt):

- `frontend/src/pages/TeamDashboardPage.jsx` and
  `frontend/src/pages/WellnessDashboardPage.jsx` make exactly one
  network call each, both to `/api/v1/templates/?is_active=true`.
- `grep` across `frontend/` finds zero references to
  `/api/v1/dashboards/team/`, `/api/v1/dashboards/wellness/`,
  `TeamDashboardView`, or `WellnessDashboardView`.
- The only backend importers of team_dashboard / wellness_dashboard
  modules are `bunk_logs/api/urls.py` and their own test files.
- `seed_team_dashboard_demo.py` (a one-off Django shell script) exists
  only to populate fixture data for /api/v1/dashboards/team/. Without
  that endpoint, the script has no purpose.
- One doc paragraph in `docs/membership-role-vs-capability.md` cites
  `api/wellness_dashboard.py::WELLNESS_ACCESS_ROLES` as evidence that
  "route access != reflection visibility". The point still holds via
  other examples, but the citation has to be rewritten because the
  module is going away.

GOALS:

1. Drop dead code: delete the views, their tests, the URL routes, and
   the demo seed script.
2. Keep the frontend untouched. TeamDashboardPage and
   WellnessDashboardPage continue to work because their data source
   (/api/v1/templates/ + TemplateDashboard) is unaffected.
3. Update the one doc paragraph that referenced the deleted module so
   future readers don't chase a missing file.
4. Preserve test coverage of visibility / aggregation: nothing unique
   lives in the deleted views -- rating averaging, period parsing,
   concerning-row detection, etc. are also covered by
   `template_dashboard.py`, `dashboards/concerns.py`, and
   `dashboards/subject.py` (and their tests).

OUT OF SCOPE:

- Building richer team/wellness aggregation UI on top of the deleted
  payloads. That is a feature task and gets its own future prompt.
- Touching `_unit_scoped_supervisor_q` / `_wellness_q` helpers in
  `core.permissions.visibility`. Those are independent of the API
  module and still used by `reflections_visible_to`.
- Renaming the frontend routes /dashboards/team and
  /dashboards/wellness. They keep working; only the backend endpoints
  at the same path go away.

TASKS:

1. Delete the following files outright:
     - `backend/bunk_logs/api/team_dashboard.py`
     - `backend/bunk_logs/api/wellness_dashboard.py`
     - `backend/bunk_logs/api/tests/test_team_dashboard.py`
     - `backend/bunk_logs/api/tests/test_wellness_dashboard.py`
     - `backend/scripts/seed_team_dashboard_demo.py`

2. Edit `backend/bunk_logs/api/urls.py`:
     - Drop `from . import team_dashboard`
     - Drop `from . import wellness_dashboard`
     - Drop the two `path("dashboards/team/", ...)` and
       `path("dashboards/wellness/", ...)` entries.

3. Edit `docs/membership-role-vs-capability.md`:
     - Rewrite the paragraph that cites
       `api/wellness_dashboard.py::WELLNESS_ACCESS_ROLES`. Keep the
       point ("camper_care needs unit-wide reflection visibility, which
       is broader than just wellness-flavor templates") but drop the
       dashboard-route example. The doc should not reference removed
       modules.

4. Run `make test-backend`. Expect 605 -> ~570 tests (whatever the team
   + wellness suites contributed) and all green. Verify nothing else
   imported the deleted modules.

5. Run `make test-frontend`, `npx vite build`, and
   `ruff check bunk_logs/ config/`. All clean -- no frontend changes
   were made, so existing tests must still pass unchanged.

6. Commit + PR `3_30_remove_unused_team_wellness_endpoints: ...`.
```

---

## Acceptance criteria

- `git grep TeamDashboardView` and `git grep WellnessDashboardView`
  return zero matches.
- `/api/v1/dashboards/team/` and `/api/v1/dashboards/wellness/` return
  404 (no URL pattern). The frontend pages at /dashboards/team and
  /dashboards/wellness still render because they don't depend on these
  endpoints.
- All remaining backend tests pass; no test imports from the deleted
  modules.
- `docs/membership-role-vs-capability.md` no longer mentions
  `wellness_dashboard.py`.
- Diff is overwhelmingly deletions; no new feature surface.

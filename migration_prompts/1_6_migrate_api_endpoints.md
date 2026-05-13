Based on `docs/api-consolidation-plan.md`, migrate all endpoints from `/api/` to `/api/v1/`.

Tasks:
1. For each endpoint marked MIGRATE:
   a) Add the route to /api/v1/ if not already there
   b) Add a redirect from old /api/ to /api/v1/ (RedirectView, permanent=False)
   c) Update React frontend fetch calls
2. For DELETE: remove route, view, and frontend code.
3. For KEEP: confirm already under /api/v1/.
4. After all changes, only redirects remain at /api/.
5. Run test suite and frontend build.
6. Smoke test major flows: login, view bunks, submit a bunk log.

Acceptance criteria:
- All active endpoints under /api/v1/
- /api/ paths are redirects only
- Frontend uses /api/v1/ exclusively
- Tests and build pass
- Smoke tests pass
- Commit with message: "Consolidate API endpoints under /api/v1/"

Split into smaller commits by endpoint group if scope is large.
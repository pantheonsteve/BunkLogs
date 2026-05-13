Switch Crane Lake's legacy frontend code paths from old API to new API. New endpoints already exist (built in Wave 3).

Tasks:
1. Inventory: every component calling /api/v1/bunklogs/, /api/v1/campers/, etc. Output as docs/clc-frontend-migration.md.
2. For each old call: identify equivalent new endpoint.
3. Migrate component-by-component, lowest-risk first.
4. Tests for each migrated component.
5. Smoke test on staging.
6. Keep old API endpoints functional during transition.

Acceptance criteria:
- All Crane Lake frontend uses new API
- Tests pass
- Staging smoke tests pass
- Multiple commits, one per batch (e.g., "Migrate CLC bunk list to new API")

Estimate: 3-5 commits.
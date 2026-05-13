Remove old API endpoints. Frontend already migrated.

Tasks:
1. List old routes.
2. Verify no callers.
3. Remove routes, views, serializers.
4. Run tests.
5. Smoke test on staging.

Acceptance criteria:
- Old endpoints return 404
- Frontend works
- Tests pass
- Commit with message: "Remove deprecated API endpoints for old camp models"
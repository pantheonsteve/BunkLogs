The codebase has two parallel API trees: `/api/` and `/api/v1/`. Before consolidating, we need a clear inventory.

Tasks:
1. Read URL configuration files (urls.py at project and app level).
2. Produce a markdown table at `docs/api-consolidation-plan.md` with:
   - Endpoint path under /api/
   - Endpoint path under /api/v1/ (if exists)
   - Viewset/view function name
   - HTTP methods supported
   - Currently used by frontend? (yes/no/unknown)
   - Currently used by external integration? (yes/no/unknown)
3. For each endpoint, recommend: KEEP under /api/v1/, MIGRATE from /api/ to /api/v1/, or DELETE.

Acceptance criteria:
- Markdown file exists with complete inventory
- Every endpoint has a recommendation
- Commit with message: "Document API consolidation plan"

Do NOT make code changes. Inventory only.
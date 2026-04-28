This is the BunkLogs codebase. Stack: Django 5.0.13 + DRF, React 19 + Vite + Tailwind/MUI, PostgreSQL, Redis, Celery, Podman for local dev, Render for production hosting.

Current state: single-tenant deployment serving URJ Crane Lake Camp. Old data model hierarchy is Session → Unit → Bunk → CamperBunkAssignment → BunkLog. Production URLs are admin.bunklogs.net and clc.bunklogs.net.

We are in the middle of a Strangler Fig migration to a multi-tenant SaaS architecture. New models (Organization, Program, Person, Membership, ReflectionTemplate, Reflection) coexist alongside the old ones. The old models still serve Crane Lake's existing data; new models will serve Crane Lake's Summer 2026 expansion (role-based forms for Kitchen, Maintenance, Housekeeping, Wellness, Junior Counselors, Specialists, GCs, Leadership Team) AND a new Temple Beth-El customer launching Fall 2026.

Critical constraints:
- DO NOT modify old models or break Crane Lake's existing functionality unless explicitly asked
- DO NOT introduce new frameworks or major dependencies without confirmation  
- All NEW features must be built on the new multi-tenant architecture (never extend old models for new use cases)
- ReflectionTemplate.schema must support localized prompts (English/Spanish) from day one, even when only English is used initially

Style preferences: minimal formatting in code (no excessive comments), Python type hints where helpful, follow existing project conventions. Test changes with pytest. Frontend changes verified with `npm run build` and existing Vitest tests.

Completion requirements for every migration step:
1. Run `make test-backend` (must pass) and `make test-frontend` (must pass) before committing.
2. Commit using the step ID as a conventional-commit scope so the migration dashboard can detect it — e.g. `git commit -m "feat(1_2_resolve_duplicate_viewset): ..."`. The step ID must appear verbatim in the commit message.
3. After committing, push the branch and open a pull request with `gh pr create`. The PR title should start with the step ID. Do not consider the step done until the PR is open.
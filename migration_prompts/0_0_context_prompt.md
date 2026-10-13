This is the BunkLogs codebase. Stack: Django 5.2 LTS + DRF, React 19 + Vite 6 + Tailwind 4, i18next, PostgreSQL, Redis, Celery, Podman for local dev (always via `make` targets; never run `manage.py` on the host), Render for production hosting.

Current state (as of October 2026): multi-tenant SaaS, one subdomain per organization, API and Django admin at admin.bunklogs.net. The Strangler Fig migration is complete. Live tenants:
- Crane Lake Camp (slug `clc`, clc.bunklogs.net) — summer camp, role-based reflections for counselors, support staff (English/Spanish), wellness team, specialists, JCs, GCs, and Leadership Team
- Temple Beth-El (slug `tbe`, tbe.bunklogs.net) — religious school, weekly 3-2-1 Madrichim reflections, faculty and Director queue-first homepages

Models: Organization → Program → Person → Membership → ReflectionTemplate → Reflection. Crane Lake's historical data has been migrated; the legacy models (Session → Unit → Bunk → CamperBunkAssignment → BunkLog) are frozen read-only (6_1) and the legacy frontend is retired (6_2). Dropping the legacy tables (6_3) is still pending.

Current focus:
1. TBE feature requests and UX polish. Steve has been the only admin so far; client admins must now be able to run their own org without him.
2. Wave 7 (`bunklogs-onboarding-prompts.md`): onboarding a new organization in under 4 hours of hands-on time, ahead of up to five new camps in May–June 2027.

Critical constraints:
- DO NOT modify the legacy models or apps (`bunks`, `campers`, `bunklogs`) unless explicitly asked
- DO NOT introduce new frameworks or major dependencies without confirmation
- ReflectionTemplate.schema must support localized prompts (English/Spanish) from day one, even when only English is used initially

Multi-tenancy rules (non-negotiable):
- `OrgScopedManager` fail-closed is the enforcement mechanism. Never bypass it with `all_objects` outside management commands, migrations, or explicitly cross-org admin code.
- Every outbound absolute URL (emails, password reset links, redirects, reminder links) must be built from the organization, never from a global setting, `SITE_ID`, or a hardcoded domain. Request-bound code uses `request.organization`; Celery tasks resolve the org from the record being processed.
- No hardcoded organization slugs (`clc`, `tbe`) outside that organization's own setup/onboarding commands and fixtures.
- Any new feature touching auth, email, or redirects needs a test proving it resolves correctly for at least two different organizations.
- New organizations are configuration, not code. If onboarding a new customer would require a code change, treat that as a bug in the platform.

One product for camps and schools:
- Every feature must work for both a summer camp and a religious school. A feature requested by TBE is built so a camp can use it, and vice versa.
- The only per-customer differences are terminology and per-org settings. Do not branch on `program_type`, `isReligiousSchoolOrg`, org slug, or a school-only or camp-only role. If a feature is optional, gate it with an `Organization.settings` flag, not the customer type.
- All user-visible nouns go through `term()` (backend, `core/terminology.py`) or `useTerm()` (frontend). Canonical keys stay the camp words (`camper`, `bunk`, `counselor`, `unit_head`, `director`) and are display-only: never use terminology to derive permissions or look up rows. When touching a screen, convert any hardcoded nouns on it.
- Role equivalents: Camper ↔ Student, Counselor ↔ Madrich, Unit Head ↔ Faculty, Bunk ↔ Class, Director ↔ Ed Team.

Admin usability (client admins, not Steve):
- Every routine admin task (people, groups, programs, templates, imports, settings) must be doable in the app by a non-technical admin, with no Django admin and no management commands.
- Empty states say what to do next; errors say how to fix the problem; destructive actions require confirmation (see Setup's program deletion).
- When a fix needs Steve to intervene in the database, treat it as a missing admin feature.

Architecture conventions:
- Template behavior is driven by additive schema flags on ReflectionTemplate field definitions (`thread_enabled`, `thread_scope`, `routes_to`, `share_with_cohort`, `trend_key`), not hardcoded field names
- All comment trails share one thread substrate (`EntryThread` / `ThreadMessage`)
- Permission checks use `Membership.capability` (derived from `role` via `ROLE_TO_CAPABILITY`); `role` is for template routing and labels. Never set `role` with `QuerySet.update()` or `bulk_create` in app code, since that skips the capability sync
- Org-admin capability is `Membership.role='admin'`; gate admin endpoints with `admin_only_or_403`
- Template version-family identity is `(organization, slug)`, not the `parent_template` chain
- `Reflection.person` is the submitter, not the subject
- Test fixtures may use `bulk_create` to bypass model-level validation
- Additive over replacement; defer abstractions until real requirements force them

Frontend conventions:
- Build UI from the `components/ui` primitives (Card, DataTable, PageHeader, EmptyState, ConfirmDialog, FilterBar, Modal, Toast, KpiTile, AttentionCard, etc.) and the semantic color tokens from 8_1. No one-off colors or ad hoc component styling.
- Pages must be usable at phone width; counselor and madrich flows are phone-first.

Audit before implement: every prompt with unknowns starts with a pre-flight audit section. Report findings before writing code.

Style preferences: minimal formatting in code (no excessive comments), Python type hints where helpful, follow existing project conventions. Test changes with pytest. Frontend changes verified with `npm run build` and existing Vitest tests. Lean execution by default (see CLAUDE.md).

Completion requirements for every step:
1. Run `make test-backend` (must pass) and `make test-frontend` (must pass) before committing.
2. Commit using the step ID as a conventional-commit scope, e.g. `git commit -m "feat(8_5_supervisor_home): ..."`. The step ID must appear verbatim in the commit message.
3. After committing, push the branch and open a pull request with `gh pr create`. The PR title should start with the step ID. Do not consider the step done until the PR is open.
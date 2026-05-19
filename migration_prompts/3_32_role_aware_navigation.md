# Prompt 3.32 — Role-aware navigation restructure

**Wave:** 3 (Crane Lake Summer 2026 Build) — UI cleanup, post-audit follow-up
**Estimated time:** 3-4 hours
**Prerequisite:** Prompt 3.31 complete.

**Use the context prompt at the top of `migration_prompts/0_0_context_prompt.md` before this session.**

---

```
The 3.27-3.31 audit cleaned up admin chrome and built shared UI
primitives, but the sidebar itself is still the original structure --
flat, ungrouped except for two admin submenus, and gated on legacy
`User.role` strings (Title Case 'Admin' / 'Counselor' / 'Unit Head'
/ ...). Two adjacent symptoms:

1. Admins see *duplicate* links to /dashboards/team and
   /dashboards/wellness: once as top-level shortcuts ("Unit health
   (LT)" / "Wellness team", Sidebar.jsx:193-234) and once under the
   Dashboards submenu (Sidebar.jsx:496-526). Same URLs, twice.
2. The frontend has no notion of capability. Backend RBAC is
   organized around Membership.capability (participant / supervisor /
   program_lead / domain_specialist / admin) and `is_super_admin`,
   but the sidebar still reads `user.role === 'Admin'` strings. There
   is no `hasCapability` helper anywhere in frontend/src.

This prompt is the structural fix: introduce a frontend capability
helper that mirrors backend ROLE_TO_CAPABILITY, then restructure the
sidebar around capability tiers with discrete sections for each
audience. The auto-redirect Dashboard.jsx becomes a real Home page
in the next PR (3.33); this one stops at the sidebar.

REQUIREMENTS

- New helper `frontend/src/utils/auth/capability.js` exporting:
    - `CAPABILITIES` (ordered tuple, admin strongest)
    - `userCapability(user)` returning the user's capability bucket
      derived from `user.role` (legacy User.role; the helper is the
      one place we'll swap to membership-based later)
    - `hasCapability(user, capOrList)` boolean, inclusive of "at
      least this tier" semantics for admins
    - `useCapability()` hook wrapping useAuth
  Coverage tests for every legacy User.role string in
  backend/bunk_logs/users/models.py and a "no user" path.

- Sidebar restructure (Sidebar.jsx) into these sections, top-down:

    MY WORK         (everyone)
      My tasks                  /tasks
      File a reflection         /reflect              (reflection roles)
      My reflections            /my-reflections       (reflection roles)

    SUPERVISE       (supervisor+, includes admin / super_admin)
      Coverage                  /supervisor/coverage
      Concerns about my unit    /dashboards/concerns

    DASHBOARDS      (program_lead+ or super_admin)
      Overview                  /dashboards
      Coverage                  /dashboards/coverage
      Author attribution        /dashboards/authors
      Unit head dashboard       /dashboards/team
      Wellness dashboard        /dashboards/wellness
      (Concerns inbox lives in SUPERVISE only -- not duplicated here)

    ADMIN           (admin or super_admin)
      Admin home                /admin
      Memberships               /admin/memberships
      Templates                 /admin/templates
      Assignment groups         /admin/groups
      Field keys                /admin/field-keys

    CRANE LAKE LEGACY (admin or super_admin, with tooltip)
      Bunk logs                 /admin-bunk-logs
      Staff reflections         /admin-dashboard

    OTHER
      Orders                    /orders               (everyone)

- Counselor home (/counselor-dashboard) stays for the Counselor role
  but moves into the MY WORK section so it sits with the
  participant's other personal entry points. Drop the special
  Counselor-only standalone link in favor of being a participant-tier
  default for users whose User.role === 'Counselor'.

- The `extraLinks` prop on Sidebar is removed. The Camper Care extra
  "My Bunk Logs" / "Needs Attention" buttons were a workaround for
  the missing Supervise section; with Supervise present, those views
  remain reachable from CamperCareDashboard's own in-page tabs, and
  the sidebar no longer ships per-page injections.

- All sidebar gates flip from `user.role === '...'` literals to
  `hasCapability(user, [...]) || isSuperAdmin(user)`. The only
  remaining `user.role` reference allowed in Sidebar.jsx is the
  Counselor-home check inside MY WORK (because it's a per-role
  workspace shortcut, not a capability gate).

- Update `frontend/src/partials/__tests__/Sidebar.test.jsx` to assert
  the new section structure per persona (admin, leadership,
  unit_head, camper_care, counselor, no_role). Use the existing
  vi.mock pattern.

- Update `frontend/e2e/rbac-sidebar.spec.ts`:
    - Fix the stale HREFS for /team/dashboard and /wellness/dashboard
      (they should be /dashboards/team and /dashboards/wellness).
    - Update the per-persona assertions to match the new structure.
    - Add coverage for /supervisor/coverage and the legacy section.

OUT OF SCOPE (handled in 3.33 or 3.34)

- The /dashboard landing page (still auto-redirects in 3.32).
- ?next= post-login wiring.
- Sidebar visibility on /tasks and /reflect (those routes
  intentionally render without the Sidebar today; revisit later).
- Backend changes. Frontend-only PR.

VERIFICATION

- `npx vitest run` 100% green including the new
  capability tests and the updated Sidebar tests.
- `npx vite build` clean.
- Manual smoke: log in as each test user from
  `frontend/e2e/fixtures/users.ts` and visually confirm the sidebar
  sections match the matrix in this prompt.
- Commit + PR titled `3_32_role_aware_navigation: ...`.
```

---

## Acceptance criteria

- `frontend/src/utils/auth/capability.js` exists with `userCapability`, `hasCapability`, `useCapability`, and a `CAPABILITIES` constant; unit tests cover every legacy role string + null/undefined paths.
- `frontend/src/partials/Sidebar.jsx` renders the sections above, in order, with capability-based gates.
- No admin user sees a duplicate link to `/dashboards/team` or `/dashboards/wellness`.
- `Field keys` appears under Admin in the sidebar.
- `extraLinks` prop is removed from Sidebar, and CamperCareDashboard no longer passes it.
- `e2e/rbac-sidebar.spec.ts` HREFS table uses `/dashboards/team` and `/dashboards/wellness` (no more `/team/dashboard`).

## Known limitation (documented, not fixed here)

The helper derives capability from `user.role` (Title Case legacy string), which can't distinguish `health_center` from `camper_care` (both have `User.role = 'Camper Care'` today). They render the same supervisor-tier sidebar; this matches today's behavior and is documented in `capability.js`. The proper fix is to read `Membership.capability` from `/api/v1/memberships/me/` and expose it on `useAuth`; that's tracked as a follow-up.

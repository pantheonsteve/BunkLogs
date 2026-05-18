# Prompt 3.26 — Admin navigation hub

**Wave:** 3 (Crane Lake Summer 2026 Build) — UX cleanup so admins can
actually find the surfaces we already built (Templates / Memberships /
Groups / Dashboards) without memorizing URLs.
**Estimated time:** 4-5 hours
**Prerequisites:** 3.21-3.25 merged.

**Use the context prompt at the top of `0_0_context_prompt.md` before this session.**

---

```
The new RBAC admin tooling has shipped in pieces: MembershipManagementPage
(/admin/memberships), TemplateListPage + split-pane editor
(/admin/templates), GroupListPage (/admin/groups), and a fistful of
dashboards under /dashboards/* plus two off-pattern ones (/team/dashboard,
/wellness/dashboard). Each page works, but discoverability is broken:

- The Sidebar's admin group is labelled "Tests" (scaffolding placeholder).
- The Sidebar admin group is missing Memberships, the Team dashboard,
  the Wellness dashboard, and Subject trends. It conflates admin work
  with personal items ("My tasks", "Reflection form").
- There is no /admin landing page -- TemplateListPage's breadcrumb says
  "Admin" but points to /admin/memberships, which is wrong and surprising.
- There is no /dashboards landing page -- every dashboard URL is
  type-it-from-memory.
- /team/dashboard and /wellness/dashboard use a different URL prefix
  from the rest of /dashboards/*.

Tasks:

1. Add ``/admin`` landing page (``frontend/src/pages/admin/AdminHub.jsx``)
   gated by ``AdminRoute``. Card grid linking to:
     - Memberships -> /admin/memberships
     - Reflection templates -> /admin/templates
     - Assignment groups -> /admin/groups
     - Dashboards -> /dashboards (link, not embed)
     - Field keys -> /admin/field-keys (placeholder card marked
       "Coming soon", no link; FieldKey UI is a separate prompt)
   Each card: title, one-sentence purpose, lucide icon, optional
   "deferred" pill. Mobile = single column. Wraps in a max-w-5xl
   container with consistent header/breadcrumb-less framing (admin
   index is the breadcrumb root).

2. Add ``/dashboards`` landing page
   (``frontend/src/pages/dashboards/DashboardsHub.jsx``) gated by
   ``ProtectedRoute`` (NOT admin-only -- counselors and supervisors
   use these too). Card grid:
     - Coverage -> /dashboards/coverage
     - Subject trends -> /dashboards/subject-trends (no groupId so the
       card links to a stub page or a "pick a group" picker; if the
       picker is too much, link to /admin/groups with a hint to click
       a group, OR omit and document)
     - Author attribution -> /dashboards/authors
     - Concerns inbox -> /dashboards/concerns
     - Team dashboard -> /dashboards/team
     - Wellness dashboard -> /dashboards/wellness
   Optionally tag each card with the role gate (e.g. "Supervisors
   only", "Wellness team only") sourced from the same role lists the
   backend uses; if the role lists aren't trivially accessible from
   the FE, hardcode the labels as strings -- a future polish PR can
   wire them up.

3. URL consistency for the two off-pattern dashboards:
   - Wire NEW routes:
     - /dashboards/team   -> TeamDashboardPage
     - /dashboards/wellness -> WellnessDashboardPage
   - Keep the OLD routes (/team/dashboard, /wellness/dashboard) as
     ``<Navigate to="/dashboards/team" replace>`` so existing bookmarks
     still land. Don't delete the old routes.
   - Anywhere in the codebase that links to the old URLs (sidebar,
     dashboards, tests) gets pointed at the new one.

4. Sidebar reorg (``frontend/src/partials/Sidebar.jsx``):
   - Rename the "Tests" group to "Admin".
   - Items, in this order:
     - Admin home -> /admin           (new top-level link inside group)
     - Memberships -> /admin/memberships
     - Templates -> /admin/templates
     - Assignment groups -> /admin/groups
   - Move the dashboards into a SEPARATE sidebar group called
     "Dashboards" (same gating: visible when the user can see at
     least one dashboard; for now reuse the existing admin gate
     ``user?.role === 'Admin' || isSuperAdmin(user)`` -- a follow-up
     can broaden it to supervisors / counselors as we wire up the
     non-admin entry points).
     Items inside Dashboards group:
       - Dashboards home -> /dashboards
       - Coverage -> /dashboards/coverage
       - Author attribution -> /dashboards/authors
       - Concerns inbox -> /dashboards/concerns
       - Team -> /dashboards/team
       - Wellness -> /dashboards/wellness
   - Move "My tasks" and "Reflection form" OUT of the admin group --
     "Reflection form" already has a top-level entry for roles in
     ``REFLECTION_FORM_ROLES``. "My tasks" should become a top-level
     entry above Orders, gated identically (any authenticated user).

5. Fix the TemplateListPage breadcrumb. Currently it links to
   /admin/memberships but says "Admin". Point it at /admin instead.
   While here, audit MembershipManagementPage and GroupListPage for
   the same pattern and align them (one ``Link`` back to /admin with
   the text "Admin", consistent ArrowLeft icon).

6. Tests:
   - ``frontend/src/pages/admin/__tests__/AdminHub.test.jsx`` -- 3
     specs (renders the five expected cards; deferred card has no
     link; clicking memberships routes to /admin/memberships).
   - ``frontend/src/pages/dashboards/__tests__/DashboardsHub.test.jsx``
     -- 2 specs (renders the six dashboard cards; clicking the
     coverage card routes to /dashboards/coverage).
   - ``frontend/src/partials/__tests__/Sidebar.test.jsx`` (or
     wherever Sidebar tests live; create if missing) -- 2 specs:
     "Admin" group label appears (not "Tests"); memberships link is
     present inside the admin group.
   - Tighten the existing TemplateListPage test if it asserts on the
     breadcrumb target.

Acceptance:
- ``make test-frontend`` adds the new specs and keeps the existing
  191 green.
- ``make test-backend`` unchanged (no backend changes in this PR).
- Manual sanity-check: log in as an admin, navigate from Sidebar to
  Admin home, click each card, click back -- everything reachable
  without typing URLs.

Out of scope:
- FieldKey registry CRUD UI (placeholder card only; separate prompt).
- Broadening dashboard visibility for non-admin supervisors -- the
  sidebar group still uses the admin gate; a follow-up can wire the
  per-dashboard role gates into the sidebar.
- Subject-trends "pick a group" picker if too much for this PR; the
  Subject trends card can link to /admin/groups with a hint in the
  card copy.

Commit structure (single PR):
  1. docs(3_26_admin_navigation_hub): plan
  2. feat(3_26_admin_navigation_hub): /dashboards hub + URL aliases for team/wellness
  3. feat(3_26_admin_navigation_hub): /admin hub landing page
  4. refactor(3_26_admin_navigation_hub): sidebar Admin + Dashboards groups
  5. fix(3_26_admin_navigation_hub): align admin breadcrumb targets
  6. test(3_26_admin_navigation_hub): cover new hubs + sidebar rename
```

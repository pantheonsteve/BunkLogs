# 10_5 — One Reflections dashboard for camps and schools

**Step ID:** `10_5_reflections_dashboard_consolidation`
**Estimated time:** 4–6 hours
**Mode:** lean, except change 4 (a permission gate) — give that one the full-mode tests listed below
**Depends on:** 10_4
**Branch:** `feat/reflections-dashboard-consolidation`, one PR
**Source:** BunkLogs URL Consistency Audit (Claude Doc), PR 1

```
Goal: /dashboards/reflections is the single Reflections dashboard for every
org. /admin/reflections (the TBE-only Madrich completion page) is retired;
its roster becomes a "Completion" tab on /dashboards/reflections, turned on
by an Organization.settings flag rather than by program type. All
/dashboards/* pages share one layout so the sidebar behaves the same
everywhere.

Problems this fixes:
1. The Reflections nav item disappears on /dashboards/reflections for a TBE
   admin. Sidebar.jsx renders /dashboards/reflections for camps
   (surfaces.campDashboards) and /admin/reflections for schools
   (!surfaces.campDashboards && hasReflectionWork). hasReflectionWork for an
   admin with no personal reflection role depends on
   navBadges.questionsForYou, and only AdminLayout passes navBadges. The
   /dashboards/* pages mount their own <Sidebar> with no badges.
2. Form tiles on /dashboards/reflections link to
   /admin/templates/:id/responses. The page is shown to supervisors,
   madrichim, camper care, kitchen staff and specialists, but only admins
   can open responses, so those users are bounced home with "Admin access
   required".
3. Program leads can reach the responses route (LeadershipTemplatesRoute
   allows program_lead) but LeadershipTeamTemplateResponsesView calls
   admin_only_or_403, so the API 403s for them.

Decision (Steve, 2026-10-16): only admins and program leads see the
Reflections dashboard and open a form's responses. Everyone else keeps
their own reflection pages (My reflections, /<role>/history, etc.).

Pre-flight (report briefly, then continue — no stop needed):
- List every link to /admin/reflections (index only, not its sub-routes)
  in frontend/src and backend (director.py growth_dashboard_url is a
  sub-route and stays).
- Confirm how Organization.settings reaches the frontend (per-org auth
  payload / currentOrgContext). If it does not, expose the one flag below
  the same way program_types is exposed.

Changes:
1. Shared layout for /dashboards/*.
   - Move every /dashboards/* route in routeConfig.jsx (logs, reflections,
     coverage, concerns, authors, wellness, the hub, subject-trends, group,
     bunk redirect) under one layout route that renders Sidebar with
     navBadges (reuse useNavBadges from AdminLayout, or move the badge
     fetch into a hook both layouts call).
   - Remove the per-page <Sidebar>/<Header> from those pages and from
     AssignmentTemplatesDashboard.
   - The wrapper still uses protect(); page-level gates stay as they are.

2. One Reflections nav item.
   - Sidebar.jsx: replace both org-specific Reflections items (admin-style
     nav) with one item to /dashboards/reflections, shown when
     canAdmin || canSeeDashboards (program_lead) || isSuperAdmin. No
     surfaces.* check.
   - Default (non-admin, non-LT) nav: remove the /dashboards/reflections
     items. Those users keep their personal reflection links.
   - Update the IA comment block at the top of Sidebar to match.

3. Responses move under the dashboard.
   - New route /dashboards/reflections/:templateId renders the existing
     LeadershipTeamResponses page (same component, guarded like
     ltTemplates today).
   - Same for logs: /dashboards/logs/:templateId.
   - FormTile in AssignmentTemplatesDashboard links to
     /dashboards/<scope>/:templateId?date=...
   - /admin/templates/:id/responses redirects to
     /dashboards/reflections/:id, keeping the query string, so emailed
     links and bookmarks still work.
   - responsesBackLink(): back goes to /dashboards/reflections (or logs)
     for every org; drop the homePath short-circuit for role-based orgs.

4. Program leads can read responses (the only backend change).
   - LeadershipTeamTemplateResponsesView and its export view: read gate is
     active admin OR active program_lead membership OR super admin. Keep
     admin_only_or_403 for every write surface (builder, publish,
     assignments). Rows stay filtered by reflections_visible_for_user —
     do not widen the queryset.

5. Completion tab.
   - New Organization.settings flag: "reflection_completion" (bool,
     default false). Data migration (idempotent, reverse noop) sets it true
     for slug "tbe" only.
   - /dashboards/reflections gets two tabs: "Forms" (today's picker,
     default) and "Completion", the second shown only to admins when the
     flag is on. Tab state in the URL: ?tab=completion.
   - Completion renders the current AdminReflectionsDashboard roster
     (move it into dashboards/reflections/CompletionTab.jsx). Replace the
     hardcoded ROLE = 'madrich' with a role select listing the org's
     membership roles that have self-reflection templates; default to the
     first. The backend already takes role as a path param.
   - Keep the grade filter only when the roster rows carry grades (hide it
     otherwise) so the tab works for a camp too. Labels through term().
   - Keep the CSV export.

6. Retire /admin/reflections (index only).
   - Route becomes <Navigate to="/dashboards/reflections?tab=completion"
     replace />.
   - adminNavConfig.adminReportLinks: drop the "Madrich completion" entry;
     growth and availability stay. Change the gradeReflections surface
     gate for those two to the same settings flag.
   - Back links in AvailabilityMatrix.jsx and AdminGrowthDashboard.jsx go
     to /dashboards/reflections?tab=completion.
   - Keep /admin/reflections/growth, /admin/reflections/availability and
     /admin/reflections/:role/members/:membershipId unchanged (linked from
     DirectorHome, CoverageDetailModal, Responses, director.py).
   - Delete AdminReflectionsDashboard.jsx once CompletionTab replaces it.

Do not:
- Branch on program_type, isReligiousSchoolOrg, or org slug in new code.
  orgSurfaces() stays for other surfaces; just stop using it for
  Reflections.
- Rename other URLs from the audit (PR 2 and PR 3 cover those).
- Touch the admin_flow reflections API paths.

Tests (lean):
- Sidebar: admin at a school org and a camp org both see one Reflections
  item to /dashboards/reflections, on /admin/home and on
  /dashboards/reflections (regression for problem 1); a madrich and a
  supervisor do not see it.
- Routing: /admin/reflections and /admin/templates/5/responses?date=x
  redirect correctly.
- Reflections page: Completion tab hidden when the flag is off or the user
  is a program lead; shown for an admin with the flag on; ?tab=completion
  opens it.
- Backend (full-mode for change 4): program_lead GET responses 200 and
  only sees reflections_visible_for_user rows; program_lead POST/PATCH to
  builder/publish still 403; unrelated role 403; admin unchanged.
- Data migration: tbe gets the flag, clc doesn't, rerun is a no-op.
- Update or remove the existing tests that assert the old links:
  Sidebar.test, adminNavConfig.test, hubs.test, DirectorHome.test,
  Responses.test, responsesBackLink.test, AdminReflectionsDashboard.test
  (move what still applies to CompletionTab).

Acceptance criteria:
- A TBE admin and a Crane Lake admin see the same Reflections nav item,
  page and click path; only the words differ.
- The nav item never disappears on any /dashboards/* page, and nav
  badges show there.
- No user is shown a form tile they can't open.
- Old /admin/reflections and /admin/templates/:id/responses links land on
  the right page.
- make test and npm run build pass.
```

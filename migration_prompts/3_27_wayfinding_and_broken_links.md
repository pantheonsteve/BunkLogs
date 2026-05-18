# Prompt 3.27 — Wayfinding fixes and broken summary deep-links

**Wave:** 3 (Crane Lake Summer 2026 Build) — UI cleanup
**Estimated time:** 3-4 hours
**Prerequisite:** Prompt 3.26 complete.

**Use the context prompt at the top of `migration_prompts/0_0_context_prompt.md` before this session.**

---

```
After the admin/dashboards hubs landed in 3.26, an audit surfaced several real
functional bugs in the new RBAC stack plus some leftover wayfinding gaps. This
prompt fixes them in a single small slice. Polishy "design tokens" work is
deferred to 3.31; this PR is strictly about routes that don't work, links that
don't go where the label suggests, and orphan pages that nothing links to.

CONTEXT:

Audit findings (Wave 3 only; legacy single-tenant pages were ignored):

1) Broken `/reflect/summary?reflection=<id>` deep links. Three new dashboard
   components generate links of this form:
     - frontend/src/dashboards/concerns/ConcernsInbox.jsx ("Open reflection")
     - frontend/src/dashboards/subject/SubjectDetail.jsx (two: "View
       reflection" on concerning patterns, "view" on each reflection row)
     - frontend/src/dashboards/trends/TrendCell.jsx (the colored cell link)
   But `ReflectionSummaryPage` only reads `location.state` set by the form's
   post-submit redirect. Query-string visits land on the "No reflection
   summary to show" branch. All four call sites are silently broken.

   ReflectionTasksPanel.jsx (coverage popover "View" button) also navigates to
   `/reflections/${reflection_id}`, but that route does not exist in
   Router.jsx, so it 404s and bounces to /dashboard. Same underlying gap.

2) Counselor sidebar misroute. For `user.role === 'Counselor'`, Sidebar.jsx
   renders a link labeled "My Reflections" that points to /counselor-dashboard
   (the legacy Crane Lake bunk-log home, not the new reflection history).
   The actual /my-reflections page is only reachable from the post-submit
   summary footer — undiscoverable from the shell.

3) Orphan routes. `/dashboards/subject-trends/:groupId` and
   `/supervisor/coverage` are declared in Router.jsx but have no inbound
   link anywhere in `frontend/src` (sidebar, hub cards, or inline). Either
   they need a discovery path or they should be removed.

4) Stale sidebar URLs. Sidebar still uses /team/dashboard and
   /wellness/dashboard. Those work via the 3.26 redirects but are
   inconsistent with the canonical /dashboards/* scheme we standardized on.

5) Missing back-link on memberships. /admin/templates and /admin/groups
   both have a "← Admin" back link (3.26). /admin/memberships does not.

Out of scope for this PR (covered by later prompts):

- Admin-page chrome alignment (sub-pages without Sidebar/Header) → 3.28
- FieldKey registry CRUD UI → 3.29
- Unused team/wellness JSON endpoints → 3.30
- Shared button/empty/loading/error primitives → 3.31

GOALS:

A. /reflect/summary?reflection= deep links work, OR are replaced by a route
   that does. After this PR every "View reflection" / "Open reflection"
   /trend-cell link lands on the right reflection.

B. /reflections/:id is a real, permission-aware read-only viewer for one
   reflection.

C. Counselor sidebar entry is honest about its destination.

D. /dashboards/subject-trends/:groupId and /supervisor/coverage are reachable
   by clicking, not just by typing the URL.

E. Sidebar leadership / wellness items point at the canonical /dashboards/*
   URLs (the redirects stay in place for old bookmarks).

F. /admin/memberships has a "← Admin" back link, matching templates/groups.

TASKS:

1. Backend: extend ReflectionSerializer with a SerializerMethodField named
   `localized_schema` that returns `_localize_schema(obj.template.schema,
   obj.language)` for instance reads. This lets the new detail page render
   without a separate /api/v1/templates/<id>/ round trip. Add the field to
   Meta.fields and ensure existing tests still pass (it's additive).

2. Frontend: new component `ReflectionDetailPage.jsx` under `frontend/src/pages/`.
     - Reads `:id` from useParams, fetches `/api/v1/reflections/<id>/`,
       and renders prompts + answers in the same visual style as
       ReflectionSummaryPage. Uses the FullShell layout (Sidebar + Header)
       — this is a real navigable page, not a one-shot post-submit screen.
     - Renders PrivacyChip from `team_visibility`.
     - On 403 / 404 from the backend, shows a friendly "You don't have
       access to this reflection or it doesn't exist." panel with a "Back to
       my reflections" link.
     - Honors `returnTo` query param if present so back-link goes where the
       linker expected.
   Add `frontend/src/pages/__tests__/ReflectionDetailPage.test.jsx` covering
   loading, success, 403, and 404 cases.

3. Frontend: route in `Router.jsx`:
     <Route path="/reflections/:id"
            element={<ProtectedRoute><ReflectionDetailPage/></ProtectedRoute>}/>
   Keep /reflect/summary unchanged (it's still used by the post-submit flow).

4. Frontend: update the three broken call sites to link to
   `/reflections/<id>` (drop the `?reflection=` form):
     - ConcernsInbox.jsx
     - SubjectDetail.jsx (both places)
     - TrendCell.jsx
   ReflectionTasksPanel.jsx already uses /reflections/<id>; with the route
   added, its CoveragePopover "View" button works without code changes.

5. Frontend: in `Sidebar.jsx`:
     a) For role === 'Counselor', rename the existing "My Reflections" item
        to "Counselor home" (more honest about /counselor-dashboard) and
        keep the target unchanged.
     b) For users in REFLECTION_FORM_ROLES (Counselor, Admin, Unit Head,
        Camper Care), add a sibling "My reflections" item beneath the
        existing "Program reflection" entry, pointing to /my-reflections.
        Pick a distinct icon (e.g. clipboard-list).
     c) Change the Leadership "Unit health (LT)" link from /team/dashboard
        to /dashboards/team.
     d) Change the Camper Care / Admin "Wellness team" link from
        /wellness/dashboard to /dashboards/wellness.

6. Frontend: discovery for orphan routes.
     a) GroupDetailPage.jsx — under the group title or actions row, add a
        "View subject trends →" link to `/dashboards/subject-trends/${id}`.
     b) ReflectionTasksPanel.jsx — in the header (variant === 'page'), add a
        secondary "Coverage →" link to /supervisor/coverage. Render the
        link only when at least one task in the fetched list has an
        `assignment_group` (i.e. the viewer is an author of some roster
        group, which is the cohort that benefits from the coverage view).
        Plain self-only reflectors don't see the link.

7. Frontend: in MembershipManagementPage.jsx, add a "← Admin" back link at
   the top of the main column, mirroring TemplateListPage / GroupListPage.

8. Tests:
     - ReflectionDetailPage.test.jsx (item 2).
     - Sidebar.test.jsx — add cases asserting:
         · /team/dashboard is no longer present
         · /wellness/dashboard is no longer present
         · /dashboards/team and /dashboards/wellness ARE present
         · "Counselor home" replaces "My Reflections" for role=Counselor
         · "My reflections" → /my-reflections appears for the relevant roles
     - GroupDetailPage already has no Vitest; add a small render test that
       the "View subject trends" link is present.
     - ReflectionTasksPanel — extend its existing test (if any) or add one
       to assert the coverage link appears only when group tasks are present.

9. Migration prompt + commit per logical slice. PR title matches
   `3_27_wayfinding_and_broken_links: ...`.

10. Run `make test-frontend`, `make test-backend`, and
    `ruff check bunk_logs/ config/` from `backend/`. All must pass.

11. Update docs/membership-role-vs-capability.md only if a fix actually
    changes a documented behavior — most of these are bug fixes; no doc
    changes expected.
```

---

## Acceptance criteria

- Clicking "Open reflection" on a concerns inbox row navigates to a
  read-only page for that reflection.
- Clicking a colored cell in the subject trend grid navigates to that
  reflection.
- Clicking "View" in a coverage popover from /tasks navigates to that
  reflection (and does NOT bounce to /dashboard).
- /my-reflections is reachable from the sidebar by all REFLECTION_FORM_ROLES
  without bookmarking.
- /dashboards/subject-trends/:groupId is reachable from
  /admin/groups/:id by clicking.
- /supervisor/coverage is reachable from /tasks by clicking, but the
  entry point appears only for users who would have any data on that page.
- Leadership and Camper Care users on the sidebar go directly to
  /dashboards/team / /dashboards/wellness (no redirect bounce).
- /admin/memberships shows a "← Admin" back link.
- No new lint warnings; all test suites green.

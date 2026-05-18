# Prompt 3.28 — Admin chrome alignment

**Wave:** 3 (Crane Lake Summer 2026 Build) — UI cleanup
**Estimated time:** 2-3 hours
**Prerequisite:** Prompt 3.27 complete.

**Use the context prompt at the top of `migration_prompts/0_0_context_prompt.md` before this session.**

---

```
The 3.26 audit flagged that /admin/* sub-pages dropped the global Sidebar
and Header: AdminHub used FullShell, but TemplateListPage, TemplateNewPage,
TemplateEditorPage, GroupListPage, and GroupDetailPage were all "bare" --
no app shell. Click any card on /admin and you lost navigation. The 3.26
PR opted not to fix this because it was a structural change touching every
admin child page; this prompt does the surgery.

CONTEXT:

We want every /admin/* page to share one shell (Sidebar + Header), with a
single source of truth so future admin pages don't drift. The dominant
pattern in the new RBAC stack is already FullShell (memberships,
all /dashboards/*); /admin children are the outliers.

The cleanest react-router-v6 expression of "shared chrome for a URL
subtree" is a **layout route** -- one parent <Route> whose `element` is
the shell, and whose children render into the layout's <Outlet/>. We add
exactly one layout component and nest the existing pages under it.

Existing access gates must be preserved verbatim:

- `/admin` itself uses AdminRoute (Admin or Super Admin).
- `/admin/templates`, `/admin/templates/new`, `/admin/templates/:id/edit`,
  `/admin/groups`, `/admin/groups/:id` use AdminRoute.
- `/admin/memberships` uses ProtectedRoute only -- the page renders its
  own org-admin "access restricted" state instead of redirecting. This
  UX must not regress.

Out of scope (later prompts):

- FieldKey registry UI (3.29)
- Unused team/wellness backend endpoints (3.30)
- Shared button/empty/loading/error primitives (3.31)

GOALS:

1. Every /admin/* list / hub / CRUD page renders inside Sidebar + Header
   without each page duplicating that chrome.
2. /admin/memberships's "you're not an org admin" branch keeps showing the
   shell (no redirect), exactly as today.
3. /admin/templates/:id/edit is a deliberate exception: it stays full-bleed.
   It's a focused editor surface with its own sticky in-page header for
   inline name editing, language switching, and save; pulling it under the
   shared shell would either double-stack stickies or shrink the working
   pane needed for the split-pane editor. Document this exception in
   Router.jsx so future contributors don't accidentally "fix" it. From
   the editor users still navigate by clicking its "Back to templates"
   arrow, exactly as today.
4. Existing per-page Vitest suites still pass without modification (they
   render the page directly with MemoryRouter, so layout changes are
   transparent).

TASKS:

1. New component `frontend/src/layouts/AdminLayout.jsx`:
     - Renders `<Sidebar/>`, `<Header/>`, a scrollable main, and an
       `<Outlet/>` from react-router-dom for the matched child route.
     - Tracks `sidebarOpen` state internally so children don't have to.
     - No max-width constraint -- each child controls its own content
       width. The layout is chrome only.
   Add a Vitest test that asserts (a) Outlet content renders, and
   (b) the mocked Sidebar + Header stubs both render (i.e. the layout
   pulls them in).

2. Update `frontend/src/Router.jsx`:
     - Import AdminLayout.
     - Replace the flat /admin* routes with a nested layout route for
       everything except the editor:

         <Route path="/admin"
                element={<ProtectedRoute><AdminLayout/></ProtectedRoute>}>
           <Route index element={<AdminRoute><AdminHub/></AdminRoute>}/>
           <Route path="memberships"
                  element={<MembershipManagementPage/>}/>
           <Route path="templates"
                  element={<AdminRoute><TemplateListPage/></AdminRoute>}/>
           <Route path="templates/new"
                  element={<AdminRoute><TemplateNewPage/></AdminRoute>}/>
           <Route path="groups"
                  element={<AdminRoute><GroupListPage/></AdminRoute>}/>
           <Route path="groups/:id"
                  element={<AdminRoute><GroupDetailPage/></AdminRoute>}/>
         </Route>

         {/* Editor stays full-bleed -- documented exception. */}
         <Route path="/admin/templates/:id/edit"
                element={<AdminRoute><TemplateEditorPage/></AdminRoute>}/>

     - Memberships intentionally lacks AdminRoute so the in-page
       "Access restricted" branch keeps rendering for non-admin
       authenticated users.

3. Strip per-page shell wrappers and outermost `min-h-screen` /
   page-backdrop classes from these files (the layout's scroll
   container owns scrolling + backdrop):
     - `frontend/src/pages/admin/AdminHub.jsx`
     - `frontend/src/pages/MembershipManagementPage.jsx`
     - `frontend/src/pages/admin/templates/TemplateListPage.jsx`
     - `frontend/src/pages/admin/templates/TemplateNewPage.jsx`
     - `frontend/src/pages/admin/groups/GroupListPage.jsx`
     - `frontend/src/pages/admin/groups/GroupDetailPage.jsx`
   Each page becomes "content only": preserve its inner max-width
   container and content, drop the outer `<div className="flex h-screen
   overflow-hidden"><Sidebar/><div...><Header/><main>...</main></div></div>`
   pattern (where present) or the `<div className="min-h-screen
   bg-gray-50 dark:bg-gray-950 ...">` page-bg wrapper (where the page
   was bare). The layout itself owns the backdrop (gray-50 / dark
   gray-900) so children render directly inside it.

   TemplateEditorPage is NOT in this list -- it stays as-is (see goal 3).

4. Tests:
     - Frontend test suite must still be 100% green; no per-page test
       changes expected.
     - Add a smoke test for AdminLayout: render it inside MemoryRouter +
       Routes/Route + a dummy outlet child, assert child renders.
     - Sidebar.test.jsx unaffected (it renders Sidebar directly).
     - Optionally add a Router-level smoke test that mounts the app at
       /admin/templates and asserts Sidebar mock rendered -- but skip if
       it requires too much auth context plumbing.

5. Update `docs/membership-role-vs-capability.md` only if any user-visible
   gate semantics changed; we do not expect any.

6. Run `make test-frontend`, `make test-backend`, and
   `ruff check bunk_logs/ config/`. All green.

7. Commit per logical slice, PR title `3_28_admin_chrome_alignment: ...`.
```

---

## Acceptance criteria

- Clicking any card on /admin lands on a child page with Sidebar + Header
  visible. Click another sidebar entry from there and navigation works
  without any "lost shell" feel.
- TemplateEditorPage still scrolls correctly and its sticky in-page
  header still pins to the top of the visible content area.
- /admin/memberships still shows the "Access restricted" panel inside
  the shell for non-admin authenticated users (no redirect).
- AdminRoute still redirects non-admins away from /admin, /admin/templates,
  /admin/groups subtrees.
- All existing tests pass; no new lint warnings.

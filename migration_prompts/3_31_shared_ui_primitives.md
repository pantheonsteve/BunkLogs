# Prompt 3.31 — Shared UI primitives for admin surfaces

**Wave:** 3 (Crane Lake Summer 2026 Build) — UI cleanup
**Estimated time:** 3-4 hours
**Prerequisite:** Prompt 3.30 complete.

**Use the context prompt at the top of `migration_prompts/0_0_context_prompt.md` before this session.**

---

```
The 3.27 audit flagged that across the new admin/dashboard pages we
keep re-writing the same five tailwind blobs: primary buttons, loading
lines, empty states, error panels, and bottom toasts. We've added five
new admin pages in 3.26-3.29 and each one copy-pastes its own version.
This is the last item on the audit list. Pull the patterns into shared
primitives so future admin pages have a single style to follow.

CONTEXT (patterns observed before writing this prompt):

- "fixed bottom-6 ... bg-gray-900 dark:bg-gray-100 ... rounded-full"
  toast: 3 places (GroupListPage, GroupDetailPage, FieldKeyListPage).
- A second toast variant ("fixed bottom-6 right-6 ... rounded-lg") in
  TemplateListPage and TemplateEditorPage. We will normalize the
  three list pages onto the centered pill; the editor's right-corner
  toast already lives inside its bespoke chrome and stays as-is to
  avoid bleeding into the editor's "exception surface" cleanup that
  3.28 deliberately left alone.
- "Loading templates…" / "Loading groups…" / "Loading…" lines: ~15
  call sites with the same `text-sm text-gray-500 dark:text-gray-400`
  treatment. Scope this PR to the admin surfaces; dashboards stay as
  they are.
- "text-center py-12 text-gray-500 dark:text-gray-400" empty states
  with optional icon + headline + action: 4 admin pages.
- "rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200
  dark:border-red-800" inline error panel: 3 admin pages.
- Primary button "bg-blue-600 text-white text-sm font-medium
  rounded-lg hover:bg-blue-700 disabled:opacity-50" appears 30+
  times across admin pages, sometimes with px-3/py-1.5 (small),
  sometimes px-4/py-2 (medium). Same shape, different sizing.

GOALS:

1. One source of truth in `frontend/src/components/ui/` for these
   five primitives.
2. Visual parity: pages look identical before/after the migration.
   Class output for the most common variants must match the strings
   we're replacing.
3. Tests for the primitives themselves; do not invent new behaviors
   that aren't already in use.
4. Migrate the 6 admin pages that already share the AdminLayout
   shell. Out of scope: dashboards, sidebar, forms shared with the
   counselor flow, and TemplateEditorPage's internal chrome.

OUT OF SCOPE (called out so we don't sprawl):

- Replacing every inline button across the app -- only the canonical
  "New X" + "Cancel" + "Delete" cases in the 6 admin pages.
- Refactoring forms or modals (we'd lose too much per-page nuance).
- Color tokens / design system overhaul. We codify the *current*
  styles, not new ones.
- Migrating TemplateEditorPage. It is the documented chrome
  exception from 3.28 and uses a different toast layout intentionally.

TASKS:

1. New components in `frontend/src/components/ui/`:

   a. `Button.jsx` -- props: variant ('primary' | 'secondary' |
      'danger'), size ('sm' | 'md', default 'md'), full standard
      <button> passthrough (onClick, disabled, type, etc.). The
      rendered className matches the existing variant strings exactly.

   b. `Toast.jsx` -- a controlled component plus a `useToast` hook.
      The hook returns `{ toast, showToast, clearToast }` with the
      same 4-second auto-hide timeout used today. Toast renders
      "fixed bottom-6 left-1/2 -translate-x-1/2 ... rounded-full".

   c. `LoadingState.jsx` -- thin wrapper: `<LoadingState>Loading
      field keys…</LoadingState>` renders the standard treatment.
      Optional `inline` prop for the in-section variant used by the
      dashboards page (we use it in MembershipManagementPage).

   d. `EmptyState.jsx` -- props: `{ icon, title, action }`. Title is
      the headline; action is an optional ReactNode (typically a
      `<Link>` or `<Button>`); icon is an optional lucide-react icon
      component (rendered at size=40 with opacity-40, matching the
      GroupListPage usage).

   e. `ErrorPanel.jsx` -- prop: `children` (the message). Renders
      the standard red-50 panel. Optional `title` prop for the
      "Access restricted" style headline.

2. Tests at `frontend/src/components/ui/__tests__/`:

   - `Button.test.jsx`: variants render the expected class fragments
     and a disabled button doesn't fire onClick.
   - `Toast.test.jsx`: visible when a message is set, hides after
     the timeout, supports `data-testid` passthrough.
   - `LoadingState.test.jsx`: renders the text and the standard
     classes.
   - `EmptyState.test.jsx`: renders title, optional icon, optional
     action.
   - `ErrorPanel.test.jsx`: renders title + body, role="alert".

3. Migrate the 6 admin pages:

   - `frontend/src/pages/admin/AdminHub.jsx`
   - `frontend/src/pages/MembershipManagementPage.jsx`
   - `frontend/src/pages/admin/templates/TemplateListPage.jsx`
   - `frontend/src/pages/admin/templates/TemplateNewPage.jsx`
   - `frontend/src/pages/admin/groups/GroupListPage.jsx`
   - `frontend/src/pages/admin/groups/GroupDetailPage.jsx`
   - `frontend/src/pages/admin/field-keys/FieldKeyListPage.jsx`

   For each:
     - Replace the toast tailwind blob with `<Toast/>` + `useToast()`.
     - Replace the loading/empty/error tailwind blobs with the new
       primitives where the shape matches.
     - Replace the canonical primary/secondary buttons with `<Button/>`.
     - DO NOT replace nuanced one-off buttons (e.g. the language
       switcher in the editor, sort-header buttons in the table).

4. Preserve all existing data-testids on rows, buttons, forms, and
   inputs so the existing test suites pass without modification. If a
   primitive needs a passthrough id/testid prop, add it.

5. Visual smoke: run the existing per-page test suites; they should
   all pass with zero changes. Run `make test-frontend` + `vite build`.

6. Backend: untouched. Skip `make test-backend` but confirm `ruff` is
   still clean since the dist file may flap.

7. Commit + PR: `3_31_shared_ui_primitives: ...`.
```

---

## Acceptance criteria

- `frontend/src/components/ui/Button.jsx`, `Toast.jsx`,
  `LoadingState.jsx`, `EmptyState.jsx`, `ErrorPanel.jsx` exist with
  unit tests.
- The 6 admin pages import and use those primitives instead of
  inline tailwind blobs for the patterns called out above.
- All existing tests pass with zero per-page test edits.
- `git grep "fixed bottom-6 left-1/2"` returns at most one match
  inside the new `Toast.jsx` component itself.
- `git grep "rounded-lg bg-red-50 dark:bg-red-950/30"` returns at
  most one match inside the new `ErrorPanel.jsx`.
- `git grep "text-center py-12 text-gray-500"` returns at most one
  match inside `EmptyState.jsx`. (Other surface variants outside
  /admin can remain.)

# Prompt 3.29 — FieldKey registry UI

**Wave:** 3 (Crane Lake Summer 2026 Build) — UI cleanup
**Estimated time:** 3-4 hours
**Prerequisite:** Prompt 3.28 complete.

**Use the context prompt at the top of `migration_prompts/0_0_context_prompt.md` before this session.**

---

```
The FieldKey registry has shipped to the backend (model, manager, viewset,
seed command, validator integration) and the AdminHub already advertises
"Field keys" as a card -- but it's marked Coming Soon because there is no
frontend. This prompt builds the registry UI.

CONTEXT:

A FieldKey is a canonical short identifier (e.g. "punctuality", "wins")
that template authors reuse across reflection templates to enable
cross-template reporting. Backend model lives at
`bunk_logs/core/models.py` (class FieldKey) and the API is
`/api/v1/field-keys/` from `bunk_logs/api/field_keys.py`. Tests live in
`bunk_logs/core/test_field_key_registry.py` and pass today.

API surface, fully implemented:

- GET    /api/v1/field-keys/[?q=<prefix>]   list (org + global, prefix search)
- POST   /api/v1/field-keys/                create (always in request.organization)
- PATCH  /api/v1/field-keys/<id>/           partial update
- DELETE /api/v1/field-keys/<id>/           delete (409 if referenced by any template)

Permissions:

- list/retrieve: any authenticated user with organization context
- create/update/delete: IsOrgAdminOrSuperuser (org admin or `is_staff`/`is_superuser`)
- Edits to global keys (organization=null): Super Admin only

Response includes:

  id, organization, key, display_name, description,
  expected_field_type, expected_dashboard_role,
  is_global (derived), created_at

Editable fields (server enforces): key, display_name, description,
expected_field_type, expected_dashboard_role.

`expected_field_type` aligns with the schema field types in
`frontend/src/components/templates/FieldList.jsx` / `LivePreview.jsx`:
text, textarea, text_list, single_choice, multiple_choice, yes_no, date,
number, section_header, instructions, rating_group, single_rating.

`expected_dashboard_role` is currently free-form on the backend but the
seed command uses: category_ratings, wins, improvements, open_concern.

GOALS:

1. /admin/field-keys lists every field key visible to the current org
   (org-scoped + global), with search and scope/type filters.
2. Super Admins can create, edit, and delete keys (including global
   keys). Org admins technically can edit their org's keys via the API,
   but the UI gates the page behind AdminRoute (Super Admin) for v1
   parity with templates and groups -- broaden later when org-admin
   tooling becomes a coherent surface.
3. Delete must surface the 409 "key is referenced" message clearly so
   the user knows to clean up templates first.
4. Card on AdminHub becomes a real link, not "Coming soon".

OUT OF SCOPE:

- Bulk import / CSV.
- Per-key usage report ("which templates reference this key?"). Backend
  has the data for this but it's not a v1 need; the 409 on delete is
  enough signal for now.
- Org-admin UI exposure. Stays AdminRoute / Super Admin only.

TASKS:

1. New page `frontend/src/pages/admin/field-keys/FieldKeyListPage.jsx`:

   - Renders inside AdminLayout (single `<main>` with max-w-6xl).
   - Breadcrumb back-link to /admin (matches templates and groups).
   - Header: title + blurb + "New field key" button.
   - Search input wired to the `?q=` API param (debounced ~250ms or
     on Enter; either is fine).
   - Scope filter chips: All / Mine / Global, applied client-side
     against `is_global`.
   - Optional secondary filter by `expected_field_type`.
   - Inline create form (collapsible) for: key, display_name,
     description, expected_field_type, expected_dashboard_role.
   - Table with columns: Key, Display name, Type, Dashboard role,
     Scope (Global/Org), Created, Actions.
   - "Edit" opens a modal (or right drawer) with the same fields as
     the create form; key is read-only on edit.
   - "Delete" prompts a confirmation, then surfaces 409 detail in a
     toast if the key is in use.
   - Toast pattern matches GroupListPage (fixed bottom-center pill).
   - Error states (network, 403) render a small panel above the table.

2. Add tests at `frontend/src/pages/admin/field-keys/__tests__/FieldKeyListPage.test.jsx`:

   - Renders list from a mocked GET response.
   - Scope filter (Global / Mine) narrows the visible rows.
   - "New field key" form posts and refreshes.
   - "Delete" handles 204 (row disappears) and 409 (toast surfaces the
     server-supplied detail and the row remains).
   - Search input drives `?q=` on the API call.

3. Update `frontend/src/Router.jsx`:

   - Add `<Route path="field-keys" element={<AdminRoute><FieldKeyListPage/></AdminRoute>}/>`
     under the existing AdminLayout parent.

4. Update `frontend/src/pages/admin/AdminHub.jsx`:

   - Replace the deferred `field-keys` card with a live one:
       to: '/admin/field-keys'
       deferred: false
       blurb: rewrite to past tense ("Canonical short keys used across
       reflection templates to enable cross-template reporting.").

5. Update `frontend/src/pages/admin/__tests__/AdminHub.test.jsx`:

   - Remove the "Coming soon" expectation for the field-keys card.
   - Assert the card now links to /admin/field-keys.

6. Optional but nice:
   - Sidebar: do NOT add a field-keys entry. The AdminHub card is the
     entry point; sidebar would crowd the admin section. The deep-link
     is also discoverable from the AdminHub card.

7. Documentation:
   - Update `docs/membership-role-vs-capability.md` only if any
     access-tier copy needs to change. We do not expect any.

8. Run `make test-frontend`, `make test-backend`, `ruff check
   bunk_logs/ config/`, and `vite build`. All green.

9. Commit + PR: `3_29_field_key_registry_ui: ...`.
```

---

## Acceptance criteria

- Navigating to /admin/field-keys as a Super Admin shows the list of
  org-visible + global keys.
- Search narrows by prefix.
- Scope filter (All / Mine / Global) filters rows in the table.
- New key flow creates a key under the current org and it appears in the
  list.
- Editing a key (display_name, description, type hint, dashboard role)
  persists.
- Deleting a key that is referenced by a template surfaces the server's
  "Key is referenced..." message and keeps the row.
- Deleting an unused key removes it from the list.
- AdminHub card links to /admin/field-keys and is no longer marked
  "Coming soon".
- All existing tests still pass; new tests for FieldKeyListPage pass.

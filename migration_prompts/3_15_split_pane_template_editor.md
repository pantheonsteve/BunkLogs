# Prompt 3.15 — Split-pane template editor (frontend)

**Wave:** 3 (Crane Lake Summer 2026 Build) — Form Builder addition
**Estimated time:** 14-18 hours (consider splitting into 3.15a, 3.15b, 3.15c if scope feels heavy)
**Prerequisite:** Prompts 3.13 and 3.14 complete.

**Use the context prompt at the top of `bunklogs-migration-prompts.md` before this session.**

---

```
Build the React template editor with field list, field inspector, and live preview. This is the largest prompt in the form-builder sequence; consider splitting into 3.15a, 3.15b, 3.15c if scope feels heavy.

CONTEXT:
The editor is at /admin/templates and /admin/templates/{id}/edit. It targets org admins and super admins. The live preview reuses the dynamic reflection renderer from prompt 3.5, ensuring the editor and runtime never drift. Refer to the mockup discussed in conversation for the visual target.

Tasks:

1. Routing and access:
   - /admin/templates — list view (table with name, role, version, status badge, response count, last edited, actions)
   - /admin/templates/new — create new (template-type chooser first: blank, or clone from existing)
   - /admin/templates/{id}/edit — split-pane editor
   - /admin/templates/{id} — read-only view (for non-admin members, optional)
   - All /admin/templates/* routes guarded: redirect to / for non-admins with a toast "Admin access required"

2. Template list view:
   - Table with sortable columns
   - Status badge: "Draft", "Published v{n}", "Archived"
   - "Clone" action on global templates (writes to current org)
   - "New template" button -> /admin/templates/new
   - Filter chips: by role, by program type, "Mine" vs "Global"
   - Empty state with link to seed templates if list is empty

3. Editor shell layout (the split-pane mockup):
   - Header: back arrow, template name (editable inline), status badge, language switcher, "Preview" button (mobile preview modal), "Save changes" button (primary)
   - Header right side also shows last-edited timestamp and unsaved-changes indicator
   - Two-column body: left pane (field list + inspector) ~58%, right pane (live preview + version warning) ~42%
   - Mobile/narrow: stack vertically with preview collapsible

4. Field list (left pane, left column):
   - Vertical list of cards, one per field, in schema order
   - Each card shows: drag handle (ti-grip-vertical), field type icon, field name (English prompt text or section label, truncated)
   - Below name: field type and (if set) dashboard_role in muted small text
   - Selected card highlighted with --color-background-info / --color-border-info
   - Drag-to-reorder using @dnd-kit/sortable (not react-dnd; dnd-kit is more accessible)
   - Cards with missing translations show an amber dot indicator
   - "Add field" dashed-border button at bottom; clicking opens a type picker popover

5. Field type picker popover:
   - Grouped by category: Text input, Choice, Structured, Meta
   - Each type shows icon + name + one-line description
   - Click adds field at end of list with sensible defaults, then auto-selects it for editing
   - Esc or click-outside dismisses

6. Field inspector (left pane, right column):
   - Header: "Edit field" with delete button (red text, confirms before deleting)
   - Inputs vary by field type. Common to all: prompt (per current language), required toggle
   - text/textarea: max_length input
   - text_list: min_items, max_items
   - rating_group: scale (number range), scale_labels (one input per scale step), categories (repeatable list with add/remove)
   - single_choice/multiple_choice: options list (key + label per language) with add/remove
   - yes_no: follow_up_on toggle, follow_up_prompt textarea
   - section_header: prompts only (no other config)
   - instructions: prompts only
   - "Advanced" disclosure: field key (with autocomplete from FieldKey registry), dashboard_role dropdown (filtered by valid values for the field type)

7. Field key autocomplete:
   - As admin types in the key field, GET /api/v1/field-keys/?q={prefix}
   - Show dropdown with matches: key + display_name + description
   - Selecting fills in the key. If admin types a new key, show "Create new key" option that opens a small modal to register it (calls POST /api/v1/field-keys/)
   - Auto-suggest a key from the English prompt when first creating a field (calls suggest_key_from_prompt server-side or implements client-side equivalent)

8. Language switcher:
   - Dropdown in header listing all languages declared in template.languages
   - Switching swaps the prompt input on the left and the rendered text on the right
   - Adding a language: small "+" next to switcher opens a modal to add a language code; saves on next "Save changes"

9. Live preview (right pane):
   - Renders the current schema using the existing ReflectionForm component from prompt 3.5
   - Wrapped in a phone-frame-ish container (~320px wide, white card on muted bg) to communicate "this is what Madrichim see"
   - Updates on every keystroke in the inspector (debounced 200ms)
   - Subsequent fields below the currently-edited one are dimmed (opacity 0.5) to keep focus
   - Submit button on the preview is disabled with tooltip "Preview only"

10. Versioning warning:
    - Below preview pane, show a warning card when the template has responses on the current version
    - Text: "{N} responses on v{n}. Saving will publish this as v{n+1}. v{n} stays available for existing data."
    - When no responses: quiet status "Editing v{n} in place."
    - On save, surface the result of the API's `created_new_version` flag in a toast: "Saved (still v{n})" or "Published as v{n+1}"

11. Save flow:
    - Button disabled when no unsaved changes
    - Validation runs client-side on save: missing required prompts (per declared language), invalid keys, missing rating_group categories
    - Server validation errors surface as field-level error pills + toast summary
    - Successful save: toast + redirect to /admin/templates (or stay if "Save and continue editing" is held — keyboard shortcut Cmd+S)

12. Tests (Vitest + Testing Library):
    - List view renders templates and handles filters
    - Editor renders all field types
    - Field reordering via drag handle (use @dnd-kit's keyboard sensor for testable reorder)
    - Inspector updates schema state correctly per field type
    - Language switcher swaps content without losing other-language data
    - Adding/removing fields updates list and preview
    - Save calls API correctly and handles versioning response
    - Permission gate prevents non-admin access to /admin/templates/*
    - Live preview reflects schema changes (debounced)
    - Validation errors display inline

13. Accessibility:
    - All inputs have associated labels
    - Drag-and-drop has keyboard alternative (dnd-kit's keyboard sensor)
    - Field list has appropriate ARIA roles (listbox/option pattern works well)
    - Color is not the only indicator (e.g. missing-translation amber dot is paired with an icon or tooltip)

Acceptance criteria:
- All routes work with permission guards
- Editor handles all 11 field types correctly
- Live preview matches what the runtime renderer produces
- Drag-to-reorder works with mouse and keyboard
- Language switcher is reliable
- Versioning warning displays correctly
- Field key autocomplete pulls from registry
- All Vitest tests pass
- npm run build succeeds
- Manual smoke test: create a new template from scratch using every field type, save it, render it via the existing reflection form route, submit a response, edit the template, verify versioning behaves correctly
- Commit history is structured (suggest: shell + routing, list view, field inspector, language switcher, live preview integration, versioning UX, tests)

Out of scope:
- Dashboard rendering (prompt 3.16)
- Bulk operations on multiple templates
- Template marketplace / sharing across orgs (Tier 3 territory)
```

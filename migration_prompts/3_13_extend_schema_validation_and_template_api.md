# Prompt 3.13 — Extend schema, validation, and template API

**Wave:** 3 (Crane Lake Summer 2026 Build) — Form Builder addition
**Estimated time:** 8-10 hours
**Prerequisite:** Prompts 1.1 through 3.8 complete (multi-tenant infrastructure, ReflectionTemplate model, dynamic reflection form from 3.5).

**Use the context prompt at the top of `bunklogs-migration-prompts.md` before this session.**

---

```
Extend the ReflectionTemplate schema to support the full v1 field type set, dashboard role tagging, and a versioning-aware CRUD API. This is the backend foundation for the form builder UI.

CONTEXT:
We're building a no-code template editor. Org admins (and super admins) will create and edit ReflectionTemplates through a UI instead of seeding from JSON files. The dynamic renderer from prompt 3.5 will be reused as a live preview, so the schema and validation logic must support every field type the editor exposes.

Tasks:

1. Extend the supported field type set. The schema validator must accept all of the following `type` values, each with their documented properties:

   Text input:
   - `text` — single line. Optional: max_length, placeholder (per language)
   - `textarea` — multi-line. Optional: min_length, max_length, placeholder (per language)
   - `text_list` — repeated single-line inputs. Required: min_items, max_items
   
   Choice:
   - `single_choice` — radio. Required: options (list of {key, labels: {lang: text}})
   - `multiple_choice` — checkboxes. Required: options. Optional: min_selections, max_selections
   - `rating_group` — N categories on a 1-M scale. Required: scale (e.g. [1, 4]), scale_labels (per language), categories (list of {key, labels: {lang: text}})
   - `single_rating` — one 1-M scale, no categories. Required: scale, scale_labels (per language)
   
   Structured:
   - `yes_no` — binary. Optional: follow_up_on (either "yes" or "no") with follow_up_prompts (per language) for a textarea revealed conditionally
   - `date` — date picker. Optional: min_date, max_date
   - `number` — numeric. Optional: min, max, step
   
   Meta (rendered but not collected as answer data):
   - `section_header` — heading and optional subheading. Required: prompts (per language)
   - `instructions` — explanatory block. Required: prompts (per language)

2. Add a `dashboard_role` property to every field. Allowed values:
   - `null` (default — no special dashboard treatment)
   - `primary_rating` — only valid on `single_rating`
   - `category_ratings` — only valid on `rating_group`
   - `wins` — only valid on `text_list`
   - `improvements` — only valid on `text_list`
   - `open_concern` — valid on `text` or `textarea`
   
   Validation rejects mismatches (e.g. `dashboard_role: primary_rating` on a `text` field).

3. Field key handling:
   - Every field requires a `key` property (string, snake_case)
   - Keys must be unique within a template
   - Reserved keys (cannot be used): `id`, `created_at`, `updated_at`, `submitted_at`, `submitted_by`, `template`, `program`, `person`, `organization`
   - Provide a helper `core/utils/keys.py` with `suggest_key_from_prompt(prompt_text: str) -> str` that slugifies English prompt text to snake_case (e.g. "List 3 things you did well" -> "list_3_things_you_did_well", truncated to 50 chars)

4. Move the schema validator out of the model into `core/validators/template_schema.py` as a standalone function `validate_template_schema(schema: dict, languages: list[str]) -> None` that raises `django.core.exceptions.ValidationError` with field-specific messages. Replace the existing inline validation in ReflectionTemplate.

5. Update the existing JSON template files in templates/reflection_templates/ to include keys and (where appropriate) dashboard_role tags. Specifically:
   - clc_2026 counselor template: tag the daily ratings as `category_ratings`
   - tbe_2026/madrich_weekly.json: tag the 5 ratings as `category_ratings`, the 3 wins as `wins`, the 2 improvements as `improvements`, the 1 question as `open_concern`
   
   Run `seed_role_template` for each updated file to confirm they still seed cleanly.

6. Build the Template CRUD API at /api/v1/templates/:
   - GET /api/v1/templates/ — list templates visible to current user (own org + global). Filters: ?role=, ?program_type=, ?is_active=, ?include_global=true|false (default true)
   - GET /api/v1/templates/{id}/ — retrieve full template with schema
   - POST /api/v1/templates/ — create new template (org-scoped automatically)
   - PATCH /api/v1/templates/{id}/ — update existing template, with versioning logic (see point 7)
   - POST /api/v1/templates/{id}/clone/ — clone a global or org template into the current org as a new draft (used for "clone-to-edit" of global templates)
   - DELETE /api/v1/templates/{id}/ — soft delete (set is_active=False); reject if any Reflections reference it

7. Versioning logic on PATCH:
   - If `Reflection.objects.filter(template=t).count() == 0`: edit in place (same row, increment nothing)
   - If responses exist: create a NEW ReflectionTemplate row with version+1, parent_template=current, copy/apply the patched schema, mark old version is_active=False if requested
   - Return: the resulting template (either the in-place edit, or the new version) plus a `created_new_version: bool` flag in the response payload
   - Add a query param `?force_new_version=true` to opt into creating a new version even when no responses exist (useful for intentional version bumps)

8. Permissions on the Template API:
   - List/retrieve: any authenticated user in the org (so the reflection form can fetch its template)
   - Create/update/delete/clone: requires Membership with role='admin' in the current org, OR User.is_superuser
   - Editing global templates (organization=null): super admin only. Org admins must clone first.
   - Add a permission class `core/permissions.py::IsOrgAdminOrSuperuser` for reuse

9. Tests (must cover):
   - Each field type validates correctly with valid input
   - Each field type rejects malformed input with clear error messages
   - dashboard_role mismatches rejected (e.g. primary_rating on text field)
   - Reserved keys rejected
   - Duplicate keys within a template rejected
   - suggest_key_from_prompt produces stable, valid keys
   - PATCH with no responses edits in place
   - PATCH with responses creates new version with parent link
   - PATCH with force_new_version=true creates new version even without responses
   - Org admin can edit own org's templates
   - Org admin cannot edit other org's templates (404, not 403, to avoid info leak)
   - Org admin cannot edit global templates directly
   - Org admin CAN clone global template to own org
   - Super admin can edit any template including global
   - Cross-org isolation holds for list endpoint
   - DELETE rejected when reflections reference the template
   - Existing JSON template files still seed cleanly

10. Update docs/reflection-template-schema.md with the full v1 field type reference, including a complete example showing every field type and the dashboard_role property.

Acceptance criteria:
- All field types validate correctly per spec
- Template CRUD API works with versioning logic
- Permissions enforced at endpoint level
- Existing seeded templates still load cleanly
- Test coverage for all listed cases, full pytest suite passes
- ruff check passes
- Schema documentation updated with examples
- Commit history is clean and atomic (suggest splitting: 1) field types + validator, 2) dashboard_role + key handling, 3) API + versioning, 4) permissions + docs)
- PR description includes a diff of the schema doc and a summary of breaking changes (none expected, but verify)

Out of scope (deferred to later prompts):
- Frontend editor UI (prompt 3.15)
- Dashboard role rendering (prompt 3.16)
- File upload, signature, conditional logic beyond yes_no follow-up
```

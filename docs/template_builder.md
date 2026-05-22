# LT Template Builder — Tier 1 (Step 7_12, Story 51)

The LT-scoped template builder lives at
`/leadership-team/templates/new` and `/leadership-team/templates/:id`
in the frontend and `/api/v1/leadership-team/templates/...` on the
backend. It deliberately exposes a narrower surface than the admin
template editor so Tier 1 customers can self-serve without admin
review.

## Tier 1 field types

| Type | UI control | Notes |
|------|-----------|-------|
| `text` | single-line input | bounded by `max_length` (default 200) |
| `textarea` | multi-line textarea | bounded by `max_length` (default 1000) |
| `text_list` | repeated text entries | `min_items` / `max_items` |
| `single_choice` | radio group | requires `options[]` |
| `multiple_choice` | checkbox group | requires `options[]` |
| `rating_group` | matrix of categories × scale | requires `categories[]` + `scale` |

Tier 2 controls (conditional / calculated / file upload / multi-page /
skip logic / approval workflow) are intentionally absent from this
builder; they remain admin-only.

## Lifecycle states

```
draft  → (publish)  → published  → (archive) → archived
   ↑           edit-in-place (PATCH) ↻             │
   └─────────  clone (always works)  ──────────────┘
```

- **draft**: PATCH edits the row in place; the version stays at the
  initial value. Anyone with `program_lead` capability who supervises a
  team in the program can view + edit it.
- **published**: PATCH a published template that already has any
  Reflections submitted under it creates a new row with
  `parent_template` set (preserving historical answers against the old
  version). Pass `?force_new_version=true` to make the new-version
  fork explicit.
- **archived**: terminal state — reflections stay readable but no new
  responses can be collected. Cannot transition back to `published`;
  use **Clone** to start a new draft from an archived template.

## Versioning rules

`ReflectionTemplate.version` increments on every new fork:

- `parent_template_id IS NULL` for the v1 row.
- Each subsequent version has `parent_template_id` = the prior version's
  pk. Walking the chain to the root gives the full version history.
- Within an `organization` + `slug`, exactly one row may be
  `is_active=True` at a time. Older versions are deactivated when a
  newer version is published.
- Reflections always store their `template_id` directly so existing
  responses keep pointing at the version that was active when they
  were submitted.

## Publishing validation

`POST .../templates/<id>/publish/` runs:

1. Every field key is unique.
2. Every required field has a prompt in every declared language
   (`languages[]`).
3. `single_choice` / `multiple_choice` have at least one option each.
4. `rating_group` has at least one category and a valid `scale`.

Failures are returned as a 409 with a `warnings` array so the builder
can render them inline next to the offending field.

## Language gap behavior

The builder surfaces a "language gap" indicator next to any field
whose prompt is empty for an enabled language. Publishing is blocked
while gaps exist for **required** fields, but optional fields with
gaps publish with a soft warning. Fallback at runtime is the first
non-empty translation, so a missing translation degrades to English
rather than rendering an empty prompt.

## Clone semantics

`POST .../templates/<id>/clone/` always produces a brand new draft:

- New `slug` (`<original-slug>-copy-<n>`).
- `version` resets to 1.
- `parent_template` is `NULL` — the clone is NOT a new version of the
  source template.
- All schema content (fields, prompts, options, categories) is
  deep-copied.

Use Clone when you want to fork a template for a different role or
program; use the PATCH-on-published flow when you want to keep the
slug and produce a new version of the same template.

## Roll-out checklist

For every new tier-1 customer:

1. Seed the global LT9 base templates via
   `python manage.py seed_role_template --status published`.
2. Confirm the customer's LT memberships have `program_lead` in their
   `capabilities` JSON.
3. Sample-publish one template per role inside an LT account.
4. Verify the team dashboards render the expected member roster.

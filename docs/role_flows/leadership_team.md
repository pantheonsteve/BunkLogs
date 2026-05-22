# Leadership Team Flow — Step 7_12 (Stories 45-53)

## Overview

The Leadership Team (LT) is the program-leadership layer above unit
heads, camper care, kitchen, specialists, etc. They supervise multiple
role-based teams, file their own biweekly reflection, and design the
reflection templates the rest of the program fills out.

The flow combines three surfaces:

1. **Dashboards** — Story 45 LT overview, Story 46 per-team, Story 47
   per-member.
2. **Self-reflection** — Story 50 LT biweekly with optional Private
   toggle.
3. **Template builder + assignments + responses** — Stories 51-53.

## Invariants

- LT viewers must have an active Membership with `role="leadership_team"`
  AND the `program_lead` capability set on the user. The shared
  `viewer_or_403(request)` helper enforces both.
- LT users see content based on **supervision**, not transitive role
  inheritance: a viewer who supervises `kitchen_staff` for program X
  may *not* see another program's kitchen team.
- Sensitive notes (Specialist / Camper Care, `is_sensitive=True`) are
  visible to LT only when the subject is inside the LT's supervised
  scope.
- The LT self-reflection's "Private" toggle maps to
  `team_visibility=supervisors_only` + `is_sensitive=True`, so the row
  is visible only to the author and admins.
- Templates have a tri-state lifecycle (`draft` / `published` /
  `archived`). Only `published` can be assigned and collect responses;
  `archived` is preserved read-only.

## Backend endpoints

| Method | Path | Story |
|--------|------|-------|
| GET | `/api/v1/leadership-team/dashboard/` | 45 |
| GET | `/api/v1/leadership-team/teams/<team_role>/` | 46 |
| GET | `/api/v1/leadership-team/teams/<team_role>/members/<id>/reflection/` | 47 |
| GET | `/api/v1/leadership-team/teams/<team_role>/aggregate/export/` | 48 |
| POST/DELETE | `/api/v1/leadership-team/reflections/<id>/mark-attention/` | 46 c5 |
| POST/PATCH | `/api/v1/leadership-team/self-reflection/[<id>/]` | 50 |
| GET/POST | `/api/v1/leadership-team/templates/` | 51 |
| GET/PATCH | `/api/v1/leadership-team/templates/<id>/` | 51 |
| POST | `/api/v1/leadership-team/templates/<id>/publish/` | 51 |
| POST | `/api/v1/leadership-team/templates/<id>/clone/` | 51 |
| POST | `/api/v1/leadership-team/templates/<id>/archive/` | 51 |
| GET/POST | `/api/v1/leadership-team/assignments/` | 52 |
| PATCH/DELETE | `/api/v1/leadership-team/assignments/<id>/` | 52 |
| GET | `/api/v1/leadership-team/templates/<id>/responses/` | 53 |
| GET | `/api/v1/leadership-team/templates/<id>/responses/export/` | 53 c7 |

## Supervision query model (Story 45 c3)

A LT viewer's "supervised teams" are the active `Supervision` rows
where:

- `supervisor_membership = <LT membership>`
- `target_type = "role_in_program"`
- `target_program = <ctx.program>`
- (no `expires_at` or `expires_at >= today`)

For each such supervision, `team_members(lt, role, today=today)`
returns active Memberships in that role for the same program.
`Supervision.objects.co_supervisors(supervision)` returns peer LTs who
also supervise that role.

## Attention conditions (Story 45 c5)

Per-team-card badges fire in order:

1. `low_completion` — `< 50%` of expected reflections submitted by the
   program's `expected_by_time` (default 18:00 local).
2. `concerning_ratings` — any answer in any submission equals the
   minimum of the scale on any scored field.
3. `sensitive_content` — any `Note` with `is_sensitive=True` from
   `specialist` / `camper_care` authors about a current team member,
   for the current period.

## Mark-for-attention (Story 46 c5)

LT viewers (and any user who can see the reflection) may flag a
reflection via `POST .../reflections/<id>/mark-attention/`. The flag is
stored on a separate `ReflectionAttentionMarker` row — it does not
mutate the reflection or notify the author. Co-supervisors see the
flag; other LTs not in the supervision chain do not.

## Template lifecycle (Story 51)

```
            ┌────────┐  publish  ┌────────────┐  archive  ┌──────────┐
   create → │  draft │ ────────▶ │  published │ ────────▶ │ archived │
            └────────┘           └────────────┘           └──────────┘
                 ▲    edit-in-place                            │
                 │    (PATCH)                                  │
                 └─────────────────────────────────────────────┘
                          clone (always allowed)
```

- `draft` → `published`: requires per-language prompts on every field
  and unique keys. The endpoint returns a 409 with `warnings` if any
  validation fails so the UI can surface them inline.
- `published` → new version: PATCHing a `published` template that has
  reflections automatically creates a new row with `parent_template`
  set. Pass `?force_new_version=true` to opt in explicitly.
- `archived` is terminal — reflections are preserved as read-only.

## Assignments + conflict resolution (Story 52)

`TemplateAssignment` is the link between a template and its audience
for a given window. Three target types:

| target_type | payload | dynamic? |
|-------------|---------|----------|
| `role` | `{role: "kitchen_staff"}` | yes — auto-includes new memberships |
| `tag_group` | `{tag: "kitchen-lead"}` | yes — based on `Membership.tags` |
| `individuals` | `{membership_ids: [...]}` | no — static snapshot |

Creating an assignment that overlaps an existing one (same template +
target identifiers) returns 409 with a `conflicts` list. The caller
must resubmit with one of:

- `replace` — ends prior assignment(s) the day before `start_date` and
  sets `replaces` FK on the new row.
- `run_both` — creates the new assignment without touching the old.
- `cancel` — backend returns 200 OK without creating anything.

Once any reflection has been submitted under an assignment, only
`end_date` is mutable (Story 52 c4/c9).

## CSV exports

Two export endpoints, both `audit.export()`-logged:

- **Team aggregate** (`/teams/<role>/aggregate/export/`): row per
  reflection for that team's active template version with translated
  text alongside the original (Story 48 c5/c6, LT13).
- **Template responses** (`/templates/<id>/responses/export/`):
  individual or aggregate row format selected by `?tab=`.

CSV columns include: period, language_of_authorship, author name,
subject name (for self-reflections this equals author), answers (one
column per scored field key), and a translated_text column for
non-English rows.

## Frontend pages

| Route | Component |
|-------|-----------|
| `/leadership-team` | `Dashboard.jsx` |
| `/leadership-team/teams/:teamRole` | `TeamDashboard.jsx` |
| `/leadership-team/teams/:teamRole/members/:membershipId` | `MemberReflection.jsx` |
| `/leadership-team/self-reflection[/...]` | `SelfReflectionPage.jsx` |
| `/leadership-team/templates` | `TemplateLibrary.jsx` |
| `/leadership-team/templates/new` and `/leadership-team/templates/:id` | `TemplateBuilder/TemplateBuilderPage.jsx` |
| `/leadership-team/templates/:id/responses` | `Responses.jsx` |

Sidebar entry is gated on `program_lead` capability. Inline English
copy is used throughout per lean-mode policy; i18n wrapping is deferred
to a separate PR.

## Deliberate non-goals

- No conditional/branching logic, calculated fields, file upload,
  multi-page templates, skip logic, translation-request workflow,
  approval workflow, or cross-org template library (all Tier 2).
- No removal of the legacy `/dashboards/team` route — deferred to
  step 7_16.
- No new chart library — the trend graph reuses the existing visual
  conventions in the codebase.

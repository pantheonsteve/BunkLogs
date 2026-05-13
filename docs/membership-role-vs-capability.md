# Membership.role vs. Membership.capability

**Status**: Accepted — 2026-05-12
**Scope**: `core.Membership`, all permission code, multi-tenant onboarding

## TL;DR

`Membership` carries **two** role-shaped fields by design:

- `role` — a 16-value `CharField` that is the customer-facing label, the
  template-routing key, and the reporting tag. **Grows over time** as new
  customers add new roles.
- `capability` — a 5-value `CharField` that is the RBAC primitive.
  **Stable**: `participant`, `supervisor`, `program_lead`, `domain_specialist`,
  `admin`.

`capability` is derived from `role` via the `ROLE_TO_CAPABILITY` mapping in
`core/models.py`, kept in sync by `Membership.save()`. Permission code branches
on `capability`. Template / label / reporting code branches on `role`.

This was an intentional two-axis design. **Do not collapse `role` down to
five values** to "clean up" the duplication — see "Why not collapse?" below.

## Why two fields?

The original `role` enum was doing three jobs simultaneously:

| Job | Notes |
|---|---|
| Permission/RBAC | "Can this user see Camper X's reflection?" — coarse-grained, must generalize across customers |
| Customer-facing label | "Junior Counselor" vs. "Specialist" — fine-grained, varies per customer |
| Template-routing key | `ReflectionTemplate.role` targets a specific role; counselor template ≠ junior-counselor template |
| Reporting/grouping tag | "How many Madrichim do we have?" |

Mixing these in one column meant permission code had to enumerate role labels
(`role__in=["camper_care", "health_center", "special_diets", "admin"]`), and
adding a new customer-specific role required touching every permission
class in the codebase. That's not multi-tenant-friendly.

The fix was to **separate the RBAC axis from the label/routing axis**:

- RBAC moves to `capability` (5 stable values).
- Labels and template routing stay on `role` (grows freely per customer).
- Reporting can use either, depending on the question.

## Decision

Add `capability` as a stored, indexed `CharField` alongside `role`. Keep them
in sync via `Membership.save()`. Surface `capability` in the admin
(read-only) and in `MembershipSerializer` (read-only). Never mutate
`capability` directly — it derives from `role`.

Permission code (starting in prompt 3.4) branches on `capability`, never on
`role`. Template / label / reporting code may still branch on `role`.

## Capability assignments

The post-3.21 mapping is the source of truth in
`backend/bunk_logs/core/models.py::ROLE_TO_CAPABILITY`. Reproduced here for
quick reference:

| capability | role(s) | visibility shape |
|---|---|---|
| `participant` | `camper`, `counselor`, `junior_counselor`, `specialist`, `general_counselor`, `kitchen_staff`, `maintenance`, `housekeeping`, `madrich` | sees own reflections + reflections in AssignmentGroups they author |
| `supervisor` | `unit_head`, `faculty`, `camper_care` | unit-scoped: `unit_head` via AssignmentGroup descendants; `faculty` / `camper_care` via `Membership.metadata.assigned_unit_slugs` |
| `program_lead` | `leadership_team` | program-wide, sliceable by `assigned_unit_slugs` |
| `domain_specialist` | `health_center`, `special_diets` | cross-unit wellness shortcut: sees every reflection whose template carries one of these roles |
| `admin` | `admin` | full org visibility |

Two important nuances:

1. **"Supervisor" means "unit-scoped".** Any role whose access boundary is "a
   set of units" maps to `supervisor`, regardless of *how* those units are
   resolved. `unit_head` resolves via the AssignmentGroup descendant walk
   (which catches dynamic per-bunk membership without slug discipline);
   `faculty` and `camper_care` resolve via `Membership.metadata.assigned_unit_slugs`
   (which is cheap and explicit but requires the importer to keep slugs in
   sync). Both produce the same effective filter in `reflections_visible_to`.
2. **`camper_care` is intentionally NOT a `domain_specialist`** even though
   the wellness dashboard groups it alongside `health_center` and
   `special_diets`. Camper-care staff are senior pastoral/clinical *leads*
   for their units, so they need read access to *every* reflection about a
   subject in those units — not just reflections that happen to be tagged
   with a wellness-role template. The wellness dashboard route gate
   (`api/wellness_dashboard.py::WELLNESS_ACCESS_ROLES`) is intentionally
   independent of `core.permissions.visibility.WELLNESS_ROLES` for exactly
   this reason: route access ≠ reflection visibility.
3. **`WELLNESS_ROLES` vs. `WELLNESS_TEMPLATE_ROLES`** (both in
   `core.permissions.visibility`). The first is the membership-side gate —
   who gets the wellness shortcut. The second is the template-side filter —
   which template flavors fall under the wellness umbrella, and is a strict
   superset of the first. `camper_care` belongs in
   `WELLNESS_TEMPLATE_ROLES` (so nurses and dietitians can see pastoral
   notes during cross-discipline care) but NOT in `WELLNESS_ROLES` (so
   camper-care staff themselves are scoped to their assigned units, not
   given a cross-program peek into every health-center / special-diets
   reflection).

## Why not collapse `role` down to 5 values?

Tempting, but it makes multi-tenancy *harder*, not easier. Concrete costs:

| Cost | What breaks |
|---|---|
| Lost label distinctions | "Counselor" and "Junior Counselor" both become `participant`; UI can't distinguish them without a second column |
| Lost template-routing precision | `ReflectionTemplate.role`, `author_role_filter`, `subject_role_filter` (see `core/models.py`) all key on the 16 values; collapsing forces every template to either accept all `participant`s or invent a new discriminator |
| Lost reporting granularity | "How many Madrichim do we have?" becomes impossible without a separate `display_label` column |
| Frontend regression | `frontend/src/pages/MembershipManagementPage.jsx` admin filter goes from 16 useful filter options to 5 too-coarse ones |
| Higher per-customer onboarding cost | Adding a new customer-specific role still requires *adding the label somewhere*; collapsing just moves the column |

In other words: the duplication between `role` and `capability` is a feature.
They're answering different questions, and pushing them into one column would
just re-create the original "this column is doing too many jobs" problem in a
new shape.

## Adding a new role to a new customer

When onboarding a customer that needs a brand-new role (e.g. `family_liaison`):

1. Add `("family_liaison", "Family Liaison")` to `Membership.ROLES` in
   `backend/bunk_logs/core/models.py`.
2. Add `"family_liaison": "supervisor"` (or whichever of the 5) to
   `ROLE_TO_CAPABILITY` in the same file.
3. Add it to the frontend `ROLE_OPTIONS` list in
   `frontend/src/pages/MembershipManagementPage.jsx` (admin filter dropdown).
4. Create or extend any `ReflectionTemplate` rows that target the new role.

Permission code does **not** change. The `ROLE_TO_CAPABILITY` coverage test in
`backend/bunk_logs/core/tests.py` (`test_mapping_covers_every_role`) will
fail in CI if you forget step 2.

## What capability does *not* solve

- **Per-tenant capability overrides.** Today the mapping is global. If
  TBE's "faculty" needed `program_lead` instead of `supervisor`, you'd
  need a tenant-scoped override (probably on `Organization.settings` or a
  new `OrganizationRoleOverride` row). Don't build this until a customer
  actually requires it.
- **Supervisor scope.** "Unit head Z supervises Unit Maple but not Unit
  Oak" is a separate concern. Today it's expressed via
  `UnitStaffAssignment` (legacy) or `Membership.metadata` (new). A
  `SupervisorScope` join table may show up in a later prompt when TBE
  Tier 2 forces it.

## Per-reflection visibility (`team_visibility`)

`Membership.capability` and `Membership.metadata.assigned_unit_slugs` decide
**who is structurally in scope** for a given reflection. The per-row
`Reflection.team_visibility` flag (step 3.22) layers on top of that to let an
author opt one specific entry out of the *peer-collaboration* path while
keeping the *supervisor* path open.

`Reflection.team_visibility` has two values, with `team` as the default:

| value | what it changes | what it does NOT change |
|---|---|---|
| `team` | default; peer authors of the same `AssignmentGroup` see the entry; the wellness shortcut (path 6) applies | n/a |
| `supervisors_only` | hides the entry from same-group peer authors; suppresses the wellness shortcut for this row | author, subject (when `subject_visible=True`), org admin, ancestor-group authors, and unit-scoped supervisors all still see it |

Implementation references:

- `Reflection.team_visibility` (`backend/bunk_logs/core/models.py`)
- `_author_group_ids_split` and the path-4 / path-6 gating in
  `backend/bunk_logs/core/permissions/visibility.py`
- The form toggle in `frontend/src/pages/ReflectionFormPage.jsx`

The flag is a per-reflection decision; there is no template-level "no, you
can't make this private" gate yet. If a template needs to forbid the toggle
(e.g. a self-reflection where privacy makes no sense), gate the UI -- the
backend will still accept either value because the data model is permissive
on purpose.

## When to revisit

Revisit this design only if one of the following becomes true:

- Permission code starts branching on `role` again (means capability granularity
  was wrong; add a 6th capability or split one).
- The 16-value `role` enum exceeds ~40 entries and roster-import code starts
  smelling like an ORM Translator (means we probably want
  `OrganizationRole` as a proper FK'd table per tenant — bigger refactor).
- Customer-facing UI starts needing localized role labels (means `role` needs
  to split into `role_key` + `role_label`, which is the rename anticipated
  in 2.4b's "open question" but deliberately deferred).

If none of these become true, leave it alone.

## References

- `backend/bunk_logs/core/models.py` — `Membership`, `CAPABILITIES`,
  `ROLE_TO_CAPABILITY`, `Membership.save()`.
- `backend/bunk_logs/core/migrations/0015_membership_capability.py`,
  `0016_backfill_membership_capability.py`,
  `0017_alter_membership_capability_nonnull.py`,
  `0018_recalibrate_camper_care_capability.py` (step 3.21).
- `backend/bunk_logs/core/tests.py::TestMembershipCapability` — coverage and
  behavior tests.
- `migration_prompts/3_4_reflection_submission_api.md` — first downstream
  consumer of `capability`.

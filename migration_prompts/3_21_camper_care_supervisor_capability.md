# Prompt 3.21 — Camper Care supervisor capability

**Wave:** 3 (Crane Lake Summer 2026 Build) — RBAC capability cleanup
**Estimated time:** 3-4 hours
**Prerequisite:** Prompt 3.20 complete (`reflections_visible_to` is the single source of truth for reflection visibility) and the `Membership.capability` axis from the WIP RBAC test bench has shipped to `main`.

**Use the context prompt at the top of `0_0_context_prompt.md` before this session.**

---

```
Reshape `Membership.capability` so Camper Care is treated as a unit-scoped supervisor, not a domain specialist. After this prompt the `domain_specialist` capability is reserved for roles whose visibility is template-tag based (Health Center, Special Diets) and `supervisor` covers any role whose visibility is scoped to a set of units (Unit Head, Camper Care, Faculty). This matches the camp ops reality: camper-care staff are senior pastoral/clinical leads for the units they're assigned to, and they need read access to every reflection about a camper or counselor in those units — not just reflections that happen to be tagged with a wellness-role template.

CONTEXT:
Background discussion captured in `docs/membership-role-vs-capability.md`. Today the mapping is:

  unit_head        -> supervisor
  faculty          -> supervisor
  leadership_team  -> program_lead
  camper_care      -> domain_specialist   <-- wrong shape for the role
  health_center    -> domain_specialist
  special_diets    -> domain_specialist

Two consequences of the current mapping that we want to fix:

  1. `core.permissions.visibility._wellness_q` grants `camper_care` visibility into every reflection whose template carries `role in {camper_care, health_center, special_diets}` — across the whole program, regardless of which units that camper-care person is assigned to. That's louder than needed and bypasses the unit scoping leadership_team / faculty already respect via `Membership.metadata.assigned_unit_slugs`.
  2. The legacy single-tenant `User.role == "Camper Care"` flow uses `UnitStaffAssignment` to enforce unit-scoped access to bunks, but the new multi-tenant stack has no equivalent for the reflection feed. After the switch, camper-care visibility in the new stack uses `Membership.metadata.assigned_unit_slugs` (the existing convention used by leadership_team), so the two stacks finally agree on the rule "camper-care sees their units, not the camp".

Health Center and Special Diets keep the `domain_specialist` capability and the wellness-template shortcut: their work is cross-unit by nature (a nurse covers everyone), and `WELLNESS_ROLES` becomes the explicit list of roles that get that shortcut.

Tasks:

1. Switch the mapping in `backend/bunk_logs/core/models.py`:

       ROLE_TO_CAPABILITY["camper_care"] = "supervisor"

   The matching coverage test in `backend/bunk_logs/core/tests.py::TestMembershipCapability::test_filter_by_capability_returns_expected_rows` needs to move `camper_care` from the `domain_specialist` set to the `supervisor` set. Leave `health_center` / `special_diets` in `domain_specialist`.

2. Write a forward-only data migration `core/migrations/0018_recalibrate_camper_care_capability.py`:

   - For every `Membership` row with `role='camper_care'`, set `capability='supervisor'`.
   - Idempotent (`update()` is fine — no signals fire that we care about) and reverse_code=noop.
   - Bake the mapping into the migration (don't import from live code) — same convention as `0016_backfill_membership_capability.py`. If a future engineer changes `ROLE_TO_CAPABILITY` again, this migration must keep producing the historically-correct state.

3. In `backend/bunk_logs/core/permissions/visibility.py`:

   - Rename `LEADERSHIP_ROLES` to `UNIT_SCOPED_SUPERVISOR_ROLES` and add `camper_care` to it. Keep `faculty` and `leadership_team`. The frozenset becomes `{"faculty", "leadership_team", "camper_care"}`.
   - Rename the helper `_leadership_q` to `_unit_scoped_supervisor_q`. Same signature, same body, just the rename — and update the call sites in `reflections_visible_to` and `has_supervisor_role`.
   - Split the original `WELLNESS_ROLES` into two sets so the wellness umbrella keeps working at the template level even as we tighten the membership-side gate:
     - `WELLNESS_ROLES` (membership-side gate) becomes `{"health_center", "special_diets"}` — drops `camper_care`. Only memberships in this set get the wellness shortcut.
     - `WELLNESS_TEMPLATE_ROLES` (template-side filter) is a new frozenset `{"camper_care", "health_center", "special_diets"}`. `_wellness_q` returns `Q(template__role__in=WELLNESS_TEMPLATE_ROLES)` so a nurse / dietitian still sees pastoral camper-care notes about subjects in their org — the wellness team collaborates across these three template flavors.
   - Update the docstring on `reflections_visible_to` so path 6 reads "Health Center / Special Diets membership -> reflections of wellness-umbrella templates (`WELLNESS_TEMPLATE_ROLES`)" and path 5 reads "Unit-scoped supervisor membership (`unit_head` is still handled via AssignmentGroup descendants; faculty / leadership_team / camper_care via assigned_unit_slugs)".

   Do NOT change the actual algorithm of either query helper; this is a labelling / set membership change only.

4. Tests in `backend/bunk_logs/core/permissions/test_visibility.py`:

   - New class `TestCamperCareScope`:
     a. `test_unrestricted_camper_care_sees_all_program_reflections` — camper_care Membership with `metadata={}`, expect the program-wide path.
     b. `test_unit_scoped_camper_care_only_sees_assigned_units` — camper_care Membership with `metadata={"assigned_unit_slugs": ["tsofim"]}`. Seed a counselor with `metadata={"unit_slug": "tsofim"}` and another with `metadata={"unit_slug": "other"}`. Reflection for each subject. Expect only the `tsofim` one.
     c. `test_camper_care_does_not_get_wellness_shortcut` — camper_care Membership, plus a reflection authored by someone else against a wellness template (`role="health_center"`). The camper-care user is not in any AssignmentGroup, has no `assigned_unit_slugs`, and does not share author/subject identity with the reflection. With current code that test would pass because of the wellness shortcut; after this prompt the unrestricted unit-scope still gives them access. To make the assertion meaningful, give the camper-care Membership `metadata={"assigned_unit_slugs": ["a"]}` and seed the reflection's subject with `metadata={"unit_slug": "b"}`. Expect count == 0 (no wellness shortcut, no unit match).
     d. `test_health_center_keeps_wellness_shortcut` — health_center Membership, wellness template with `role="health_center"`. Expect count == 1.
     e. `test_wellness_viewer_still_sees_camper_care_templates` — health_center Membership, reflection on a template with `role="camper_care"`. Expect count == 1 (the `WELLNESS_TEMPLATE_ROLES` superset contract).

   Existing wellness test (`TestWellnessScope`) uses `health_center` — leave it alone, it still validates the wellness path for the remaining roles.

5. Update `backend/bunk_logs/core/management/commands/seed_rbac_test_users.py`:

   - The `purpose` text for the `camper_care` test user currently reads `"domain_specialist (wellness); /wellness/dashboard"`. Replace with `"supervisor (unit-scoped); /wellness/dashboard + unit-scoped reflection feed"`.
   - No structural change to the data — the test bench still seeds the camper_care Membership without `metadata.assigned_unit_slugs`, which keeps the existing Playwright assertions green via the unrestricted-supervisor path. A follow-up prompt can wire `assigned_unit_slugs` into the fixture once the e2e suite has explicit unit-scope coverage.

6. Update `frontend/e2e/fixtures/users.ts`:

   - Change `camper_care.capability` from `'domain_specialist'` to `'supervisor'`. The notes string should reflect the new path: `"/wellness/dashboard route gate + unit-scoped reflection feed"`.
   - Leave `health_center.capability` as `'domain_specialist'`.

7. Update `frontend/e2e/rbac-reflection-visibility.spec.ts`:

   - The existing "camper_care sees the wellness reflection that counselor cannot" assertion still passes after this change, but for a different reason — camper_care is now the author of the seeded reflection, not its wellness-template-tag receiver. Update the file's top-level docstring so the visibility paths it describes match the post-3.21 reality.

8. `docs/membership-role-vs-capability.md`:

   - Add a "Capability assignments" section (if not already present) and document the post-3.21 mapping verbatim. Call out explicitly that "supervisor" now means "unit-scoped" and is the right capability for any role whose access is bounded by a set of units, whether that scoping comes from AssignmentGroup descendants (unit_head) or `Membership.metadata.assigned_unit_slugs` (camper_care, faculty, leadership_team).

Acceptance criteria:
- `ROLE_TO_CAPABILITY["camper_care"] == "supervisor"`.
- Migration 0018 runs on top of 0017 cleanly on a Crane Lake-shaped database. After it runs, every existing `role='camper_care'` row has `capability='supervisor'`.
- `_unit_scoped_supervisor_q` returns a Q that grants visibility to `camper_care` memberships exactly the same way it grants visibility to `leadership_team` / `faculty` memberships (driven by `metadata.assigned_unit_slugs` / `metadata.unit_slugs`, falling back to "all in program" when empty).
- `_wellness_q` returns None for a camper_care Membership in isolation (no AssignmentGroup, no `assigned_unit_slugs`). It still returns a Q for health_center / special_diets.
- New `TestCamperCareScope` cases pass; `TestWellnessScope::test_wellness_user_sees_wellness_template_reflections` still passes unchanged.
- `make test-backend` and `make test-frontend` both green.
- Playwright RBAC suite (`frontend/e2e/rbac-*.spec.ts`) still green — including the existing `camper_care sees the wellness reflection that counselor cannot` test, which now exercises the author path.

Out of scope:
- Adding `Membership.metadata.assigned_unit_slugs` to the seed_rbac_test_users fixture (separate prompt; needs Playwright coverage to land alongside).
- Pruning the legacy `User.role == "Camper Care"` flow in `bunk_logs/api/views.py`. That belongs in Wave 5 (legacy frontend migration) and would risk breaking Crane Lake's current production paths.
- Surfacing the unit-scope decision in the admin UI for editing a Membership's `metadata`. There is already a JSON field admin; richer UI is its own prompt.

Commit structure (single PR, ordered commits):
  1. feat(3_21_camper_care_supervisor_capability): switch ROLE_TO_CAPABILITY + data migration + coverage test
  2. refactor(3_21_camper_care_supervisor_capability): rename LEADERSHIP_ROLES -> UNIT_SCOPED_SUPERVISOR_ROLES; drop camper_care from WELLNESS_ROLES
  3. test(3_21_camper_care_supervisor_capability): new TestCamperCareScope cases + Playwright fixture/comment updates
  4. docs(3_21_camper_care_supervisor_capability): update membership-role-vs-capability and seed-command purpose strings
```

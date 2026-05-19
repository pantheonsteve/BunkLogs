# Step 7_1: Visibility Model Primitive

**Goal:** Implement the cross-cutting visibility model as a shared primitive used by all subsequent role-flow prompts.

**Canonical product spec:** `docs/user_stories/00_cross_cutting/visibility_model.md`

**Scope of this step:**

1. Backend: implement `content_visibility` helper module in `bunk_logs/core/` defining, for each content type, the function that returns the audience for a given content instance, given its sensitivity state. Encode the visibility table from the spec.
2. Backend: add `is_sensitive` BooleanField to `core.Note` and `core.Reflection` models where applicable per the visibility table. Default `false`. Migration: nullable + default, backwards-compatible per CLAUDE.md migration safety rules.
3. Backend: enforce visibility at the queryset level. Every content-returning ViewSet under `/api/v1/` must filter by the requesting Membership's role and the content's visibility configuration. Add `RoleVisibilityFilterBackend` to DRF settings.
4. Frontend: implement `AudienceDisclosure` component at `frontend/src/components/AudienceDisclosure.jsx`. Props: `audience` (array of role labels), `contextHint` (optional). Visual: small notice above form, neutral styling, clearly readable. i18n-ready via `react-i18next` keys.
5. Frontend: implement `SensitiveNotePlaceholder` component at `frontend/src/components/SensitiveNotePlaceholder.jsx`. Renders the count-only placeholder line ("1 sensitive note (Camper Care)") in-flow where notes would otherwise appear. Props: `count`, `gatingRole`.
6. Tests:
   1. Backend: unit tests for `content_visibility` module per visibility table.
   2. Backend: API tests verifying cross-role isolation for each content type — a Counselor's API call returns only what a Counselor should see; a UH's call returns the UH set; etc. One test per content type.
   3. Frontend: Vitest tests for `AudienceDisclosure` (renders all role labels, updates on prop change) and `SensitiveNotePlaceholder` (renders correct count and label).
7. Documentation: add brief `bunk_logs/core/VISIBILITY_MODEL.md` developer reference for module API. Cross-link to product spec.

**Out of scope (later steps):**

- Per-content-type forms that use AudienceDisclosure (those land in role-flow steps).
- The Admin override path that bypasses visibility (lands in Step 7_13).
- Audit trail of visibility decisions (lands in Step 7_4).

**Completion requirements:**

- `make test-backend` and `make test-frontend` pass.
- Commit message: `feat(7_1_visibility_model_primitive): ...`
- PR opened with `gh pr create`. PR title prefix: `7_1`. PR body includes: testing notes, risk assessment (this changes API filtering for every content endpoint — list which existing endpoints were modified), rollback plan (revert the merge; verify counselor flow still works).

**Reviewer focus areas:**

1. No client-side filtering of full payloads anywhere; all filtering server-side.
2. Visibility table in code matches the canonical product spec line by line.
3. Cross-role API isolation tests cover every content type listed in the visibility table.

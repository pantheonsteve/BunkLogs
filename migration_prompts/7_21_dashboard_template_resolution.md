# Step 7_21: Per-role dashboard refactor — TemplateAssignment-driven template resolution

**Goal:** Replace the hard-coded template resolvers in each per-role `common.py` with TemplateAssignment-aware lookups. Each role's dashboard endpoint payload contract stays IDENTICAL; only the internal template resolution changes.

**Canonical product spec:** `docs/design/form_orchestration_reframe.md` §3.4, plus decisions FA1, FA5, FA10 in `docs/user_stories/00_cross_cutting/decisions.md`.

**Depends on:** Step 7_20 (TemplateAssignment extended with `assignment_group`, `is_required`, `title`).

**Estimated time:** 4–6 hours.

**Strategic context:** This is the second of three Wave 1 prompts (FA-A=7_20, FA-B=7_21, FA-S=7_22). FA10(a) says Wave 1 ships before June 5, 2026. This is the largest of the three prompts because the refactor touches eight per-role `common.py` files. Each role gets its own commit within this prompt so a regression in one role is independently revertible.

The core insight: **the dashboard endpoint API contracts don't change**. The same JSON shape is returned. Only the internal query logic changes from `ReflectionTemplate.all_objects.filter(hard_coded_filters)` to `TemplateAssignment.all_objects.filter(viewer_context).first().template`.

**Out of scope** (deferred):

- The TemplateAssignment model extension (Step 7_20).
- Seeding TemplateAssignment rows for Summer 2026 (Step 7_22). Until FA-S ships, the refactored dashboards will return empty results because no assignments exist. That's expected; FA-B and FA-S must ship as a coordinated pair before production deploy.
- Any frontend changes.
- Changes to `ReflectionTemplate`, `Reflection`, visibility logic, or the capability/role model.

## Backend tasks

### 1. New shared helper module: `core/assignment_resolution.py`

Create a new module that all per-role dashboards consume. This keeps the resolution logic DRY across the eight role directories.

Key function signatures:

```python
def active_assignments_for(
    *,
    viewer: Person,
    organization: Organization,
    program: Program,
    as_of: date,
    target_role: str | None = None,
    target_assignment_group: AssignmentGroup | None = None,
    require_required: bool = True,
) -> list[TemplateAssignment]:
    """Return active TemplateAssignment rows for a viewer-in-context.

    Filters:
    - status='active' (or 'scheduled' that has reached start_date by as_of)
    - start_date <= as_of <= end_date (or end_date is null)
    - organization, program match
    - When target_role is set, includes assignments where target_type='role' and
      target_payload['role'] matches, OR target_type='individuals' and the
      viewer's Membership is in target_payload['membership_ids'], OR
      target_type='assignment_group' and the viewer is an author on the group
      with a matching role, OR target_type='tag_group' and viewer's
      Membership tags include the tag.
    - When require_required=True, excludes is_required=False assignments
      (used by task derivation; optional-form library passes False).
    """


def resolve_template_for(
    *,
    viewer: Person,
    organization: Organization,
    program: Program,
    as_of: date,
    role: str,
    subject_mode: str,
    cadence: str | None = None,
    assignment_group: AssignmentGroup | None = None,
) -> ReflectionTemplate | None:
    """Return the active ReflectionTemplate for a (viewer, role, subject_mode) tuple.

    This replaces the per-role hard-coded helpers. The caller provides the
    static template-shape requirements (subject_mode, optionally cadence)
    and the resolver finds the TemplateAssignment whose template matches.

    Returns None when no assignment is active. Callers MUST handle the
    None case (the existing hard-coded helpers also could return None).

    Org-shadows-global resolution preserved: if multiple assignments
    match, prefer the one whose template's organization is the caller's
    org over a global template.
    """
```

The module also exposes:

```python
def list_required_assignments_for(viewer, organization, program, as_of) -> list[TemplateAssignment]:
    """All required, active assignments where the viewer is in the resolved audience."""

def list_optional_assignments_for(viewer, organization, program, as_of) -> list[TemplateAssignment]:
    """All optional (is_required=False), active assignments where the viewer is in the resolved audience. Used by the Wave 2 'forms I can also fill out' library; not consumed by Wave 1 dashboards but the helper is here for symmetry."""
```

Place the module at `backend/bunk_logs/core/assignment_resolution.py`. It depends on `core.models` and on `api.leadership_team.assignments.resolve_members` (or factor `resolve_members` down into core to avoid the api→core import cycle if any).

**Note on `resolve_members`**: it currently lives in `api/leadership_team/assignments.py`. For this prompt, move it to `core/assignment_resolution.py` and import it from the LT module. Both surfaces should use the same resolver.

### 2. Refactor each role's `common.py`

Eight role directories to update. Each gets its own commit. Order them by ascending risk (simplest first) so regressions surface early:

1. **`api/kitchen_staff/common.py`** — single self-reflection template; smallest surface
2. **`api/madrich/common.py`** — single weekly reflection template; small surface
3. **`api/specialist/common.py`** — self-reflection + camper notes
4. **`api/counselor/common.py`** — camper reflections + self-reflection (largest surface; has `camper_reflection_template` and `counselor_self_template` helpers)
5. **`api/unit_head/common.py`** — UH self-reflection + bunk dashboards
6. **`api/camper_care/common.py`** — CC self-reflection + caseload + flags
7. **`api/leadership_team/common.py`** — LT self-reflection + team dashboards
8. **`api/admin_flow/common.py`** — admin self-reflection + oversight

For each role:

- Identify every function in `common.py` that does `ReflectionTemplate.all_objects.filter(...)` or similar direct template lookups.
- Replace its body with a call to `resolve_template_for(...)` from the new shared helper.
- Pass the static template-shape requirements (subject_mode, cadence if applicable) and the viewer-context.
- Preserve the function signature so callers in `dashboard.py`, `bunk_dashboard.py`, `camper_dashboard.py`, `team_dashboard.py`, etc., don't need to change.
- Run the role's tests (`pytest backend/bunk_logs/api/tests/test_{role}_*.py`) after each role's refactor.

Example: `api/counselor/common.py::camper_reflection_template` becomes:

```python
def camper_reflection_template(
    organization: Organization,
    program: Program,
    *,
    viewer: Person | None = None,
    bunk: AssignmentGroup | None = None,
    as_of: date | None = None,
) -> ReflectionTemplate | None:
    """Active daily camper-reflection template for a bunk roster.

    Now resolves via TemplateAssignment. The bunk parameter is preferred;
    if omitted, the resolver falls back to a program-wide assignment.
    """
    from bunk_logs.core.assignment_resolution import resolve_template_for
    from bunk_logs.core.time_utils import get_today

    if viewer is None or as_of is None:
        # Backward-compat: callers that didn't pass viewer/as_of get the
        # program-wide template via a synthetic resolution. This branch
        # exists because some test fixtures and management commands call
        # this helper without a viewer context. New code should pass them.
        as_of = as_of or get_today(organization)

    return resolve_template_for(
        viewer=viewer,
        organization=organization,
        program=program,
        as_of=as_of,
        role="counselor",
        subject_mode="single_subject",
        cadence="daily",
        assignment_group=bunk,
    )
```

Callers in `counselor/dashboard.py` and elsewhere need to pass the new keyword args. The viewer context is already available there via `viewer_or_403`.

### 3. Backward-compatibility consideration

The legacy `ReflectionTemplate` direct queries also appear in:

- Management commands (`seed_role_template`, `onboard_clc_summer_2026`).
- Test fixtures.

These should continue to work because:

- The refactor only changes how dashboards *resolve* templates; templates themselves are still queryable directly via the ORM.
- Management commands that seed templates do not need refactoring in this prompt.

If any management command currently does "find the daily camper template" to inject test data, it should be updated to either (a) call the refactored helper with a mock viewer, or (b) use direct ORM queries since management commands run outside the dashboard request context.

### 4. Tests

For each role, update existing dashboard tests so they:

- Create a TemplateAssignment row pointing at the test template (this is the new requirement; before the refactor, just creating the template was enough).
- Assert the dashboard payload includes the expected template-derived data (same assertions as before).
- Add a new test: when no TemplateAssignment exists for a role, the dashboard returns the empty-state shape (no tasks, but no 500 either).

The existing tests will FAIL after the refactor until they're updated to create assignment rows. This is expected and is the signal that the refactor is doing its job.

### 5. Documentation

Add a new section to `docs/data-model.md` titled "Template resolution after Step 7_21" explaining:

- Dashboards no longer hard-code template lookups.
- Template resolution flows through `core.assignment_resolution.resolve_template_for`.
- Adding a new role's dashboard means writing a new `common.py` that calls the same resolver.

### 6. Acceptance criteria for this prompt

- `core/assignment_resolution.py` exists with the documented signatures.
- All eight per-role `common.py` files use the resolver instead of direct template queries.
- Every dashboard endpoint's payload contract is unchanged (verified by existing dashboard contract tests).
- New tests verify the empty-state behavior when no assignment exists.
- `pytest` passes (after test fixtures are updated to create assignment rows).
- `ruff check` clean.
- Frontend tests still pass (no frontend changes; this is a backend-only refactor).

### 7. Commit / PR conventions

Per the existing migration prompts pattern:

- Branch: `step/7_21_dashboard_template_resolution`
- One commit per role refactored, in the order specified in task 2: `refactor(7_21_kitchen_staff): consume TemplateAssignment for kitchen self-reflection`, `refactor(7_21_madrich): ...`, etc.
- Plus a leading commit `feat(7_21_assignment_resolution): add core.assignment_resolution shared resolver` for the new module.
- Plus a trailing commit `test(7_21): update fixtures to create TemplateAssignment rows` if test updates span roles.
- Open a single PR with `gh pr create`; title `7_21: Per-role dashboard refactor — TemplateAssignment-driven template resolution`. Don't merge yourself.
- PR description includes:
  - **What**: summary of changes, including the list of 8 roles refactored.
  - **Why**: link to `docs/design/form_orchestration_reframe.md` §3.4 and decision FA10.
  - **Testing**: dashboard contract tests still pass; new empty-state tests added.
  - **Risk assessment**: this is the riskiest of the Wave 1 prompts. A bug in resolution silently empties a dashboard. Mitigation: per-role commits so we can revert individually.
  - **Rollback plan**: if a single role's resolver breaks, revert that role's commit and re-deploy. The shared resolver module can stay; it has no consumers if no role is refactored.

## What this prompt does NOT do

- Does NOT modify TemplateAssignment itself (that's 7_20).
- Does NOT create any TemplateAssignment rows for production data (that's 7_22).
- Does NOT change `ReflectionTemplate`, `Reflection`, or any other model.
- Does NOT add frontend UX.
- Does NOT change visibility / permission logic.

## Critical warning

Until Step 7_22 (seeding) ships in the same release window, the refactored dashboards will return empty results in production. **FA-B (7_21) and FA-S (7_22) must be deployed to production within the same release cycle**, or staging-only until both are ready. Do NOT merge 7_21 to production without 7_22 ready to follow immediately.

Suggested production deploy sequence (in the same maintenance window):

1. Merge 7_20.
2. Merge 7_21.
3. Merge 7_22.
4. Run the FA-S seeding command.
5. Smoke test as Alyson.

If 7_22 is not ready when 7_21 lands, 7_21 stays on staging only.

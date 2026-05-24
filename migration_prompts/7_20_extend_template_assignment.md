# Step 7_20: Extend TemplateAssignment with assignment_group, is_required, and title

**Goal:** Extend the existing `TemplateAssignment` model (in `core.models`) and its CRUD API (in `api/leadership_team/assignments.py`) to support per-AssignmentGroup targeting, the required/optional flag, and a per-assignment display title. Widen the API permission gate to include `admin` capability alongside `program_lead`.

**Canonical product spec:** `docs/design/form_orchestration_reframe.md` §3, plus decisions FA1, FA4 (no impact this prompt), FA5, FA7 in `docs/user_stories/00_cross_cutting/decisions.md`.

**Depends on:** Step 7_12 (LT template builder + TemplateAssignment shipped).

**Estimated time:** 3–5 hours.

**Strategic context:** This is the first of three Wave 1 prompts (FA-A, FA-B, FA-S) implementing the form-orchestration reframe per FA10(a) decision. Wave 1 MUST ship before June 5, 2026 because the Crane Lake Summer 2026 staff onboarding flows depend on the new assignment-driven task derivation. This prompt is the model-and-API extension; FA-B refactors the per-role dashboards to consume the new shape; FA-S seeds the production assignments.

**Out of scope** (deferred to other prompts):

- Any frontend changes (FA-E in Wave 2 ships the "Assign form" dialog in the builder).
- Per-role dashboard refactors (FA-B / Step 7_21).
- Seeding TemplateAssignment rows for Summer 2026 (FA-S / Step 7_22).
- Cadence semantics expansion beyond what `ReflectionTemplate.CADENCES` already defines.

## Backend tasks

### 1. Migrations and model fields

Add three new fields to `core.models.TemplateAssignment`:

```python
assignment_group = models.ForeignKey(
    "core.AssignmentGroup",
    null=True,
    blank=True,
    on_delete=models.CASCADE,
    related_name="template_assignments",
    help_text=(
        "When target_type='assignment_group', the group this assignment "
        "targets. Memberships resolve to those whose role matches the "
        "template's author_role_filter AND who hold an active "
        "AssignmentGroupMembership in this group with role_in_group='author'."
    ),
)
is_required = models.BooleanField(
    default=True,
    help_text=(
        "When True, the assignment produces tasks in the per-role dashboards. "
        "When False, it appears in the role's optional forms library and does "
        "NOT affect the 'all set' state (decision FA5)."
    ),
)
title = models.CharField(
    max_length=255,
    blank=True,
    default="",
    help_text=(
        "Per-assignment display title for dashboard widgets. "
        "Falls back to template.name when blank."
    ),
)
```

Add a new value to the `TargetType` enum:

```python
class TargetType(models.TextChoices):
    ROLE = "role", "Role (dynamic)"
    INDIVIDUALS = "individuals", "Individual memberships (static)"
    TAG_GROUP = "tag_group", "Tag group (dynamic)"
    ASSIGNMENT_GROUP = "assignment_group", "Assignment group (dynamic)"  # NEW
```

Migration considerations:

- Standard Django additive migration. All three fields are nullable / have defaults, so existing rows (if any in dev/staging) remain valid.
- No data migration needed in this prompt; FA-S handles row creation.
- Update the model docstring to reflect the new target type.

### 2. Extend `resolve_members(assignment, as_of)`

In `api/leadership_team/assignments.py`, add the `assignment_group` branch to `resolve_members`:

```python
if target_type == TemplateAssignment.TargetType.ASSIGNMENT_GROUP:
    group_id = assignment.assignment_group_id
    if not group_id:
        return base.none()
    author_roles = assignment.template.author_role_filter or []
    if not author_roles:
        return base.none()
    author_person_ids = AssignmentGroupMembership.objects.filter(
        group_id=group_id,
        role_in_group="author",
        is_active=True,
    ).values_list("person_id", flat=True)
    return base.filter(person_id__in=author_person_ids, role__in=author_roles)
```

Edge cases to test:

- Template has empty `author_role_filter` → return `base.none()` (no resolution possible).
- AssignmentGroup is inactive → still resolve to its memberships (the assignment's own date window handles activation).
- AssignmentGroupMembership has `end_date` in the past → excluded by the `is_active=True` filter on AGM (consistent with how other role-scoped queries work in the codebase).
- Cross-organization safety: the existing `base = Membership.all_objects.filter(program=assignment.program, is_active=True)` already constrains to the assignment's program, which is org-scoped.

### 3. Update API validation in `_validate_target`

In `api/leadership_team/assignments.py`, extend `_validate_target` to handle the new target type:

```python
VALID_TARGET_TYPES = ("role", "individuals", "tag_group", "assignment_group")

def _validate_target(target_type: str, target_payload: dict) -> None:
    # ... existing validation ...
    if target_type == "assignment_group":
        # assignment_group_id comes via the dedicated FK column on the
        # request body, not target_payload. This is a deliberate break
        # from the existing target_payload convention because FK
        # constraints are cleaner than JSON-encoded IDs.
        # Validation happens in the POST handler (see task 4).
        pass
```

### 4. Update the POST handler

In `LeadershipTeamAssignmentListCreateView.post`, accept and validate the new fields:

```python
# Existing: template_id, target_type, target_payload, start_date, end_date,
# cadence_override, conflict_resolution.

# New:
assignment_group_id = payload.get("assignment_group")
is_required = payload.get("is_required", True)  # default True per spec
title = (payload.get("title") or "").strip()

if target_type == "assignment_group":
    if not assignment_group_id:
        raise ValidationError(
            "assignment_group is required when target_type='assignment_group'.",
        )
    try:
        group = AssignmentGroup.objects.get(
            pk=assignment_group_id, program=ctx.program,
        )
    except AssignmentGroup.DoesNotExist as exc:
        raise NotFound("AssignmentGroup not found.") from exc
elif assignment_group_id:
    raise ValidationError(
        "assignment_group can only be set when target_type='assignment_group'.",
    )
else:
    group = None
```

When creating the row, pass `assignment_group=group`, `is_required=is_required`, `title=title`.

### 5. Update the PATCH handler

Extend the editable-when-no-responses set to include the new fields:

```python
# Existing: end_date editable always; cadence_override and target_payload
# editable only when no responses exist.

# New (when no responses exist):
# - is_required: editable
# - title: editable
# - assignment_group: NOT editable post-creation (would require a new
#   assignment row; use the conflict_resolution='replace' flow instead)
```

### 6. Update `_serialize`

Add the new fields to the serialized representation:

```python
return {
    # ... existing fields ...
    "assignment_group": assignment.assignment_group_id,
    "is_required": assignment.is_required,
    "title": assignment.title or "",
    "display_title": assignment.title or (assignment.template.name if assignment.template_id else ""),
}
```

The `display_title` convenience field makes downstream consumers (FA-B dashboard refactors) simpler.

### 7. Widen the permission gate (FA7)

The existing endpoints use `viewer_or_403` from `api/leadership_team/common.py`, which restricts to `program_lead` capability. Per decision FA7, widen this to accept `program_lead OR admin` for the assignments endpoints specifically.

Option A (preferred): add a new helper `assignment_viewer_or_403` in `api/leadership_team/common.py` that accepts both capabilities, and use it from `assignments.py`. Leaves the existing helper untouched for the rest of the LT endpoints.

Option B: parameterize `viewer_or_403` with allowed capabilities. More invasive; only do this if the existing helper has a single caller (it doesn't, so option A is safer).

Test: an Admin membership can POST/PATCH/DELETE assignments; a UH membership receives 403.

### 8. Update conflict detection for the new target type

In `_find_conflicts`, add the `assignment_group` branch. Two assignments conflict iff they share template + target_type + assignment_group AND their date windows overlap:

```python
if target_type == "assignment_group":
    qs = qs.filter(assignment_group_id=assignment_group_id)
```

The existing date-overlap logic at the bottom of `_find_conflicts` already handles the date intersection generically.

### 9. Documentation

Update `docs/data-model.md` to mention the new fields on TemplateAssignment. One paragraph; reference back to `docs/design/form_orchestration_reframe.md` §3 for the design rationale.

### 10. Tests

In `backend/bunk_logs/api/tests/test_leadership_team_assignments.py` (or wherever existing TemplateAssignment tests live; if no test file exists, create one):

1. **Model tests**: create a TemplateAssignment with `target_type='assignment_group'`, `assignment_group=<bunk>`, `is_required=False`, `title='Daily Bunk Log'`. Verify all fields persist.
2. **`resolve_members` tests**:
   - Resolve an assignment_group assignment to its expected counselors.
   - Resolve when template has empty `author_role_filter` → returns empty queryset.
   - Resolve when AssignmentGroup has no active author AGMs → returns empty.
   - Resolve a `role` assignment (existing behavior) → still works, regression check.
3. **API tests** (using DRF APIClient):
   - POST a new assignment_group assignment as an LT user → 201.
   - POST as an Admin user → 201 (FA7 widening verified).
   - POST as a UH user → 403.
   - POST without assignment_group when target_type='assignment_group' → 400.
   - POST with assignment_group when target_type='role' → 400.
   - PATCH the title and is_required of a created assignment → 200.
   - PATCH the assignment_group → 400 (immutable post-creation; use replace flow).
   - GET list shows new fields in payload.
   - Conflict detection: create two overlapping assignments on the same bunk → 409 requiring conflict_resolution.

### 11. Acceptance criteria for this prompt

- All three new fields land on `TemplateAssignment` and migrate cleanly.
- `resolve_members` correctly handles all four target types.
- API endpoints accept, validate, and serialize the new fields.
- Admin capability can use the assignment endpoints (FA7 satisfied).
- All existing tests still pass.
- New tests cover the cases enumerated in task 10.
- `pytest`, `ruff check` clean.
- Frontend tests unaffected (no frontend changes).

### 12. Commit / PR conventions

Per the existing migration prompts pattern:

- Branch: `step/7_20_extend_template_assignment`
- Commit messages use the step ID scope: `feat(7_20_extend_template_assignment): add assignment_group FK and is_required/title fields`
- Open a PR with `gh pr create`; title `7_20: Extend TemplateAssignment with assignment_group, is_required, title`. Don't merge yourself.
- PR description includes:
  - **What**: summary of changes.
  - **Why**: link to `docs/design/form_orchestration_reframe.md` and decisions FA1/FA5/FA7.
  - **Testing**: list of new tests; result of running `pytest` and `ruff check`.
  - **Risk assessment**: this is an additive migration; rollback is a revert of the model migration plus the API changes.
  - **Rollback plan**: revert the merge commit; the migration is backward-compatible because all new fields are nullable / have defaults.

## What this prompt does NOT do

- Does NOT modify any per-role dashboard endpoint (that's FA-B / Step 7_21).
- Does NOT create any TemplateAssignment rows (that's FA-S / Step 7_22).
- Does NOT add frontend UX (that's FA-E in Wave 2).
- Does NOT change `ReflectionTemplate`, `Reflection`, `Membership`, or any visibility logic.

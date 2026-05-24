# Step 7_22: Seed TemplateAssignments for Crane Lake Summer 2026

**Goal:** Create the TemplateAssignment rows that Crane Lake Summer 2026 needs so the refactored dashboards (Step 7_21) produce the same tasks as the pre-refactor implicit logic. Ship via an idempotent management command.

**Canonical product spec:** `docs/design/form_orchestration_reframe.md` §3.5, plus decisions FA1, FA10 in `docs/user_stories/00_cross_cutting/decisions.md`.

**Depends on:** Step 7_20 (TemplateAssignment extended), Step 7_21 (per-role dashboards refactored).

**Estimated time:** 2–4 hours.

**Strategic context:** This is the third and final Wave 1 prompt (FA-A=7_20, FA-B=7_21, FA-S=7_22). Without this prompt, the refactored dashboards from 7_21 will return empty results — there are no TemplateAssignment rows for them to consume. This prompt makes the post-refactor dashboards produce the same task list as pre-refactor, with no functional change visible to end users. It's the cutover that makes FA10(a) viable.

**Out of scope** (deferred):

- Any model changes (those land in 7_20).
- Any dashboard refactor (that's 7_21).
- Any frontend changes.
- TemplateAssignment rows for TBE Religious School (covered separately when TBE onboarding runs in late August).
- Optional (`is_required=False`) assignments — Wave 1 ships required tasks only; the optional-form library is Wave 2 (FA-G).

## Backend tasks

### 1. New management command: `seed_summer_2026_assignments`

Place at `backend/bunk_logs/core/management/commands/seed_summer_2026_assignments.py`.

Command signature:

```bash
python manage.py seed_summer_2026_assignments \
    --org-slug crane-lake-camp \
    --program-slug summer-2026 \
    [--dry-run] \
    [--actor-username <admin-user>]
```

Behavior:

- Idempotent: re-running with the same args produces the same set of assignments (no duplicates, no orphans).
- `--dry-run`: prints what would be created/updated, makes no DB changes.
- `--actor-username`: optional; resolves to a User whose Membership becomes the `created_by` on each row. Defaults to a synthetic platform actor when not provided.
- Wraps all writes in a single transaction so a partial failure leaves no partial seed.

### 2. The canonical assignment list for Summer 2026

Per the existing implicit logic that the per-role dashboards used to derive tasks. Enumerate every template-and-context combination here and create one TemplateAssignment row per entry.

| Role | Template (by slug, org-shadow-aware) | target_type | assignment_group / payload | cadence | is_required | title |
|---|---|---|---|---|---|---|
| counselor | `counselor-camper-log-{daily}` (single_subject) | assignment_group | each active Bunk in the program | daily | true | "Daily Camper Bunk Log" |
| counselor | `counselor-self-reflection-{daily}` (self) | role | `{role: 'counselor'}` | daily | true | "Counselor Daily Self-Reflection" |
| junior_counselor | `junior-counselor-self-reflection-{daily}` (self) | role | `{role: 'junior_counselor'}` | daily | true | "JC Daily Self-Reflection" |
| general_counselor | `general-counselor-self-reflection-{daily}` (self) | role | `{role: 'general_counselor'}` | daily | true | "GC Daily Self-Reflection" |
| specialist | `specialist-self-reflection-{daily}` (self) | role | `{role: 'specialist'}` | daily | true | "Specialist Daily Self-Reflection" |
| unit_head | `unit-head-self-reflection-{daily}` (self) | role | `{role: 'unit_head'}` | daily | true | "Unit Head Daily Self-Reflection" |
| kitchen_staff | `kitchen-staff-self-reflection-{daily}` (self) | role | `{role: 'kitchen_staff'}` | daily | true | "Kitchen Daily Self-Reflection" |
| maintenance | `maintenance-self-reflection-{daily}` (self) | role | `{role: 'maintenance'}` | daily | true | "Maintenance Daily Self-Reflection" |
| housekeeping | `housekeeping-self-reflection-{daily}` (self) | role | `{role: 'housekeeping'}` | daily | true | "Housekeeping Daily Self-Reflection" |
| camper_care | `camper-care-self-reflection-{daily}` (self) | role | `{role: 'camper_care'}` | daily | true | "Camper Care Daily Self-Reflection" |
| health_center | `health-center-self-reflection-{daily}` (self) | role | `{role: 'health_center'}` | daily | true | "Health Center Daily Self-Reflection" |
| special_diets | `special-diets-self-reflection-{daily}` (self) | role | `{role: 'special_diets'}` | daily | true | "Special Diets Daily Self-Reflection" |
| leadership_team | `leadership-team-self-reflection-{daily}` (self) | role | `{role: 'leadership_team'}` | daily | true | "LT Daily Self-Reflection" |
| admin | `admin-self-reflection-{daily}` (self) | role | `{role: 'admin'}` | daily | true | "Admin Daily Self-Reflection" |

**This table is a starting point.** During implementation:

1. Read each per-role `common.py` (post-7_21 refactor) and confirm which templates each role's dashboard expects to resolve.
2. Check `docs/clc-2026-templates.md` and the existing seeded templates via `python manage.py shell` → `ReflectionTemplate.all_objects.filter(...)` to confirm the actual template slugs.
3. Adjust the table above to match reality. The structure (one assignment per role-and-template combination) is correct; only the slugs and titles need verification.

For the counselor camper-log entry specifically: the command should enumerate all `AssignmentGroup` rows in the Summer 2026 program where `group_type='bunk'` and `is_active=True`, then create one TemplateAssignment per bunk. This is the only entry that produces multiple assignment rows; the rest produce one row each.

### 3. Implementation outline

```python
class Command(BaseCommand):
    help = "Seed TemplateAssignment rows for a Summer 2026 program."

    def add_arguments(self, parser):
        parser.add_argument("--org-slug", required=True)
        parser.add_argument("--program-slug", required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--actor-username")

    def handle(self, *args, **opts):
        org = Organization.objects.get(slug=opts["org_slug"])
        program = Program.objects.get(organization=org, slug=opts["program_slug"])
        actor = self._resolve_actor(org, opts.get("actor_username"))
        plan = self._build_plan(org, program)

        if opts["dry_run"]:
            self._print_plan(plan)
            return

        with transaction.atomic():
            for entry in plan:
                self._upsert_assignment(entry, actor=actor)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(plan)} assignments."))

    def _build_plan(self, org, program) -> list[dict]:
        # ... assemble the table above into a list of dicts ...
        # Each dict has: template, target_type, target_payload,
        # assignment_group, cadence, is_required, title, start_date.

    def _upsert_assignment(self, entry, *, actor):
        # Find an active TemplateAssignment matching (program, template,
        # target_type, target identifiers). Update title/is_required/etc. if
        # found; create if not.
```

The idempotency key is `(program, template, target_type, target_identifiers)` where `target_identifiers` is the role string, the assignment_group id, the membership_ids list, or the tag string depending on target_type.

### 4. Date window

- `start_date`: program's `start_date` (Crane Lake Summer 2026 starts June 5, 2026).
- `end_date`: program's `end_date` (or null for open-ended).

### 5. Pre-flight checks before writes

The command should refuse to run if:

- The organization or program doesn't exist (raise CommandError).
- Any expected template is missing in the program's templates (warn, list missing, exit non-zero unless `--force` is passed).
- An assignment with the same key already exists in a status that isn't `active` or `scheduled` (e.g. `ended` or `cancelled`) — log a warning and skip rather than reactivate. The intent is "seed fresh assignments," not "resurrect old ones."

### 6. Cross-program safety

Re-running the command against a different `--program-slug` must not affect Summer 2026 assignments. The idempotency key includes `program`, so this is automatic, but include an explicit test.

### 7. Tests

Create `backend/bunk_logs/core/management/tests/test_seed_summer_2026_assignments.py`:

1. **Happy path**: seed against a fixture with all expected templates → expected number of assignments created.
2. **Idempotency**: run twice → same row count, no duplicates.
3. **Dry run**: produces no DB writes.
4. **Missing template**: run against a fixture missing one template → exit with helpful error.
5. **Bunk enumeration**: fixture with 3 bunks → 3 counselor-camper-log assignments created (one per bunk).
6. **Cross-program isolation**: seed Summer 2026, then create a Summer 2027 program in the same org, run for Summer 2027 → Summer 2026 assignments untouched.
7. **Cross-org isolation**: seed Crane Lake, then run for a different org → Crane Lake assignments untouched.

### 8. Documentation

Add a new section to `docs/clc-summer-2026-launch.md` titled "Seeding TemplateAssignments (Step 7_22)" with:

- The command invocation.
- The list of assignments it creates.
- The expected verification step (run the command against staging, log into staging as Alyson, confirm dashboards populate correctly).
- The production deploy sequence (per Step 7_21's critical warning: 7_20 → 7_21 → 7_22 → run seeding command, all in one maintenance window).

### 9. Acceptance criteria for this prompt

- Command exists and is idempotent.
- All assignments listed in task 2 are created when run against the Crane Lake Summer 2026 fixtures.
- Per-role dashboards (post-7_21 refactor) return non-empty results after seeding.
- All tests in task 7 pass.
- `pytest`, `ruff check` clean.
- Frontend tests unaffected.
- Smoke test on staging: a seeded counselor sees their daily camper bunk log task and their daily self-reflection task; a seeded UH sees their daily UH self-reflection task; etc.

### 10. Commit / PR conventions

Per the existing migration prompts pattern:

- Branch: `step/7_22_seed_summer_2026_assignments`
- Commit: `feat(7_22_seed_summer_2026_assignments): seed TemplateAssignment rows for Crane Lake Summer 2026`
- Open a PR with `gh pr create`; title `7_22: Seed TemplateAssignments for Crane Lake Summer 2026`. Don't merge yourself.
- PR description includes:
  - **What**: summary of the command and the assignment list it produces.
  - **Why**: link to `docs/design/form_orchestration_reframe.md` and decision FA10.
  - **Testing**: list of tests; dry-run output from staging.
  - **Risk assessment**: this is the cutover. If template slugs in the seed table don't match production templates, dashboards will be empty after deploy. Mitigation: dry-run against staging-with-prod-data-snapshot before deploy.
  - **Rollback plan**: TemplateAssignment rows can be marked `status='cancelled'` and the pre-7_21 dashboards code can be restored to fall back to direct template queries. But the cleaner rollback is "revert 7_21 and 7_22 together" — the same maintenance window strategy applies in reverse.

## What this prompt does NOT do

- Does NOT modify any model or dashboard code.
- Does NOT add frontend UX.
- Does NOT seed TBE assignments (covered in TBE onboarding, post-summer).
- Does NOT seed any `is_required=False` (optional) assignments.

## Final Wave 1 sequence

Once 7_22 is merged:

1. Deploy 7_20 + 7_21 + 7_22 to production in a single maintenance window (suggested: a weekend evening late May / very early June).
2. Run the seeding command in production: `python manage.py seed_summer_2026_assignments --org-slug crane-lake-camp --program-slug summer-2026`.
3. Smoke test as Alyson immediately after.
4. Monitor Datadog APM for unexpected dashboard errors over the next 24 hours.
5. By June 3 at the latest, declare Wave 1 done or trigger the FA10(b) escape-hatch rollback.

After Wave 1 ships and stabilizes:

- Re-verify the existing canonical user stories against the new substrate (per the design doc §7 acceptance criteria).
- Plan Notes module deploy (7_19) for late June.
- Begin Wave 2 work in July (FA-E, FA-P, FA-F, FA-G, FA-H, FA-I).

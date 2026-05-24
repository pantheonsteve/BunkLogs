# Step 7_22: Seed TemplateAssignments for Crane Lake Summer 2026

**Goal:** Create the TemplateAssignment rows that Crane Lake Summer 2026 needs so the refactored dashboards (Step 7_21) produce tasks for every role from June 5 forward. Ship via an idempotent management command.

**Canonical product spec:** `docs/design/form_orchestration_reframe.md` §3.5, plus decisions FA1, FA10 in `docs/user_stories/00_cross_cutting/decisions.md`.

**Depends on:** Step 7_20 (TemplateAssignment extended) ✅, Step 7_21 (per-role dashboards refactored) ✅.

**Estimated time:** 2–4 hours.

**Strategic context:** Final Wave 1 prompt. Without it, the refactored dashboards from 7_21 return empty results in production. This prompt is the cutover that makes FA10(a) viable.

**Out of scope** (deferred):

- Any model changes (those landed in 7_20).
- Any dashboard refactor (that's 7_21).
- Any frontend changes.
- TemplateAssignment rows for TBE Religious School (covered separately during TBE onboarding, post-summer).
- Optional (`is_required=False`) assignments — Wave 1 ships required tasks only; the optional-form library is Wave 2 (FA-G).
- Bunk-specific (per-AssignmentGroup) assignments for the counselor camper-log — the counselor template uses `subject_mode='single_subject'` and is resolved per-bunk dynamically by `resolve_template_for(..., assignment_group=bunk)` falling back to program-wide role assignments. Wave 1 ships one program-wide role assignment per role; per-bunk targeting can be added later if/when LT wants per-bunk overrides.

---

## Pre-flight inventory (verified 2026-05-24)

The Crane Lake Summer 2026 program seeds **12 templates** via `seed_role_template`. The canonical authority for which templates exist and which role they target is `bunk_logs/core/management/commands/onboard_clc_summer_2026.py::TEMPLATE_MANIFEST`. The seeding command reads each JSON's `name`, `slug`, `cadence`, and `schema` from disk and writes `role` and `program_type` from CLI flags at seed time.

**Confirmed inventory:**

| File | Role (seeded at template) | Slug | Cadence |
|---|---|---|---|
| `counselor.json` | counselor | `clc-2026-counselor-daily` | daily |
| `junior_counselor.json` | junior_counselor | `clc-2026-junior-counselor-daily` | daily |
| `general_counselor.json` | general_counselor | `clc-2026-general-counselor-daily` | daily |
| `specialist.json` | specialist | `clc-2026-specialist-daily` | daily |
| `unit_head.json` | unit_head | `clc-2026-unit-head-daily` | daily |
| `leadership_team.json` | leadership_team | `clc-2026-leadership-biweekly` | **biweekly** |
| `kitchen_staff.json` | kitchen_staff | `clc-2026-kitchen-daily` | daily |
| `maintenance.json` | maintenance | `clc-2026-maintenance-daily` | daily |
| `housekeeping.json` | housekeeping | `clc-2026-housekeeping-daily` | daily |
| `camper_care.json` | camper_care | `clc-2026-camper-care-daily` | daily |
| `health_center.json` | health_center | `clc-2026-health-center-daily` | daily |
| `special_diets.json` | special_diets | `clc-2026-special-diets-daily` | daily |

**Org & program slugs (per `onboard_clc_summer_2026.py`):**
- Organization slug: `clc`
- Program slug: `summer-2026`

**Notes on the inventory:**
- The Leadership Team template is BIWEEKLY, not daily. Easy mistake — the seeding command must use the template's own cadence (no `cadence_override`).
- There is no `admin` template in the manifest. Confirmed in 7_21 that admin's dashboard does not consume a template resolver (admin's surface is template oversight via `templates.py` / `dashboard.py::_pending_template_review_count`). Therefore: **no `admin` assignment row needs to be created.**
- The `unit_head` template was added as part of this prompt's pre-flight work (file: `templates/reflection_templates/clc_2026/unit_head.json`; manifest entry added to `onboard_clc_summer_2026.py`). UH self-reflection is Story 16 and a Wave 1 launch requirement. The template ships with placeholder copy in the same `[PLACEHOLDER]` / `TODO(BRENT)` style as the other 11; Brent will replace the prompts before launch.
- All assignments target the role (`target_type='role'`), not per-bunk. The counselor self-reflection is `role`-targeted as well, since the existing `counselor_self_template` helper in `api/counselor/common.py` iterates the viewer's Memberships and queries for a role-targeted assignment.

---

## Backend tasks

### 1. New management command: `seed_summer_2026_assignments`

Place at `backend/bunk_logs/core/management/commands/seed_summer_2026_assignments.py`.

Command signature:

```bash
python manage.py seed_summer_2026_assignments \
    --org-slug clc \
    --program-slug summer-2026 \
    [--dry-run] \
    [--actor-username <admin-user>]
```

Behavior:

- **Idempotent**: re-running with the same args produces the same set of assignments (no duplicates, no orphans).
- **`--dry-run`**: prints what would be created/updated; makes no DB changes.
- **`--actor-username`**: optional; resolves to a User whose admin or LT Membership in the target org becomes the `created_by` on each row. Defaults to None when not provided (created_by may be null per the model definition).
- Wraps all writes in a single transaction so a partial failure leaves no partial seed.

### 2. The canonical assignment list for Summer 2026

One TemplateAssignment row per template, all `target_type='role'`, all `is_required=True`. The start date is the program's `start_date` (which is `2026-06-05` per `setup_crane_lake.py`); the end date is the program's `end_date`.

Each assignment uses `cadence_override=None` so the template's own cadence applies (daily for most, biweekly for LT).

```python
ASSIGNMENT_MANIFEST = [
    {"role": "counselor",          "slug": "clc-2026-counselor-daily",            "title": "Counselor daily bunk log"},
    {"role": "junior_counselor",   "slug": "clc-2026-junior-counselor-daily",     "title": "Junior counselor daily reflection"},
    {"role": "general_counselor",  "slug": "clc-2026-general-counselor-daily",    "title": "General counselor daily reflection"},
    {"role": "specialist",         "slug": "clc-2026-specialist-daily",           "title": "Specialist daily reflection"},
    {"role": "unit_head",          "slug": "clc-2026-unit-head-daily",            "title": "Unit head daily reflection"},
    {"role": "leadership_team",    "slug": "clc-2026-leadership-biweekly",        "title": "Leadership team check-in (biweekly)"},
    {"role": "kitchen_staff",      "slug": "clc-2026-kitchen-daily",              "title": "Kitchen staff daily reflection"},
    {"role": "maintenance",        "slug": "clc-2026-maintenance-daily",          "title": "Maintenance daily reflection"},
    {"role": "housekeeping",       "slug": "clc-2026-housekeeping-daily",         "title": "Housekeeping daily reflection"},
    {"role": "camper_care",        "slug": "clc-2026-camper-care-daily",          "title": "Camper care daily reflection"},
    {"role": "health_center",      "slug": "clc-2026-health-center-daily",        "title": "Health center daily reflection"},
    {"role": "special_diets",      "slug": "clc-2026-special-diets-daily",        "title": "Special diets daily reflection"},
]
```

**12 assignments total** — one per CLC 2026 template. No `admin` row.

### 3. Implementation outline

```python
class Command(BaseCommand):
    help = "Seed TemplateAssignment rows for the CLC Summer 2026 program."

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
        plan = []
        missing = []
        for entry in ASSIGNMENT_MANIFEST:
            try:
                template = ReflectionTemplate.all_objects.get(
                    organization=org,
                    slug=entry["slug"],
                )
            except ReflectionTemplate.DoesNotExist:
                missing.append(entry["slug"])
                continue
            plan.append({
                "organization": org,
                "program": program,
                "template": template,
                "role": entry["role"],
                "title": entry["title"],
                "start_date": program.start_date,
                "end_date": program.end_date,
            })
        if missing:
            slugs = ", ".join(missing)
            raise CommandError(
                f"Template(s) not found for org={org.slug}: {slugs}. "
                f"Run onboard_clc_summer_2026 first.",
            )
        return plan

    def _upsert_assignment(self, entry, *, actor):
        existing = TemplateAssignment.all_objects.filter(
            program=entry["program"],
            template=entry["template"],
            target_type=TemplateAssignment.TargetType.ROLE,
            target_payload__role=entry["role"],
            status__in=[
                TemplateAssignment.Status.SCHEDULED,
                TemplateAssignment.Status.ACTIVE,
            ],
        ).first()

        if existing:
            changed = False
            if existing.title != entry["title"]:
                existing.title = entry["title"]
                changed = True
            if not existing.is_required:
                existing.is_required = True
                changed = True
            if changed:
                existing.save(update_fields=["title", "is_required"])
                self.stdout.write(f"updated {existing}")
            else:
                self.stdout.write(f"unchanged {existing}")
            return existing

        new_assignment = TemplateAssignment.all_objects.create(
            organization=entry["organization"],
            program=entry["program"],
            template=entry["template"],
            target_type=TemplateAssignment.TargetType.ROLE,
            target_payload={"role": entry["role"]},
            start_date=entry["start_date"],
            end_date=entry["end_date"],
            cadence_override=None,
            is_required=True,
            title=entry["title"],
            status=TemplateAssignment.Status.SCHEDULED,
            created_by=actor,
        )
        self.stdout.write(self.style.SUCCESS(f"created {new_assignment}"))
        return new_assignment
```

The idempotency key is `(program, template, target_type='role', target_payload['role'])`. If an existing scheduled/active row matches, update title/is_required only. Never resurrect ended or cancelled rows.

### 4. Date window

- `start_date`: `program.start_date` (2026-06-05 per setup_crane_lake.py).
- `end_date`: `program.end_date` (2026-08-14 per setup_crane_lake.py).

These flow directly from the Program record; do not hardcode dates in the command.

### 5. Pre-flight checks before writes

The command should refuse to run (raise CommandError) if:

- The organization doesn't exist.
- The program doesn't exist.
- ANY expected template is missing (list all missing templates in the error).

The command should log a warning and skip (not fail) if:

- An assignment with the same key already exists in a status that isn't `active` or `scheduled` (e.g. `ended` or `cancelled`). The intent is "seed fresh," not "resurrect."

### 6. Cross-program / cross-org safety

Re-running the command against a different program-slug must not affect Summer 2026 assignments. The idempotency key includes `program`, so this is automatic, but include an explicit test (task 7.6 below).

### 7. Tests

Create `backend/bunk_logs/core/tests/test_seed_summer_2026_assignments.py` (or under `core/management/tests/` matching the existing convention; check what exists).

1. **Happy path**: seed against a fixture with all 12 expected templates → 12 assignments created.
2. **Idempotency**: run twice → 12 assignments, no duplicates, no errors.
3. **Dry run**: produces no DB writes; lists what would be done.
4. **Missing template**: run against a fixture missing one template → CommandError with the missing slug named.
5. **Title update**: pre-create an assignment with wrong title → re-running command corrects the title; row count unchanged.
6. **Cross-program isolation**: seed Summer 2026, then create a hypothetical Summer 2027 program in the same org, run for 2027 → Summer 2026 assignments untouched.
7. **Cross-org isolation**: seed CLC, then run for a different org → CLC assignments untouched.
8. **Existing ended/cancelled row**: an ended assignment exists for the same (program, template, role) → command logs warning and creates a NEW scheduled row alongside (does not resurrect).

### 8. Documentation

Add a new section to `docs/clc-summer-2026-launch.md` titled "Seeding TemplateAssignments (Step 7_22)" with:

- The command invocation.
- The list of 12 assignments it creates.
- The expected verification step: run on staging, log in as Alyson, confirm dashboards populate.
- The production deploy sequence (see "Final Wave 1 sequence" below).

If `docs/clc-summer-2026-launch.md` does not exist, create it with just this section plus a header. Don't bloat it; the production deploy plan in `docs/wave_1_progress.md` is the canonical source.

### 9. Acceptance criteria for this prompt

- Command exists and is idempotent across all 8 test cases.
- All 12 assignments are created when run against the CLC Summer 2026 fixtures.
- Per-role dashboards (post-7_21 refactor) return non-empty results after seeding (verified by running 7_21 dashboard tests with seed data present).
- All tests pass; `ruff check` clean.
- Frontend tests unaffected.
- Smoke test on local dev: run `onboard_clc_summer_2026 --skip-import` to ensure templates exist, then run `seed_summer_2026_assignments --org-slug clc --program-slug summer-2026`, then query TemplateAssignment count = 12.

### 10. Commit / PR conventions

Per the existing pattern:

- Branch: `step/7_22_seed_summer_2026_assignments`
- Commit: `feat(7_22_seed_summer_2026_assignments): seed TemplateAssignment rows for CLC Summer 2026`
- Open a PR with `gh pr create`; title `7_22: Seed TemplateAssignments for Crane Lake Summer 2026`. Don't merge yourself.
- PR description includes:
  - **What**: command summary + 12 assignments produced.
  - **Why**: link to design doc and decision FA10.
  - **Testing**: tests + dry-run output from local dev.
  - **Risk assessment**: if template slugs in the seed table don't match production templates, dashboards stay empty after deploy. Mitigation: dry-run against staging-with-prod-snapshot before deploy.
  - **Rollback plan**: TemplateAssignment rows can be marked `status='cancelled'`. The cleaner rollback is to revert 7_21 and 7_22 as a pair.

## Final Wave 1 sequence

Once 7_22 is merged:

1. Deploy 7_20 + 7_21 + 7_22 to production in a single maintenance window (suggested: evening of June 1 or 2).
2. Run the seeding command in production: `python manage.py seed_summer_2026_assignments --org-slug clc --program-slug summer-2026`.
3. Smoke test as Alyson immediately after.
4. Monitor Datadog APM for unexpected dashboard errors over the next 24 hours.
5. By June 3 at the latest, declare Wave 1 done or trigger the FA10(b) escape-hatch rollback.

After Wave 1 ships and stabilizes:

- Re-verify the existing canonical user stories against the new substrate.
- Plan Notes module deploy (7_19) for late June.
- Begin Wave 2 work in July (FA-E, FA-P, FA-F, FA-G, FA-H, FA-I).

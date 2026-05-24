# Wave 1 Progress — Form Orchestration Reframe (FA10(a))

**Goal:** Ship the TemplateAssignment extension + per-role dashboard refactor + Summer 2026 seeding before June 5, 2026.

**Total estimated work:** 9–15 hours across three prompts, plus 3–5 hours of canonical-story re-verification.

**Hard deadline:** Production deploy by June 3, 2026 (gives 2-day buffer before June 5 staff onboarding).

**Escape hatch:** If any prompt fails or scope creeps past estimate, revert in-progress work and proceed with FA10(b) (post-summer rollout). The existing implicit-template-resolution code remains the production source of truth until 7_21+7_22 are deployed together.

---

## Status legend

- ⬜ Not started
- 🔄 In progress (branch open, work underway)
- 👀 In review (PR open, awaiting self-review or test pass)
- ✅ Merged to main
- 🚀 Deployed to production
- ❌ Blocked or reverted

---

## Prompt tracker

### Step 7_20 — Extend TemplateAssignment

**Status:** ✅ Merged to main
**Branch:** `step/7_20_extend_template_assignment` (merged)
**PR:** https://github.com/pantheonsteve/BunkLogs/pull/118
**Estimated:** 3–5 hours
**Actual:** 0.25 hours

**Scope reminder:** Add `assignment_group` FK, `is_required` flag, `title` field. Add `'assignment_group'` to TargetType. Extend `resolve_members` with the new branch. Widen permission gate to admin (FA7). Tests.

**Verified post-merge (2026-05-24):**
- `TemplateAssignment` model has `assignment_group`, `is_required`, `title`, `ASSIGNMENT_GROUP` in TargetType ✅
- `resolve_members` handles the new branch with `author_role_filter` check ✅
- `_serialize` exposes `assignment_group`, `is_required`, `title`, `display_title` ✅
- `assignment_viewer_or_403` helper exists in `api/leadership_team/common.py` (FA7 widening) ✅
- Migration index `core_templa_assignm_8ec6ca_idx` on `(assignment_group, status)` ✅

**Notes / blockers:**

- None.

---

### Step 7_21 — Per-role dashboard refactor

**Status:** 👀 In review
**Branch:** `step/7_21_dashboard_template_resolution`
**PR:** _(open after push)_
**Estimated:** 4–6 hours
**Actual:** ~3 hours
**Depends on:** 7_20 merged

**Scope reminder:** Create `core/assignment_resolution.py` shared resolver. Refactor 8 per-role `common.py` files to use it. One commit per role. Update existing tests to create TemplateAssignment rows.

**Per-role progress** (within the prompt):

- ✅ kitchen_staff
- ✅ madrich
- ✅ specialist
- ✅ counselor (camper-reflection + self templates)
- ✅ unit_head
- ✅ camper_care
- ✅ leadership_team
- ➖ admin_flow — no template helper to refactor; admin's template surface is oversight (`templates.py`, `dashboard.py::_pending_template_review_count`), not resolution

**Notes / blockers:**

- Backend test suite passes 1135 tests after refactor + fixture updates. One pre-existing failure in `core/test_translation::TestBeatRegistration::test_migration_installs_the_periodic_task_row` is unrelated (PeriodicTask seed missing in test DB).
- Production note: dashboards will return `no_template` empty state in prod until 7_22 seeds TemplateAssignment rows. Do NOT deploy 7_21 standalone — coordinate with 7_22.

---

### Step 7_22 — Seed Summer 2026 TemplateAssignments

**Status:** ⬜ Not started
**Branch:** _(not yet)_
**PR:** _(not yet)_
**Estimated:** 2–4 hours
**Actual:** _(record when done)_
**Depends on:** 7_21 merged

**Scope reminder:** Idempotent management command `seed_summer_2026_assignments`. Verify the canonical assignment list against actual seeded templates before running.

**Notes / blockers:**

- _Add as you encounter them_

---

### Canonical story re-verification

**Status:** ⬜ Not started
**Estimated:** 3–5 hours
**Depends on:** 7_20 + 7_21 + 7_22 merged to staging

For each existing canonical story under `docs/user_stories/01_counselor/` through `09_madrich/`, verify the acceptance criteria still hold against the assignment-driven substrate. Most should pass without code change.

**Per-role re-verification progress:**

- ⬜ 01_counselor (Stories 1–9)
- ⬜ 02_unit_head (Stories 10–17)
- ⬜ 03_camper_care (Stories 18–23)
- ⬜ 04_specialist (Stories 24–29)
- ⬜ 05_maintenance (Stories 30–34)
- ⬜ 06_kitchen_staff (Stories 35–40)
- ⬜ 07_leadership_team (Stories 45–53)
- ⬜ 08_admin (Stories 54–60)
- ⬜ 09_madrich (Stories 61–65)

**Findings (record any divergence here):**

- _Add as you find them_

---

## Production deploy plan

When all three prompts are merged and the re-verification passes:

1. **Pre-deploy** (the day before):
   - Run `seed_summer_2026_assignments --dry-run` against staging-with-prod-snapshot.
   - Verify the dry-run output matches expectations.
   - Have Alyson smoke-test the dashboards on staging.
2. **Deploy window** (target: evening of June 1 or 2, 2026):
   - Merge 7_20, 7_21, 7_22 to main in order.
   - Trigger production deploy via the standard Render flow.
   - Run `python manage.py seed_summer_2026_assignments --org-slug crane-lake-camp --program-slug summer-2026` in production shell.
   - Verify a sample of dashboards as Alyson.
3. **Post-deploy monitoring** (next 24–48 hours):
   - Watch Datadog APM for dashboard endpoint errors.
   - Watch for support requests from Alyson.
   - Have rollback plan ready (revert merge commits, in reverse order: 7_22 → 7_21 → 7_20).

---

## Rollback plan

If any of these conditions are true by June 3:

- A Wave 1 prompt has not merged to main.
- The re-verification surfaced a blocker.
- Alyson reports problems during staging smoke-test that can't be resolved by June 3.

Then:

1. **Revert 7_22, 7_21, 7_20** in that order (each is independently revertible).
2. **Re-seed the pre-7_20 state** if any TemplateAssignment rows were created.
3. **Proceed with the original implicit-template-resolution code** for June 5 launch.
4. **Update `decisions.md` FA10** to reflect the actual outcome (mark FA10(a) attempted but descoped to FA10(b)).
5. **Plan Wave 1 for late June / July** as part of post-summer-launch work.

---

## Update cadence

- After each commit: update the status of the active prompt.
- After each PR merge: flip prompt status to ✅ and update timing actuals.
- After production deploy: flip 7_20, 7_21, 7_22 to 🚀.
- If any prompt blocks: flip status to ❌ and record the reason.
- When Wave 1 is fully ✅+🚀: archive this file at `docs/wave_1_progress_2026_complete.md` and remove from this location.

---

## Wave 1 complete state

Wave 1 is "done" and ready to be archived when:

- ⬜ 7_20 deployed to production
- ⬜ 7_21 deployed to production
- ⬜ 7_22 deployed to production
- ⬜ Seeding command run in production
- ⬜ Alyson confirms dashboards work for a sample counselor and UH on staging *and* production
- ⬜ 24 hours of clean Datadog APM signal post-deploy
- ⬜ Re-verification complete across all 9 role flows
- ⬜ June 5 staff onboarding runs cleanly on the new substrate

When all checkboxes above are ✅, archive this file and start tracking the next thing (likely the Notes module deploy, 7_19).

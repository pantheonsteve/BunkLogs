# Step 7_15: TBE Program Setup

**Goal:** Implement TBE-specific configuration, templates, and deployment runbook for Fall 2026 launch.

**Canonical product spec:** Stories 61-65 + organizational setup from migration prompts 4_1 through 4_6.

**Depends on:** 7_13 (Admin flow), 7_14 (Madrich flow).

**Scope of this step:**

1. Backend: TBE-specific seed command `python manage.py seed_tbe_program <slug>`:
   1. Creates TBE Organization with `religious_school` type, Eastern timezone, 00:00 rollover, English-only language support.
   2. Creates TBE Religious School 2026-27 Program with appropriate dates.
   3. Creates TBE 3-2-1 reflection template assignment to `madrich` role with weekly cadence, start date matching program start.
   4. Configures Wednesday-evening reminder schedule.
   5. Idempotent.
2. Backend: TBE roster import handling per migration Story 4_3. Verify still works post-7_13.
3. Frontend: TBE-specific Admin onboarding wizard at `frontend/src/pages/admin/onboarding/tbe.jsx` (one-time use; guides Rachel through people invitation, template review, soft-launch group selection).
4. Documentation: `docs/tbe_launch_runbook.md`:
   1. Pre-launch checklist (people imported, template assigned, reminders scheduled, soft launch group identified)
   2. Soft-launch August: 8-10 Madrichim
   3. Full-launch September: all Madrichim
   4. First two weeks monitoring + intensive support
   5. Rollback plan (deactivate template assignment, communicate via email)
5. Tests:
   1. Seed command idempotency test.
   2. End-to-end test: TBE seeded, sample Madrich submits weekly reflection, Rachel reads it from her Director dashboard.

**Out of scope:**

- Tier 2 features per TBE proposal: faculty self-assessment, weekly job success contract, parent communication, classroom observation tool, multi-year tracking, grade-differentiated content.

**Commit scope: `feat(7_15_tbe_program_setup): ...`. PR title prefix: `7_15`.**

End-to-end onboarding script that prepares Crane Lake for June 5 launch. Combines previous setup commands plus verification.

Tasks:
1. Create `core/management/commands/onboard_clc_summer_2026.py`.
2. Command runs:
   - setup_crane_lake (org + program)
   - Seeds all role templates (loops over template files)
   - Imports staff from Campminder CSV (path passed as arg)
   - Verifies counts (orgs, programs, persons, memberships, templates)

3. Output: clear summary of what was set up.

4. Run on staging environment first. Verify thoroughly.

5. Document the launch runbook in docs/clc-summer-2026-launch.md:
   - Pre-launch checklist
   - Day-of steps
   - Rollback plan
   - Monitoring during first 48 hours

Acceptance criteria:
- Onboarding command runs cleanly on staging
- Runbook complete
- All verifications pass
- Commit with message: "Add Crane Lake summer 2026 onboarding command and runbook"
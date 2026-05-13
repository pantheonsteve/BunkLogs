Document the TBE launch process and create a launch command.

Tasks:
1. Create `core/management/commands/onboard_tbe_2026.py` combining setup_tbe, template seeding, and roster import.
2. Document launch runbook in docs/tbe-2026-launch.md:
   - August soft launch (8-10 Madrichim)
   - September full launch
   - Pre-launch checklist
   - Day-of steps
   - Rollback plan
   - First 2 weeks of intensive support

3. Run on staging, verify, document findings.

Acceptance criteria:
- Onboarding command runs cleanly on staging
- Runbook complete
- Commit with message: "Add TBE 2026 onboarding command and launch runbook"
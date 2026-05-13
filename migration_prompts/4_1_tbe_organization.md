Create TBE organization and 2026-27 Religious School program records.

Tasks:
1. Create `core/management/commands/setup_tbe.py` (modeled on setup_crane_lake).
2. Idempotent. Creates:
   - Organization (slug='tbe')
   - Program "TBE Religious School 2026-27" (program_type='religious_school', dates per TBE calendar)
   - Configures organization.settings with TBE-specific config

3. Tests for idempotency and correctness.

Acceptance criteria:
- Command exists and works
- Tests pass
- Commit with message: "Add TBE organization setup command"
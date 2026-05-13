Migrate Crane Lake's pre-Summer-2026 historical data from old models (Camper, Bunk, BunkLog, etc.) into new models. Run dry-run first.

Tasks:
1. Create `core/management/commands/migrate_clc_historical.py`.
2. Flag: --dry-run (default True; require --apply to write)
3. Migration logic:
   - For each historical Session (excluding Summer 2026 which is already on new models): create matching Program (program_type='summer_camp')
   - For each historical Camper not yet a Person: create Person record
   - For each CamperBunkAssignment: create Membership
   - For each historical staff User: create Person + link via Person.user
   - For each BunkLog: create a Reflection using a 'crane_lake_legacy_daily_log' template (seed if not present)
   - Map old fields to new answers JSON
4. Output: counts, sample migrations, warnings.
5. Wrapped in transaction in --apply mode.
6. Tests with realistic fixtures.

Acceptance criteria:
- Dry run accurate
- Apply mode transactional and idempotent
- Tests pass
- Commit with message: "Add Crane Lake historical data migration (dry-run)"

DO NOT --apply against production yet.
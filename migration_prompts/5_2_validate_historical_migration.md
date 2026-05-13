Run migration against staging copy of production data. Verify thoroughly.

Tasks:
1. Set up staging with production data dump.
2. Run migration in --dry-run mode. Capture output.
3. Run migration in --apply mode against staging.
4. Run verification command (write `core/management/commands/verify_clc_migration.py`):
   - Old Camper count == new Person count (excluding Summer 2026 persons)
   - Old BunkLog count == new Reflection count for legacy program
   - Spot-check 30 random old BunkLogs against their new Reflection equivalents
   - No orphan records
   - All Reflections have valid answers per template
5. Document in docs/clc-historical-migration-validation.md.

Acceptance criteria:
- Verification command exists
- Validation document confirms migration is clean
- Issues filed as new prompts
- Commit with message: "Validate Crane Lake historical migration on staging"
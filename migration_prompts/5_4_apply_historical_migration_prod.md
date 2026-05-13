Run migration against production. Procedural prompt — mostly verification.

Tasks:
1. Schedule maintenance window with Alyson (post-summer 2026, low-usage period).
2. Pre-migration:
   - Full database backup
   - Capture record counts of all old models
   - Verify staging migration was clean
3. Run migration --apply.
4. Post-migration:
   - Run verify_clc_migration.py
   - Spot-check records
   - Smoke test as Alyson
5. Monitor Datadog 48 hours.
6. Document in docs/production-migration-2026-XX.md.

Acceptance criteria:
- Migration applied cleanly
- Verification passes
- No errors in Datadog
- Alyson confirms system works
- Document any issues encountered

Rollback plan: restore from pre-migration backup if invalid data appears.
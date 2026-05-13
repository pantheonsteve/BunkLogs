Final cleanup: drop old tables. After 8+ weeks of stable operation only.

Tasks:
1. Generate empty migration with DeleteModel for each deprecated model.
2. Test migration in staging with recent prod backup.
3. Apply in production during maintenance window.
4. Verify no errors. Take fresh backup post-migration.

Acceptance criteria:
- Old tables dropped
- App runs cleanly
- Backups before and after
- Commit with message: "Drop deprecated camp model tables"
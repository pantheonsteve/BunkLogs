After Crane Lake is stable on new models for 4+ weeks, mark old models deprecated.

Tasks:
1. Add deprecation comment to each old model.
2. Override save() to raise (read-only).
3. Update Django admin: read-only display.
4. Run all tests.

Acceptance criteria:
- Old models readable, not writable
- Admin shows read-only
- Tests pass
- Commit with message: "Mark old camp models as deprecated and read-only"
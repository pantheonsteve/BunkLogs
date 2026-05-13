Beyond api/views.py (already fixed), there are references to removed ORM fields in `UserSerializer`, `auth_api.py`, and possibly other files. Removed fields: `Bunk.counselors` (M2M), `User.assigned_bunks` (M2M), `Unit.unit_head` (FK), `Unit.camper_care` (FK). They were replaced by the `UnitStaffAssignment` join table.

Tasks:
1. Search the entire codebase (Python only) for: `assigned_bunks`, `managed_units`, `unit_head`, `camper_care`, `bunk.counselors`. List every file with a match.
2. For each match, determine whether to:
   a) Replace with a UnitStaffAssignment query
   b) Delete (if surrounding code is also dead)
   c) Keep (if it's a different field with a similar name — verify carefully)
3. Make the corrections, preserving existing behavior where possible.
4. Update tests. Add new tests if coverage is missing.
5. Run pytest and ruff check.

Acceptance criteria:
- No references to removed fields remain (verified by grep)
- Replaced code uses UnitStaffAssignment correctly
- All affected endpoints covered by tests
- Tests and linter pass
- Smoke test the auth flow in dev
- Commit with message: "Migrate remaining ORM drift to UnitStaffAssignment"
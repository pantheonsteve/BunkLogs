The file `[path to your api/views.py]` contains a duplicate class definition with `# noqa: F811`. The second definition silently overrides the first and uses removed ORM fields (`assigned_bunks`, `managed_units`).

Tasks:
1. Locate the duplicate class. Read both definitions carefully and determine which is correct given the current data model (UnitStaffAssignment, not the removed M2M fields).
2. Identify all callers of this viewset (URL routes, frontend API calls, tests).
3. Delete the incorrect duplicate.
4. Update the surviving class to use the current ORM (UnitStaffAssignment queries, not assigned_bunks).
5. Remove the `# noqa: F811` comment.
6. Add or update tests that verify the viewset returns the correct data for each user role (camper, counselor, unit head, admin).
7. Run the test suite and the linter (ruff). Both should pass.

Acceptance criteria:
- No `# noqa: F811` comments remain in api/views.py
- The viewset uses UnitStaffAssignment queries, not removed fields
- Tests cover the role-based filtering behavior
- `pytest` and `ruff check` both pass
- Manual smoke test: log in as a counselor in dev, verify the viewset returns the expected bunks
- Commit with message: "Resolve duplicate viewset class and migrate to UnitStaffAssignment queries"
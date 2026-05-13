Import staff roster from Crane Lake's Campminder system. Must store Campminder IDs on Person records for cross-system reference.

Tasks:
1. Create `core/management/commands/import_campminder_staff.py`.
2. Command accepts:
   - --csv-path (CSV exported from Campminder)
   - --org-slug (e.g., 'clc')
   - --program-slug (e.g., 'summer-2026')
   - --dry-run flag

3. CSV columns expected (document in docs/campminder-import.md):
   - campminder_id, first_name, last_name, email, role, language_preference, tags

4. Command logic:
   - For each row: get_or_create Person by campminder_id (stored in external_ids dict)
   - If Person new: create with provided fields
   - If Person exists: update name/email if changed
   - Create or update Membership for the program
   - Apply tags

5. Idempotent: re-running same CSV doesn't duplicate.

6. Tests with sample CSV.

7. Document the workflow in docs/campminder-import.md including:
   - How to export from Campminder
   - Required CSV format
   - Running the command
   - Verifying results

Acceptance criteria:
- Command imports correctly
- Idempotent
- Tests pass
- Documentation written
- Commit with message: "Add Campminder staff import command"
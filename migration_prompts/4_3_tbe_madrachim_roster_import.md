Import TBE Madrichim roster. Modeled on the Campminder import, but TBE will likely export from ShulCloud or provide a custom CSV.

Tasks:
1. Create `core/management/commands/import_tbe_madrichim.py`.
2. CSV columns: first_name, last_name, email, grade_level, parent_email (optional).
3. Command creates Person and Membership (role='madrich') records.
4. Idempotent (matches by email or first+last+grade_level).
5. Tests with sample CSV.
6. Document expected CSV format.

Acceptance criteria:
- Command works correctly
- Idempotent
- Tests pass
- Commit with message: "Add TBE Madrichim roster import command"
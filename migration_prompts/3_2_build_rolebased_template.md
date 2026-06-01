Create the framework for seeding role-specific reflection templates. Individual templates will be added per role in subsequent prompts (one per role) once Brent provides specific questions.

Tasks:
1. Create `core/management/commands/seed_role_template.py` that takes:
   - --org-slug (e.g., 'clc')
   - --role (must match a Membership role choice)
   - --template-file (path to JSON file with template definition)
   - --dry-run flag

2. The command:
   - Loads the JSON template file
   - Validates the schema structure (uses ReflectionTemplate.schema validation logic)
   - Creates or updates the template (idempotent by org+slug+version)
   - Reports what was created/updated

3. Create `templates/reflection_templates/` directory in repo for JSON template files.

4. Add a sample template file `templates/reflection_templates/example_counselor.json` with a basic counselor reflection (placeholder content; real content comes from Brent).

5. Tests:
   - Command creates template from valid JSON
   - Dry run produces output without writing
   - Invalid schema produces clear error
   - Re-running with same file is idempotent

Acceptance criteria:
- Framework command exists
- Sample template file in repo
- Tests pass
- Documentation in docs/seeding-templates.md
- Commit with message: "Add role-based template seeding framework"
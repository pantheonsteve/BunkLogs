Create the Crane Lake Organization and Summer 2026 Program records on the new architecture. This is the first real data flowing into the new models.

Tasks:
1. Create management command `core/management/commands/setup_crane_lake.py`.
2. Idempotent. The command:
   - Creates Crane Lake Organization (slug='clc') if not exists
   - Creates Summer 2026 Program (program_type='summer_camp', dates per actual camp calendar)
   - Sets organization.settings to include any Crane Lake-specific config (timezone, etc.)
3. Tests: command is idempotent, creates expected records.

Acceptance criteria:
- Command exists and is idempotent
- Crane Lake org and Summer 2026 program created
- Tests pass
- Commit with message: "Add Crane Lake organization setup command"
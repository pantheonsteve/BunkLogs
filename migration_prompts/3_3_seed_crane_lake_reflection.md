Create JSON template files for each Crane Lake role and seed them. Requires actual question content from Brent — do not invent questions.

PREREQUISITE: Specific reflection questions per role from Brent. If not available, skip this prompt and use placeholder content with a TODO comment, then revisit when content arrives.

Roles needing templates:
- counselor (existing daily reflection — port the current BunkLog questions)
- junior_counselor
- specialist
- general_counselor
- leadership_team (1-2x per week, "How is the unit doing?" — biweekly cadence)
- kitchen_staff (Spanish + English)
- maintenance (Spanish + English)
- housekeeping (Spanish + English)
- camper_care (wellness team)
- health_center (wellness team)
- special_diets (wellness team)

Tasks:
1. Create one JSON template file per role under `templates/reflection_templates/clc_2026/`.
2. Each template includes:
   - Role-appropriate prompts in English
   - Spanish translations for kitchen, maintenance, housekeeping
   - Appropriate cadence (most are daily; leadership_team is biweekly)
   - Appropriate field types (text, textarea, rating_group)
3. Run `seed_role_template` for each.
4. Verify all templates exist in admin.
5. Document the templates in `docs/clc-2026-templates.md` listing each template, its role, cadence, and language coverage.

Acceptance criteria:
- One template per role exists
- Spanish translations present where needed
- Documentation lists all templates
- Templates validate against schema
- Commit with message: "Seed Crane Lake Summer 2026 role-based reflection templates"

If specific questions aren't ready from Brent, use sensible placeholder questions and clearly mark with TODO. Revise when real content arrives.
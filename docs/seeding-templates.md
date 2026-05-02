# Seeding role-based reflection templates

Reflection templates for the multi-tenant `ReflectionTemplate` model can be loaded from JSON files using a Django management command. This keeps prompts in version control and makes Crane Lake / future tenants repeatable.

## Command

Run inside the backend container (see project `Makefile`; use `make shell` or the pattern used for other management commands):

```bash
python manage.py seed_role_template \
  --org-slug clc \
  --role counselor \
  --template-file templates/reflection_templates/example_counselor.json
```

### Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--org-slug` | yes | Target `Organization.slug` (org must already exist, e.g. via `setup_crane_lake`). |
| `--role` | yes | Must match a `Membership` role code (`counselor`, `kitchen_staff`, …). |
| `--template-file` | yes | Path to JSON file (absolute or relative to current working directory). |
| `--dry-run` | no | Validate the file and print what would happen; no database writes. |

### Idempotency

Templates are keyed by **organization + slug + version** (same uniqueness as the model). Re-running with the same file updates the row in place and does not create duplicates.

## JSON file shape

Top-level keys:

| Key | Required | Notes |
|-----|----------|--------|
| `name` | yes | Display name. |
| `slug` | yes | Stable slug within the org. |
| `cadence` | yes | One of: `daily`, `weekly`, `biweekly`, `monthly`, `on_demand`. |
| `schema` | yes | Object validated like `ReflectionTemplate.schema` (see [reflection-template-schema.md](reflection-template-schema.md)). |
| `version` | no | Integer ≥ 1; default `1`. |
| `program_type` | no | `summer_camp` or `religious_school`, or omit / null for any program type. |
| `description` | no | Default empty string. |
| `languages` | no | List of BCP 47 codes; default `[]`. |
| `is_active` | no | Default `true`. |

The **role** is not stored in the JSON file; it is supplied with `--role` so one schema file can be reused only if you intentionally use the same role when invoking the command.

## Sample file

See `templates/reflection_templates/example_counselor.json` for a minimal counselor placeholder.

## Related

- [Reflection template schema](reflection-template-schema.md) — field types and localized prompts (`en` / `es`).

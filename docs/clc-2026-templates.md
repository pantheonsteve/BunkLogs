# Crane Lake Summer 2026 role reflection templates

JSON definitions live under `backend/templates/reflection_templates/clc_2026/`. They target organization slug **`clc`** (create/update via `setup_crane_lake` before seeding).

## Template index

| File | Membership `--role` | Cadence | Languages | Notes |
|------|---------------------|---------|-----------|--------|
| `counselor.json` | `counselor` | daily | `en` | Mirrors legacy BunkLog counselor prompts from `frontend/src/components/form/BunkLogForm.jsx`. Brent may refine for standalone reflection UX. |
| `junior_counselor.json` | `junior_counselor` | daily | `en` | Placeholder prompts — TODO(BRENT). |
| `specialist.json` | `specialist` | daily | `en` | Placeholder prompts — TODO(BRENT). |
| `general_counselor.json` | `general_counselor` | daily | `en` | Placeholder prompts — TODO(BRENT). |
| `leadership_team.json` | `leadership_team` | biweekly | `en` | Unit pulse / wins & risks — TODO(BRENT). |
| `kitchen_staff.json` | `kitchen_staff` | daily | `en`, `es` | Placeholder bilingual — TODO(BRENT) + Spanish copy review. |
| `maintenance.json` | `maintenance` | daily | `en`, `es` | Placeholder bilingual — TODO(BRENT) + Spanish copy review. |
| `housekeeping.json` | `housekeeping` | daily | `en`, `es` | Placeholder bilingual — TODO(BRENT) + Spanish copy review. |
| `camper_care.json` | `camper_care` | daily | `en` | Wellness placeholder — TODO(BRENT); avoid PHI in free text. |
| `health_center.json` | `health_center` | daily | `en` | Placeholder — TODO(BRENT); follow charting policy. |
| `special_diets.json` | `special_diets` | daily | `en` | Placeholder — TODO(BRENT). |

Schema rules: [reflection-template-schema.md](reflection-template-schema.md). Seeding command: [seeding-templates.md](seeding-templates.md).

## Load all templates (local / container)

Ensure `clc` exists, then run `seed_role_template` once per row (paths resolve from repo root or `backend/`):

```bash
make shell   # or equivalent Django shell container
```

```bash
python manage.py setup_crane_lake

python manage.py seed_role_template --org-slug clc --role counselor \
  --template-file templates/reflection_templates/clc_2026/counselor.json
python manage.py seed_role_template --org-slug clc --role junior_counselor \
  --template-file templates/reflection_templates/clc_2026/junior_counselor.json
python manage.py seed_role_template --org-slug clc --role specialist \
  --template-file templates/reflection_templates/clc_2026/specialist.json
python manage.py seed_role_template --org-slug clc --role general_counselor \
  --template-file templates/reflection_templates/clc_2026/general_counselor.json
python manage.py seed_role_template --org-slug clc --role leadership_team \
  --template-file templates/reflection_templates/clc_2026/leadership_team.json
python manage.py seed_role_template --org-slug clc --role kitchen_staff \
  --template-file templates/reflection_templates/clc_2026/kitchen_staff.json
python manage.py seed_role_template --org-slug clc --role maintenance \
  --template-file templates/reflection_templates/clc_2026/maintenance.json
python manage.py seed_role_template --org-slug clc --role housekeeping \
  --template-file templates/reflection_templates/clc_2026/housekeeping.json
python manage.py seed_role_template --org-slug clc --role camper_care \
  --template-file templates/reflection_templates/clc_2026/camper_care.json
python manage.py seed_role_template --org-slug clc --role health_center \
  --template-file templates/reflection_templates/clc_2026/health_center.json
python manage.py seed_role_template --org-slug clc --role special_diets \
  --template-file templates/reflection_templates/clc_2026/special_diets.json

# Or run all at once using the onboarding command:
python manage.py onboard_clc_summer_2026 --skip-import
```

Use `--dry-run` to validate without writing. Re-running the same file updates the row (org + slug + version).

## Admin verification

After seeding, open Django admin → **Reflection templates** and confirm eleven active templates for organization Crane Lake (`clc`), each with the expected role, cadence, and `languages` list.

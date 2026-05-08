# Campminder Roster Import

This guide covers importing camper and staff rosters from Campminder exports into the BunkLogs multi-tenant data model. For the TBE ShulCloud importer, see [TBE Classroom Import](#tbe-shulcloud-classroom-import).

---

## Management command

```bash
# Inside the container
python manage.py import_campminder_roster \
  --csv-path /path/to/export.csv \
  --org-slug clc \
  --program-slug summer-2026

# Dry run (no DB writes)
python manage.py import_campminder_roster \
  --csv-path /path/to/export.csv \
  --org-slug clc \
  --program-slug summer-2026 \
  --dry-run

# Reconcile mode: deactivate memberships not in the CSV
python manage.py import_campminder_roster \
  --csv-path /path/to/export.csv \
  --org-slug clc \
  --program-slug summer-2026 \
  --reconcile
```

Or via the Makefile wrapper:

```bash
make shell  # opens Django shell_plus
# then call_command("import_campminder_roster", ...)
```

---

## CSV format

| Column | Required | Description |
|--------|----------|-------------|
| `campminder_id` | **Yes** | Unique Campminder identifier. Used as the idempotency key. |
| `first_name` | **Yes** | Legal or preferred first name. |
| `last_name` | **Yes** | Last name. |
| `role` | **Yes** | One of the valid `Membership.ROLES` values (see below). |
| `email` | No | Email address. Updated if changed on re-import. |
| `language_preference` | No | `en` or `es`. Stored in `Membership.metadata`. |
| `tags` | No | Comma-separated tag strings. Lowercased and deduplicated. |
| `bunk_name` | No | Creates/finds a `bunk` AssignmentGroup. |
| `unit_name` | No | Creates/finds a `unit` AssignmentGroup; set as parent of bunk. |
| `division_name` | No | Creates/finds a `division` AssignmentGroup; set as parent of unit. |
| `caseload_name` | No | Creates/finds a `caseload` AssignmentGroup. Requires `caseload_owner_campminder_id`. |
| `caseload_owner_campminder_id` | Conditional | Required when `caseload_name` is set. The owner is added as `author` of the caseload. |

### Valid role values

`camper`, `counselor`, `junior_counselor`, `specialist`, `general_counselor`, `unit_head`, `leadership_team`, `kitchen_staff`, `maintenance`, `housekeeping`, `camper_care`, `health_center`, `special_diets`, `madrich`, `faculty`, `admin`

### Role-to-group assignment

| Membership role | `role_in_group` in bunk |
|-----------------|------------------------|
| `camper` | `subject` |
| all other roles | `author` |

---

## Sample CSV

```csv
campminder_id,first_name,last_name,role,email,language_preference,tags,bunk_name,unit_name,division_name,caseload_name,caseload_owner_campminder_id
CM001,Alice,Smith,camper,alice@example.com,en,"swimming,nature",Bunk Maple,Sophomores,Upper Camp,,
CM002,Bob,Jones,camper,,,, Bunk Maple,Sophomores,Upper Camp,,
CM003,Carol,Lee,counselor,carol@example.com,es,,Bunk Maple,Sophomores,Upper Camp,,
CM004,Dave,Park,unit_head,dave@example.com,en,,,,,,
CM005,Wellness,Staff,camper_care,wellness@example.com,,,,,Senior Caseload,CM005
CM006,Evan,Reed,camper,evan@example.com,,,,,,Senior Caseload,CM005
```

This produces:
- `AssignmentGroup(group_type=division, name="Upper Camp")` with no parent
- `AssignmentGroup(group_type=unit, name="Sophomores", parent=Upper Camp)`
- `AssignmentGroup(group_type=bunk, name="Bunk Maple", parent=Sophomores)`
- Alice and Bob as **subjects** in Bunk Maple
- Carol as **author** in Bunk Maple
- Dave as staff-only (no bunk assignment)
- `AssignmentGroup(group_type=caseload, name="Senior Caseload")` with CM005 as author and Evan as subject

---

## Common workflows

### Initial summer import

1. Export the full roster from Campminder (campers + staff).
2. Run the importer with the default (additive) mode:
   ```bash
   python manage.py import_campminder_roster \
     --csv-path summer_full_roster.csv \
     --org-slug clc \
     --program-slug summer-2026
   ```
3. Verify in Django admin: check `AssignmentGroup` counts under the program, and spot-check a bunk's membership list.

### Mid-summer roster change (camper switched bunks)

1. Export the updated roster from Campminder.
2. Run with `--reconcile` to deactivate old assignments:
   ```bash
   python manage.py import_campminder_roster \
     --csv-path updated_roster.csv \
     --org-slug clc \
     --program-slug summer-2026 \
     --reconcile
   ```
   `--reconcile` only deactivates `AssignmentGroupMembership` records — it does **not** delete `Person` or `Membership` records.

### End-of-summer cleanup

Run `--reconcile` one final time with the end-of-season snapshot to ensure all deactivated campers/counselors are correctly marked inactive in their group assignments.

---

## Troubleshooting

### A Person exists but their `bunk_name` doesn't match anything

The importer uses `get_or_create` with a slugified `name`. If a bunk already exists with a different slug (e.g. "Bunk Maple" vs "Maple"), the importer creates a second group rather than merging.

**Resolution**: Ensure bunk names in the CSV match exactly what was used in the initial import. If you need to merge, use Django admin to reassign memberships and deactivate the duplicate group.

### `caseload_owner_campminder_id missing` warning

The row has a `caseload_name` but no `caseload_owner_campminder_id` column or value. Caseload assignment is skipped for that row.

**Resolution**: Ensure the caseload owner row appears somewhere in the CSV (or a prior import) and provide the owner's `campminder_id` in the `caseload_owner_campminder_id` column.

### Re-running produces 0 created / 0 updated

This is correct behaviour — the importer is fully idempotent. All rows already exist. No action needed.

### `Organization not found` / `Program not found`

Double-check the `--org-slug` and `--program-slug` values against Django admin → Core → Organizations / Programs. Slugs are case-sensitive.

---

## TBE ShulCloud classroom import

For Temple Beth-El, use `import_tbe_roster` which reads a ShulCloud CSV format:

```bash
python manage.py import_tbe_roster \
  --csv-path tbe_fall_roster.csv \
  --org-slug tbe \
  --program-slug religious-school-2026
```

### TBE CSV format

| Column | Required | Description |
|--------|----------|-------------|
| `first_name` | **Yes** | |
| `last_name` | **Yes** | |
| `role` | **Yes** | `madrich` or `faculty` (or other valid Membership roles) |
| `classroom_name` | **Yes** | Maps to `AssignmentGroup(group_type=classroom)` |
| `grade_level` | No | Integer grade level stored on `Membership.grade_level` |
| `email` | No | |

### TBE role assignment

| Role | `role_in_group` |
|------|----------------|
| `madrich` | **both** `subject` (faculty observes them) and `author` (self-reflection) |
| `faculty` | `author` only |
| all others | `subject` |

### TBE sample CSV

```csv
first_name,last_name,role,classroom_name,grade_level,email
Noah,Cohen,madrich,Tzedakah 101,10,noah@tbe.org
Maya,Levy,madrich,Tzedakah 101,10,maya@tbe.org
Rabbi,Gold,faculty,Tzedakah 101,,rgold@tbe.org
Ari,Klein,madrich,Chesed 201,11,ari@tbe.org
```

### TBE idempotency note

TBE's CSV has no external ID column. The importer matches on `(organization, first_name, last_name)`. Rename changes (e.g. "Noah" → "Noam") will create a second Person record — clean up manually in Django admin.

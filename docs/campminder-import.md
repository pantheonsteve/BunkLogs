# Campminder Staff Import

This document describes how to export a staff roster from Campminder and import it into BunkLogs using the `import_campminder_staff` management command.

## Overview

The command creates or updates `Person` and `Membership` records for each row in the CSV. It is idempotent — re-running with the same file does not produce duplicates.

**Person records are keyed by `campminder_id`**, stored in `Person.external_ids`. This is the stable cross-system identifier.

---

## Exporting from Campminder

1. Log in to your Campminder account.
2. Navigate to **Staff → Roster** (exact path varies by Campminder version).
3. Export to CSV. You will need to ensure the export includes at a minimum:
   - Staff ID (their internal Campminder ID)
   - First name, last name, email
   - Role / position

Campminder exports may have different column headers than those expected by this command. Rename the relevant columns in a spreadsheet editor before importing (see "Required CSV format" below).

---

## Required CSV Format

The CSV must have a header row with the following column names (order does not matter):

| Column | Required | Notes |
|--------|----------|-------|
| `campminder_id` | Yes | Unique staff ID from Campminder. Used to match existing records. |
| `first_name` | Yes | |
| `last_name` | Yes | |
| `email` | No | Blank is accepted. |
| `role` | Yes | Must match one of the valid BunkLogs roles (see below). |
| `language_preference` | No | Stored in `Membership.metadata`. E.g. `en`, `es`. |
| `tags` | No | Comma-separated list. Tags are stored on the `Membership` record and normalized to lowercase. |

### Valid roles

```
camper, counselor, junior_counselor, specialist, general_counselor,
unit_head, leadership_team, kitchen_staff, maintenance, housekeeping,
camper_care, health_center, special_diets, madrich, faculty, admin
```

Rows with an unrecognized role are skipped with a warning printed to stdout.

### Example CSV

```csv
campminder_id,first_name,last_name,email,role,language_preference,tags
10001,Alice,Smith,alice@example.com,counselor,en,"nature,arts"
10002,Bob,Jones,bob@example.com,unit_head,es,leadership
10003,Carmen,Rivera,carmen@example.com,kitchen_staff,es,
```

---

## Running the Command

All commands must be run inside the Podman container. Use `make shell` to open the Django shell, or prefix with `podman exec`.

### Basic import

```bash
podman exec -it bunklogs_django python manage.py import_campminder_staff \
  --csv-path /path/to/staff.csv \
  --org-slug clc \
  --program-slug summer-2026
```

### Dry run (no database writes)

```bash
podman exec -it bunklogs_django python manage.py import_campminder_staff \
  --csv-path /path/to/staff.csv \
  --org-slug clc \
  --program-slug summer-2026 \
  --dry-run
```

The dry run prints each row that would be processed and exits without touching the database.

### Passing the CSV from your host machine

If the CSV is on your local machine and not inside the container, copy it in first:

```bash
podman cp /path/to/staff.csv bunklogs_django:/tmp/staff.csv
podman exec -it bunklogs_django python manage.py import_campminder_staff \
  --csv-path /tmp/staff.csv \
  --org-slug clc \
  --program-slug summer-2026
```

Or use the Makefile shortcut (if defined):

```bash
make shell
# inside the container:
python manage.py import_campminder_staff --csv-path /tmp/staff.csv --org-slug clc --program-slug summer-2026
```

---

## Verifying Results

After the import, check the output summary:

```
Done. Created: 42  Updated: 3  Unchanged: 0
```

- **Created** — new `Person` records (and their `Membership` records).
- **Updated** — existing `Person` records whose `first_name`, `last_name`, or `email` changed.
- **Unchanged** — existing `Person` records with no field changes (their `Membership` tags/metadata are still refreshed).

Any rows skipped due to validation errors (missing `campminder_id`, unknown role) are printed as warnings below the summary line.

### Django admin

Browse to **Admin → Core → Persons** and filter by organization. The `external_ids` column will show `{"campminder_id": "10001"}` for imported records.

Browse to **Admin → Core → Memberships** and filter by program to see role assignments, tags, and metadata.

### Django shell

```python
from bunk_logs.core.models import Person, Membership
Person.objects.filter(external_ids__campminder_id="10001").first()
Membership.all_objects.filter(program__slug="summer-2026").count()
```

---

## Idempotency

The command is safe to re-run at any time:

- If a `Person` with the same `campminder_id` already exists, it is updated (not duplicated).
- `Membership` records are created with `get_or_create`; the `unique_together` constraint on `(program, person, role)` prevents duplicates at the database level.
- Tags and `language_preference` on `Membership` are always refreshed to match the latest CSV values.

---

## Field Mapping Reference

| CSV column | Django field |
|------------|-------------|
| `campminder_id` | `Person.external_ids["campminder_id"]` |
| `first_name` | `Person.first_name` |
| `last_name` | `Person.last_name` |
| `email` | `Person.email` |
| `role` | `Membership.role` |
| `language_preference` | `Membership.metadata["language_preference"]` |
| `tags` | `Membership.tags` (list of strings, normalized) |

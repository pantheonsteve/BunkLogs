# Assigning campers to bunks

Campers are placed in bunks as **subjects** of an `AssignmentGroup`. There are two
supported ways to do this in bulk. Which one you use depends on whether the
campers already exist in the system.

---

## Option A — One CSV with bunk columns (recommended)

Use this for an initial roster import when you want to create campers **and**
assign them to bunks in a single pass.

1. Go to **Admin → People** (`/admin/people`).
2. Click **Bulk import**.
3. Choose **Campminder** as the source and select your **program** (e.g. Summer 2026).
4. Download the **"Campers with bunk assignments"** template.
5. Fill in the CSV. Required and optional columns:

| Column | Required | Notes |
|--------|----------|-------|
| `PersonID` | Yes | Campminder ID. Used as the idempotency key. |
| `Last Name` | Yes | |
| `Preferred Name` or `First Name` | Yes (one of) | |
| `Role` | Yes | Use `camper`. |
| `Bunk Name` | Yes | Creates or finds the bunk group. |
| `Unit Name` | No | Creates the unit and sets it as the bunk's parent. |
| `Division Name` | No | Creates the division and sets it as the unit's parent. |

Example:

```csv
PersonID,Last Name,First Name,Preferred Name,Role,Bunk Name,Unit Name,Division Name
20476515,Abraham,,Allie,camper,Bunk Maple,Sophomores,Upper Camp
20476516,Cohen,,Sam,camper,Bunk Maple,Sophomores,Upper Camp
```

6. Click **Preview**, review the classified rows, then **Commit**.

What happens on commit:

- Creates or finds the `division → unit → bunk` group hierarchy.
- Adds each camper as a **subject** in their bunk.
- Re-running the same CSV is **idempotent**—no duplicate people or memberships.

---

## Option B — Import into one bunk at a time

Use this when the bunks already exist and you want to add campers to a **single
bunk** (or the campers already exist and just need bunk membership).

1. Go to **Admin → Assignment groups** (`/admin/groups`).
2. Open the bunk you want (e.g. "Bunk Maple").
3. Scroll to **Import roster from CSV**.
4. Set:
   - **Importer:** Campminder
   - **Import as:** **Subject (observed)** — correct for campers
   - **Reconcile:** check this to deactivate members removed from the CSV
5. Upload a Campminder-style CSV and click **Import**.

No `Bunk Name` column is needed—everyone in the file joins the bunk you are
viewing.

---

## What not to use

- **The "Campers" template** (People bulk import) imports people only. It has no
  `Bunk Name` column, so it does **not** assign anyone to a bunk.
- **Bulk import groups** (on the Groups list page) creates the bunk/unit/division
  **structure** only. It does not assign campers.

---

## Mid-season bunk changes

Re-export from Campminder and re-import with **Reconcile** enabled (either on the
per-bunk import or via the `import_campminder_roster --reconcile` command).
Reconcile deactivates old bunk memberships without deleting `Person` records.

---

## CSV encoding note

Campminder and Excel often export CSVs as Windows-1252 (Latin-1) rather than
UTF-8. The importer detects and handles these automatically, so accented names
(e.g. José, García) import cleanly. If you ever hit an encoding error, re-saving
the file from Excel as **CSV UTF-8** is the most reliable long-term format.

---

## Related guides

- [Assigning counselors to bunks](assign-counselors-to-bunks.md)
- [Assigning Camper Care to caseloads](assign-camper-care-caseloads.md)

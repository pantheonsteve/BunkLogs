# Assigning counselors to bunks

Counselors are placed on bunks as **authors** of an `AssignmentGroup`—the people
who observe and file forms about the campers in that bunk. This uses the same
machinery as camper assignment; the only difference is the role.

There are three ways to do it, from bulk to one-off.

---

## Option A — One CSV with bunk columns (recommended)

Use this for an initial roster load when you want to create staff **and** place
them on bunks in one pass.

1. Go to **Admin → People** (`/admin/people`).
2. Click **Bulk import**.
3. Choose **Campminder** and select your **program**.
4. Download the **"Campers with bunk assignments"** template (despite the name,
   it accepts counselors too).
5. Fill in counselor rows that include a `Bunk Name`:

```csv
PersonID,Last Name,First Name,Login/Email,Role,Bunk Name,Unit Name,Division Name
5927300,Baker,Jordan,jbaker@example.com,counselor,Bunk Maple,Sophomores,Upper Camp
5927301,Smith,Alex,asmith@example.com,junior_counselor,Bunk Birch,Sophomores,Upper Camp
```

Required columns for counselors:

- `PersonID`, `Last Name`, `First Name`
- `Role` — one of `counselor`, `junior_counselor`, `general_counselor`, `specialist`
- `Bunk Name`

Optional but useful:

- `Login/Email` — creates or links a login account
- `Unit Name` / `Division Name` — builds the full hierarchy

6. Click **Preview**, then **Commit**.

The importer automatically sets the group role to **author** for any non-camper
role. Campers in the same file become subjects; counselors become authors on
their respective bunks. You can mix both in one CSV.

---

## Option B — Import into one bunk at a time

Use this when the bunks and counselors already exist.

1. Go to **Admin → Assignment groups** (`/admin/groups`).
2. Open the target bunk.
3. Scroll to **Import roster from CSV**.
4. Set:
   - **Importer:** Campminder
   - **Import as:** **Author (observer)** — important for counselors
   - **Reconcile:** check to replace the bunk's counselor roster
5. Upload a Campminder staff export and click **Import**.

No `Bunk Name` column is needed—everyone joins the bunk you are viewing.

---

## Option C — Assignments UI (no CSV)

For a handful of counselors or quick fixes:

1. Go to **Admin → Assignments** (`/admin/assignments`).
2. Open the **Counselor → Bunk** tab.
3. Select your **program**.
4. Pick a **bunk** on the left.
5. Multi-select counselors on the right and assign.

This is best for small changes, not a full roster.

---

## What not to use

- **The "Staff" template** (People bulk import) imports people and roles but has
  **no `Bunk Name` column**, so it won't place anyone on a bunk.
- **Bulk import groups** (Groups list page) creates bunk/unit structure only.

---

## Working with raw Campminder staff exports

Staff exports from Campminder usually include `Position Types` and `Position` but
no bunk column. You have two choices:

- Add a `Bunk Name` column yourself in Excel/Sheets, then use Option A, or
- Import staff first (Staff template), then assign bunks via Option B or C.

---

## Related guides

- [Assigning campers to bunks](assign-campers-to-bunks.md)
- [Assigning Camper Care to caseloads](assign-camper-care-caseloads.md)

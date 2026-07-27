# Assigning Camper Care to caseloads

A Camper Care member's **caseload** is the set of **bunks they supervise**. The
caseload drives their dashboard (units → bunks → campers), flag workspace, and
which campers' reflections they can see.

> **Important:** the caseload that powers the Camper Care dashboard is a
> **bunk supervision** relationship, not the CSV `caseload_name` column. See
> [Caseload vs. the CSV caseload column](#caseload-vs-the-csv-caseload-column)
> below.

---

## Prerequisites

Each Camper Care person needs, in their program:

1. A **Person** record.
2. An active **Membership** with role `camper_care`.

If they aren't in the system yet, import them first via **Admin → People →
Bulk import** using the Campminder **Staff** template with `Role` set to
`camper_care`. (Position values like "Camper Care Associate" also infer the
`camper_care` role.)

The bunks must also already exist—see
[Assigning campers to bunks](assign-campers-to-bunks.md).

---

## Primary method — Assignments UI

**Admin → Assignments** (`/admin/assignments`) → **Camper Care → Caseload** tab.

1. Select your **program**.
2. On the left, pick a **bunk** to add to a caseload.
3. On the right, **multi-select** the Camper Care staff who should cover it.
4. Assign.

This creates `Supervision` rows (`target_type=BUNK`) linking each Camper Care
member to that bunk. Repeat for each bunk, or use the unit shortcut below.

Notes:

- **Overlapping caseloads are allowed.** Multiple Camper Care members can cover
  the same bunk, and it appears on each of their dashboards.
- You may see a **conflict warning** if someone already supervises the bunk—this
  is informational and does not block the assignment.
- There is currently **no CSV import** for bunk-caseload supervision.

---

## Shortcut — assign at the unit level

If a Camper Care member covers **every bunk in a unit**, don't assign
bunk-by-bunk:

1. Go to **Admin → Assignment groups** (`/admin/groups`).
2. Open the **unit**.
3. Use **Add member** → pick the Camper Care person → **Role in group: Author**.

The system expands that unit membership to all descendant bunks automatically,
using the same resolver the dashboard reads.

---

## Caseload vs. the CSV caseload column

The Campminder roster importer supports two optional columns:

- `caseload_name`
- `caseload_owner_campminder_id`

These create an `AssignmentGroup` of type `caseload` with the Camper Care person
as **author** and specific **campers** as **subjects**. That is useful for a
named wellness caseload of individual campers, but it is **not** the same as the
bunk supervision that populates the Camper Care dashboard.

For the dashboard caseload (units → bunks → campers), use the **Assignments →
Camper Care → Caseload** tab or unit-level author membership described above.

---

## Verify it worked

- **As the Camper Care member:** their **Camper Care dashboard** should show the
  assigned units/bunks with camper counts and reflection completion.
- **As an admin:** the **Assignments → Camper Care → Caseload** tab lists active
  supervisions per bunk.

---

## Related guides

- [Assigning campers to bunks](assign-campers-to-bunks.md)
- [Assigning counselors to bunks](assign-counselors-to-bunks.md)

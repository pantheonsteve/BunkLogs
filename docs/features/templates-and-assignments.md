# Templates & assignments

Published forms reach staff through **templates** (the form definition) and
**assignments** (who must or may fill them out, and when). Leadership Team and
admins manage both surfaces.

---

## Templates

A **template** defines:

- Form fields (ratings, text areas, flags, etc.)
- **Subject mode** — who each submission is about (see
  [Form types](form-types.md))
- **Cadence** — daily, weekly, biweekly, on demand, etc.
- **Role metadata** — which staff role the form is designed for
- **Group types** — which assignment groups apply (bunk, unit, classroom, …)

Templates move through three statuses:

| Status | Meaning |
|--------|---------|
| **Draft** | Editable; not visible to staff; not assignable |
| **Published** | Active; can be assigned; staff may see it in My Tasks when an assignment is active |
| **Archived** | Retired; no new assignments; existing responses remain readable |

Whether you **delete** or **archive** depends on whether anyone has submitted the
form yet—not on draft vs published status alone.

---

## Delete vs archive

The app uses one simple rule:

```text
No submissions yet  →  Delete (permanent)
Has submissions     →  Archive (retire, keep answers)
```

| Situation | What to do | What happens |
|-----------|------------|--------------|
| Draft you never published | **Delete** | Template row removed from the database |
| Published but **nobody filed it yet** | **Delete** | Template and its assignments are removed |
| Published or archived with **one or more submissions** | **Archive** (if not already) | Form hidden from new work; responses stay on dashboards and profiles |
| Archived with **zero submissions** | **Delete** | Cleanup—same as deleting an unused draft |

**Delete** is permanent. You cannot undo it. Associated **assignments** are removed
with the template (CASCADE). Use Delete for experiments, duplicates, and mistaken
publishes that never collected data.

**Archive** is the safe off-ramp once staff have used the form. Archived templates
no longer appear in My Tasks or assignment pickers, but supervisors can still
browse historical answers. See [Viewing form responses](viewing-responses.md).

### Where to delete or archive

**Template library** (`/admin/templates`):

- Each row shows action buttons based on status and whether responses exist.
- **Delete** appears when the template has **no responses** (`reflection_count`
  is zero). Click **Delete**, then confirm **Delete permanently?**
- **Archive** appears on **published** templates (use when responses exist).
- **Unpublish** appears on published templates **with no responses**—reverts to
  draft without deleting. Optional if you prefer to edit before deleting.

**Template builder** (`/admin/templates/:id`):

- **Delete** — top action bar when the template has no responses. Confirm with
  **Yes, delete**.
- **Archive** — top action bar on published templates.
- When responses exist, Delete is hidden and a hint explains: *Has responses —
  use Archive to retire this form.*

### Unpublish (published → draft)

**Unpublish** is only available when the template is **published** and has **no
responses**. It moves the template back to **draft** so you can keep editing or
publish again later—without removing the row.

If you unpublish a form that was already assigned, check **Admin → Assignments**
and cancel or adjust any active assignments so staff are not pointed at a draft.

### Step-by-step: remove a form nobody used

1. Open **Admin → Templates**.
2. Find the form (filter by status or role if needed).
3. If status is **published** and you see **Delete**, click it and confirm.
4. If you only see **Unpublish**, you can unpublish first, then delete from the
   draft row—or delete directly when the Delete button is shown.

### Step-by-step: retire a live form that has answers

1. Open the template in the builder or library.
2. Click **Archive** (not Delete).
3. Cancel or end-date active **assignments** under **Admin → Assignments** if
   staff should stop seeing the form immediately.
4. Historical responses remain on Bunk Logs, Reflections, group dashboards, and
   person profiles according to your access.

---

**Where to manage templates:**

- **Admin** → **Templates** (`/admin/templates`) — full library, routing
  settings, and WYSIWYG builder
- Leadership Team members with program-lead access use the same admin templates
  surface (legacy `/leadership-team/templates` URLs redirect here)

---

## Assignments

An **assignment** binds a published template to an audience for a date window.

| Field | What it controls |
|-------|------------------|
| **Target type** | Role, individuals, tag group, or assignment group |
| **Start / end dates** | When the form appears in My Tasks and dashboards |
| **Required** | Required forms count toward "all set"; optional forms land in a library |
| **Title** | Display label (falls back to template name) |

**Where to manage assignments:**

- **Admin** → **Assignments** (`/admin/assignments`)

Without an active assignment, staff will not see the form in **My Tasks**, and
supervisor dashboards show a "no template" empty state for that role.

---

## End-to-end workflow

1. **Create** a template (draft) in the template builder.
2. Set **subject mode**, cadence, and fields. See
   [Form types](form-types.md) if unsure which mode to pick.
3. **Publish** the template.
4. **Create an assignment** — pick the audience (e.g. all counselors), set
   start date to today or the program start, mark required if appropriate.
5. **Verify** as a test user: open **My Tasks** (`/tasks`) and confirm the form
   appears.
6. **Review responses** via Bunk Logs or Reflections depending on subject mode.
   See [Viewing form responses](viewing-responses.md).

---

## Common pitfalls

### Form does not appear in My Tasks

Check:

- Assignment **start date** is today or earlier (not tomorrow).
- Template is **published** and assignment is active.
- **Subject mode** matches how the user authors:
  - Self-reflection → user needs a membership in the assigned role.
  - Roster forms → user must be an **author** in an assignment group whose
    `group_type` matches the template's allowed group types.
- Assignment **target** includes that user (role, group, or individual).

### Form appears in wrong dashboard

- **Self** subject mode → **Reflections** dashboard (`/dashboards/reflections`)
- **About one person / several people / group** → **Bunk Logs** dashboard
  (`/dashboards/logs`)

A leadership self-reflection assigned with `single_subject` will not behave as
expected—use **Self-reflection** subject mode instead.

### "Role" on the template vs assignment audience

The template **role** field is metadata (which staff role the form is designed
for). The assignment **target** decides who actually receives the form. They
should align, but the assignment is what drives My Tasks.

### I don't see a Delete button

Delete only appears when **no one has submitted the form yet**. If counselors or
other staff have already filed answers, use **Archive** instead. The builder
shows *Has responses — use Archive to retire this form* in that case.

### I published the wrong form type (e.g. single_subject instead of self)

If nobody has submitted yet: **Delete** the template and create a new one with
the correct [form type](form-types.md), then publish and assign again.

If submissions already exist: **Archive** the old template, create and assign
the corrected form, and leave historical responses on the old template for
audit purposes.

### Delete failed with an error about responses

The API blocks delete once any Reflection row exists for that template, even if
you cannot see those responses in the UI (permissions, date filters, or test
data). Archive the template instead.

---

## Related guides

- [Form types (subject modes)](form-types.md)
- [Viewing form responses](viewing-responses.md)
- [Log Entries, Reflections, and Observations](logs-reflections-observations.md)
- [Concerns Inbox](concern-inbox.md) — triage worrying answers from completed forms

# Viewing form responses

After staff submit forms, supervisors and admins review answers through several
surfaces. The right entry point depends on the template's **subject mode**.

---

## Archived templates

**Archive** retires a form but does **not** remove submitted answers. You can
still review responses for archived templates from Bunk Logs, Reflections, or the
template **Responses** link—as long as you have supervisor access and the
assignment period you are viewing includes those submissions.

To remove a form entirely, use **Delete** only when no submissions exist. See
[Templates & assignments — Delete vs archive](templates-and-assignments.md#delete-vs-archive).

---

## Pick the right dashboard

| Template subject mode | Start here |
|-----------------------|------------|
| Self-reflection | **Reflections** → `/dashboards/reflections` |
| About one person, several people, or a group | **Bunk Logs** → `/dashboards/logs` |

Both dashboards use the same pattern:

1. Open the dashboard.
2. Choose **Active** or **Ended** assignments.
3. Filter by audience, program, or group if needed.
4. Click a form tile to open the **responses** view for that assignment.

See [Log Entries, Reflections, and Observations](logs-reflections-observations.md)
for why these are separate.

---

## From the template library

In **Admin → Templates** (`/admin/templates`):

1. Find the published template.
2. Use the **Responses** action (when available) to jump directly to submitted
   answers for that template.

This skips the assignment picker when you already know which form you need.

---

## Group dashboards

Open a **group dashboard** (`/dashboards/group/<group-id>`) to see template
response cards for log-style forms assigned to that bunk, unit, or classroom on
the selected date.

Use the date picker to change which day's submissions appear.

---

## Person profiles

On a **subject profile** (`/profile/<person-id>`):

- **Log-style** template responses appear in template response widgets (when you
  have access).
- **Self-reflections** appear in the self-reflection history section.
- **Observations** (freeform notes) appear in a separate Observations stream—not
  mixed with template responses.

---

## Concerns and triage

For cross-template triage of worrying answers (open concern text, ratings ≤ 1),
use the **Concerns Inbox** (`/dashboards/concerns`). That inbox mines completed
reflections; it does not replace browsing a specific form on Bunk Logs or
Reflections.

See [Concerns Inbox](concern-inbox.md).

---

## Coverage and completion

To see **who has not filed yet** (per bunk, per day):

- **Coverage dashboard** → `/dashboards/coverage`
- **Author attribution** → `/dashboards/authors`
- **Group performance** → `/groups/performance`

These complement the responses views—they show gaps, not full answer text.

---

## Quick URL reference

| Goal | URL |
|------|-----|
| Browse log-style forms | `/dashboards/logs` |
| Browse self-reflections | `/dashboards/reflections` |
| Triage flagged answers | `/dashboards/concerns` |
| Per-bunk daily cards | `/dashboards/group/<id>` |
| Per-person history | `/profile/<id>` |
| Manage templates | `/admin/templates` |
| Manage assignments | `/admin/assignments` |

---

## Related guides

- [Templates & assignments](templates-and-assignments.md)
- [Form types (subject modes)](form-types.md)
- [Log Entries, Reflections, and Observations](logs-reflections-observations.md)

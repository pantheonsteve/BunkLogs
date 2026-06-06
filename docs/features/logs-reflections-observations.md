# Log Entries, Reflections, and Observations

## What they are

BunkLogs uses three related but separate ways to capture staff input about
people and groups. They are easy to confuse because all three can appear on
dashboards and profiles, but each has a different purpose and a different place
in the app.

| Feature | What it is | Typical example |
|---------|------------|-----------------|
| **Log Entries** | Structured forms **assigned to a group** (bunk, unit, classroom, etc.). An **author** fills them out **about other people or the group**—not about themselves. | Counselor daily report about each camper in the bunk |
| **Reflections** | Structured **self-reflection** forms. The **subject writes about themselves** (author and subject are the same person). | Counselor end-of-day self-reflection |
| **Observations** | Freeform notes that permissioned staff write **about one or more people**. Not tied to a template. | Swim instructor notes behavior during class |

**Log Entries** and **Reflections** both produce **Reflection** records in the system
(one row per submission). **Observations** are a separate **Observation**
record with their own inbox, threading, and sensitivity rules.

---

## How to tell them apart

```text
Template assigned to a GROUP + about others/team  →  Log Entries dashboard
Template for SELF (person writes about self)      →  Reflections dashboard
Freeform note about tagged person(s)              →  Observations
```

| Question | Log Entries | Reflections | Observations |
|----------|-------------|---------------|--------------|
| Uses a published form template? | Yes | Yes | No |
| Who is it about? | Other people or a group | The author (self) | One or more tagged subjects |
| Where do supervisors browse assignments? | **Log Entries** (`/dashboards/logs`) | **Reflections** (`/dashboards/reflections`) | **Observations** (`/observations`) |
| Where do filled answers show on a person’s profile? | Template response widgets (when you have access) | Self-reflection history (when you have access) | **Observations** panel (chronological stream) |

For supervisor triage of worrying **answers inside completed forms**, use the
[Concerns Inbox](concern-inbox.md)—that is not the same as Observations.

---

## Log Entries

### What Log Entries are for

**Log Entries** are template-driven forms assigned to **groups** (for example a bunk).
Staff in the author role complete the form **about campers, peers, or the group
as a whole**—depending on how the template is configured.

Self-reflection templates (for example “Counselor daily self-reflection”) do
**not** appear on the Log Entries dashboard even if they were mistakenly assigned to a
bunk. Those belong under **Reflections**.

### Who can open the Log Entries dashboard

You need a **supervisor** role (unit head, leadership team, program lead, admin)
or an explicit dashboard grant. Plain counselors without supervision or a grant
see an empty list or an access message—not the bunk forms they author.

**URL:** `/dashboards/logs`

**Navigation:**

- Sidebar → **My work** → **Log Entries** (admins)
- Sidebar → **My work** or **Supervise** → **Log Entries** (supervisors and program leads)

### Using the Log Entries dashboard

1. Open **Log Entries**.
2. Choose **Active** or **Ended** assignments.
   - **Active** — assignments in effect on today’s date (you can change the
     effective date when you open a form’s responses).
   - **Ended** — assignments whose lifecycle status is ended (historical review).
3. Optionally filter by **Audience**, **Program**, or **Group**.
4. Click a **form tile** to open that template’s responses (Leadership Team
   responses view), scoped to the date in the link.

From there you can review completion, read individual submissions, and use the
same response tools as other template dashboards (tables, ratings, trends)—for
**that log template only**.

### Log Entries on a group dashboard

When you open a **group dashboard** (for example `/dashboards/group/<bunk-id>`),
you also see **template response cards** for log-style forms assigned to that
group on the selected date. Those cards show submitted reflections for that bunk
(or unit, classroom, etc.) on that day.

Self-reflection templates are **not** shown in that template section.

---

## Reflections

### What Reflections are for

**Reflections** are **self-reflection** templates: the person filling out the
form is writing **about themselves**. Examples include counselor daily
self-reflection, kitchen staff check-in, unit head reflection, or leadership
team reflection.

Assignments may target a **role** (all kitchen staff), **individuals**, a
**tag group**, or sometimes a **group** context—but the dashboard still lists
them here because `subject_mode` is **self**, not because they are “logs about
the bunk.”

### Who can open the Reflections dashboard

- **Supervisors** see reflections for roles and groups they supervise.
- **Staff** see their **own** self-reflection assignments (for example a
  counselor sees counselor self-reflection even without a supervisor dashboard).
- **Admins** see all assignments in the organization.

**URL:** `/dashboards/reflections`

**Navigation:**

- Sidebar → **My work** → **Reflections** (admins, counselors, and others who file
  reflections)
- Sidebar → **Supervise** → **Reflections** (program leads)

### Using the Reflections dashboard

The flow matches **Log Entries**: **Active** / **Ended** tabs, audience/program/group
filters, then click a form tile to open responses.

To **file** your own reflection (not only browse others’), use:

- Sidebar → **My work** → **File a reflection** (`/reflect`)
- Sidebar → **My work** → **My reflections** (`/my-reflections`)

### Reflections vs Concerns Inbox

When a self-reflection includes an “open concern” or very low rating field,
supervisors may see a signal in the [Concerns Inbox](concern-inbox.md). That
inbox mines **completed reflections**; it does not replace the Reflections
dashboard for browsing a specific form type.

---

## Observations

### What Observations are for

An **Observation** is a **freeform note** about one or more people. Use it when
there is no template for the situation—for example a specialist watching a
camper at swim, a peer note, or a quick supervisor comment.

Observations support:

- **One or more subjects** (who the note is about)
- **Optional recipients** (who should be notified in the Observations inbox)
- **Sensitivity** (who can read the note based on role)
- **Optional context tag** (for example `swim_instruction`)
- **Threaded replies** (like a short conversation)
- **When it happened** — date and time, including **back-dating** if you are
  writing after the fact

### Who can create and read Observations

**Creating:** You can only write about people you are allowed to author
observations for (typically people in groups you work with or supervise).

**Reading:** You can read an observation if you are:

- The **author**
- An explicitly **tagged recipient**, or
- A supervisor whose role **covers at least one tagged subject**, and your role
  clears the note’s **sensitivity** level

Tagged subjects do **not** automatically see every observation about them. The
author must check **Make visible to the subject on their Profile** for the
subject to see that note on their own profile (and only when other rules allow).

### Observations inbox

**URL:** `/observations`

**Navigation:** Sidebar → **My work** → **Observations** (unread count badge when
applicable). Also linked from **Supervise** for program leads.

**Inbox** — observations addressed to you, plus observations you wrote that
received a reply from someone else.

**Sent** — observations you authored that have not yet drawn an inbound reply.

Use search and sort (newest, oldest, unread first) to work through the list.
Open a row to read the full thread, reply, or archive it for yourself.

### Writing an observation

1. Go to **Observations** and click **Compose**, or use **+ Add observation** on
   a person’s profile.
2. **About** — search and add one or more subjects (required).
3. **Observation** — write the note (required).
4. **When did this happen?** — defaults to now; change this to **back-date** if
   the event was earlier. Future dates are not allowed.
5. **Context tag** — optional short label (for example `swim_instruction`).
6. **Sensitivity** — controls who can be notified and who can read via hierarchy:
   - **Normal** — Everyone
   - **Sensitive** — Unit Heads and above
   - **Domain** — Leadership Team and above
   - **Confidential** — Pro Team only
7. **Notify** — optional checkboxes; only people who clear the selected
   sensitivity tier appear.
8. **Make visible to the subject on their Profile** — optional; lets the
   subject see this note on their own profile when they view it.

After you save, you are taken to the observation thread. Recipients see it in
their inbox; supervisors with access see it on subject profiles and group
dashboards as described below.

### Where observations appear

| Place | What you see |
|-------|----------------|
| **Subject profile** (`/dashboards/subject/<person-id>`) | Chronological **Observations** stream for that person (newest by *when it happened*). Only notes you are allowed to read. |
| **Bunk group dashboard** (`/dashboards/group/<bunk-id>`) | **Notes** section → **Observations** column: observations about campers in that bunk whose **observed** date matches the dashboard date picker. |
| **Observations inbox** | Cross-person list for triage and replies |

Changing the **date** on a group dashboard changes which observations appear in
that column—based on **when the event happened**, not when the note was saved.

### Amendments and archives

- **Replies** add to the thread; they cannot be edited after posting.
- **Amendments** (author or admin) create a new linked observation; the original
  stays immutable.
- **Archive** hides a thread from your inbox only; it does not delete the
  observation for others.

---

## Quick reference: URLs and navigation

| Feature | URL | Primary navigation |
|---------|-----|-------------------|
| Log Entries | `/dashboards/logs` | My work → Log Entries; Supervise → Log Entries (program leads) |
| Reflections | `/dashboards/reflections` | My work → Reflections; Supervise → Reflections (program leads) |
| File a reflection | `/reflect` | My work → File a reflection |
| My reflections | `/my-reflections` | My work → My reflections |
| Observations | `/observations` | My work → Observations |
| Subject profile | `/dashboards/subject/<id>` | From dashboards, roster, inbox links |
| Group dashboard | `/dashboards/group/<id>` | Dashboards, unit head / counselor flows |
| Concerns Inbox | `/dashboards/concerns` | Supervise → Concerns inbox |

---

## Related features

| Feature | Relationship |
|---------|----------------|
| [Concerns Inbox](concern-inbox.md) | Flags from **completed reflection forms** (open concern text, ratings ≤ 1). Not Observations. |
| **Template / group performance dashboards** | Per-template analytics for log-style forms; different scope than Log Entries picker. |
| **Bunk concerns** (unit head / camper care) | Optional bunk references on **self-reflections**; separate from Observations. |
| **Legacy Bunk logs** (Crane Lake) | Old single-tenant bunk log product; not the new Log Entries dashboard. |

---

## Access and empty states

If you open **Log Entries** or **Reflections** without permission, you may see
*Access restricted* and a link back to your home dashboard.

An **empty** Log Entries or Reflections list usually means no assignments match your
filters, your role cannot see those assignments, or nothing is active on the
selected tab—not that the product has no forms.

An **empty** Observations list on a profile means no readable observations for
that person yet, or none on the selected day on a bunk dashboard.

If something looks missing, check: correct **organization** context, **date**
(on group dashboards), **sensitivity**, and whether the form is categorized as
**Log Entries** vs **Reflections** vs a freeform **Observation**.

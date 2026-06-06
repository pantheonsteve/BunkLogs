# Concerns Inbox

## What it is

The **Concerns Inbox** is a supervisor triage queue. It gathers signals from
completed reflection forms across your organization and shows them in one place
so you can review, follow up, and clear items from *your* view when you are done.

The inbox does **not** create separate "concern" records. Each row is extracted
from an existing **Reflection** at load time based on how the form was answered
and how the template is configured.

**URL:** `/dashboards/concerns`

**Navigation:** Sidebar → **Supervise** → **Concerns inbox** (labeled **Concerns
about my unit** for unit heads with a narrower dashboard set). Also reachable
from **Dashboards** → **Overview** → **Concerns inbox** card.

---

## Who should use it

The inbox is built for people who supervise staff and need to spot problems
early:

- Unit heads
- Leadership team
- Program leads and admins
- Wellness / camper-care supervisors (when their visibility includes the
  underlying reflections)

What you see is always limited to reflections you are **allowed to read** under
BunkLogs visibility rules. You will not see private leadership self-reflections
meant for admins only, sensitive specialist notes outside your role, or
reflections about people outside your assignment scope.

If you open the page without organization context, you may see: *"You do not
have permission to view the concerns inbox."*

---

## What appears in the inbox

Each inbox item comes from one **completed** reflection whose **period end**
falls inside your selected date range. Draft or incomplete submissions never
appear.

There are two kinds of items:

### Open concern (amber badge)

A free-text answer on a field the template author marked as an **open concern**.

Typical prompts include:

- Counselor self-reflection: *"Anything you want to flag for your team?"*
- Leadership team self-reflection: *"Anything you want to share with your peers
  or administration?"*
- Madrich reflection: *"One question or concern for your Director"*

**Rules:**

- The field must be `text` or `textarea` with `dashboard_role: open_concern` in
  the template schema.
- The answer must be **non-empty** after trimming whitespace.
- Text is shown in the inbox (truncated server-side to 1,000 characters).

### Low rating (rose badge)

A numeric score at or below **1** on a rated field.

**Rules:**

- **Primary rating:** a `single_rating` field tagged
  `dashboard_role: primary_rating` with value ≤ 1 (for example counselor "How
  did today feel overall?" on a 1–5 scale).
- **Category ratings:** any category inside a `rating_group` that scores ≤ 1.
  Each low category becomes its own inbox row (field key like `pulse__morale`).

Ratings of 2 or higher do **not** appear in the inbox, even if they feel "low"
on a 1–5 scale.

---

## What each row shows

For every item you get:

| Information | Purpose |
|-------------|---------|
| **Kind badge** | Open concern vs low rating |
| **Privacy chip** | Whether the reflection is team-visible or supervisors-only |
| **Date** | Reflection period end |
| **Template name** | Which form produced the signal |
| **Assignment group** | Bunk, unit, or other group when applicable |
| **Author** | Who filed the reflection |
| **Subject** | Person the reflection is about (link to profile when available) |
| **Field label** | Which question triggered the item |
| **Value** | Full concern text, or the numeric rating |
| **Open reflection** | Link to the full read-only reflection |

---

## How to use the inbox

### Set your date window

- **Default:** last 14 days (ending today).
- **Maximum span:** 60 days (the server clamps wider ranges).
- Use **From** / **To** date pickers, then **Refresh** (the page also reloads
  when you change dates or the "Show read items" checkbox).

Items are filtered by the reflection's **period end**, not submission time.

### Triage unread items

By default you only see items you have **not** marked read.

1. Read the concern text or rating.
2. Use **Open reflection** for full context (author, all answers, visibility).
3. Click the subject name to open their **Subject** dashboard for trends and
   history.
4. Click **Mark read** when you have handled it—or select several rows with the
   checkboxes and use **Mark N as read** to clear a batch at once.

### Bulk mark read

Each row has a checkbox. Use **Select all** to select every item in the current
list, or pick individual rows. When at least one item is selected, a toolbar
appears with **Mark N as read**. With **Show read items** enabled, you can also
**Mark N as unread** on selected read rows.

Read state is **personal**: marking read hides the item from *your* default view
only. Other supervisors still see it until they mark it read themselves.

### Review cleared items

Check **Show read items** to include previously read rows. Read rows appear
slightly faded. Use **Mark unread** to bring an item back into your active queue.

### When the inbox is empty

You may see: *"No concerns in this window. Nice work!"* That means no qualifying
answers exist in the date range among reflections you can see—or you have marked
everything read and "Show read items" is off.

---

## Where concerns come from (staff perspective)

Concerns enter the inbox when staff **complete** reflection forms that include
the right template fields.

Template builders tag fields with a **dashboard role** (configured in the
template schema, often via the Field Key registry):

| Dashboard role | Field types | Inbox behavior |
|----------------|-------------|----------------|
| `open_concern` | `text`, `textarea` | Non-empty answer → open concern item |
| `primary_rating` | `single_rating` | Value ≤ 1 → low rating item |
| `category_ratings` | `rating_group` | Any category ≤ 1 → low rating item (per category) |

Staff do not "send to the concerns inbox" as a separate action. Filling the form
normally is enough.

**Visibility at write time** still applies: a counselors-only flag shows a
supervisors-only chip in the inbox; viewers without access never receive that
reflection in the API response.

---

## Related features (not the same as the inbox)

BunkLogs surfaces "concerning" information in several places. They overlap in
theme but serve different jobs:

| Feature | Where | What it shows |
|---------|--------|----------------|
| **Concerns Inbox** | `/dashboards/concerns` | Cross-template queue: open concerns + ratings ≤ 1; personal read/unread |
| **Template dashboard — Concern queue widget** | Per-template dashboard (e.g. group performance) | Open-concern text for *that template only* in the selected period |
| **Subject dashboard — Concerning patterns** | Person profile / subject detail | Low ratings in the last 14 days **plus** downward rating trends (different rules than the inbox) |
| **Bunk concerns (Unit Head / Camper Care)** | Unit Head bunk dashboard, bunk dashboard notes | Optional multi-select of bunks + note on **self-reflection**; separate from `open_concern` inbox mining |
| **Observations** | `/observations`, subject profile | Freeform notes about people; not mined into this inbox. See [logs-reflections-observations.md](logs-reflections-observations.md). |
| **Notes platform** (legacy) | Retired in favor of Observations | — |

Use the **Concerns Inbox** when you want one org-wide triage list. Use **Subject**
and **Template** views when you are already focused on one person or one form
type.

---

## Privacy and access

- **Server-side filtering:** The API only returns reflections you may view,
  including sensitive-content and private LT self-reflection rules.
- **No notifications (today):** The inbox updates when you load or refresh the
  page. Email or push alerts when a new concern is filed are not part of this
  feature yet.
- **Mark read does not delete data:** It only records that *you* dismissed the
  item from your default list. The underlying reflection remains unchanged.
- **Mark read security:** You cannot mark a reflection read if you cannot see
  that reflection (the server returns 404).

See also: [Visibility model](../user_stories/00_cross_cutting/visibility_model.md).

---

## Typical workflows

### Unit head — morning check

1. Open **Concerns about my unit**.
2. Leave the default 14-day window (or narrow to yesterday–today during camp).
3. Scan amber **Open concern** rows from counselor self-reflections.
4. Open the reflection, then the camper profile if the concern names a camper
   issue.
5. Mark read after you have talked to the counselor or logged a follow-up (Note
   thread if you need a back-and-forth).

### Leadership / admin — cross-program triage

1. Open **Concerns inbox** from the Dashboards hub.
2. Widen the date range if needed (up to 60 days).
3. Sort mentally by template and assignment group labels on each row.
4. Use **Show read items** during handoffs so the next supervisor sees what was
   already reviewed.

### Wellness — low ratings on camper reflections

Low ratings on **camper** observation forms (not self-reflection) appear when
your role can see those reflections. Treat them like any other inbox row;
cross-check the subject trend grid for pattern vs one-off.

---

## Limits and edge cases

| Situation | Behavior |
|-----------|----------|
| Whitespace-only concern text | Not listed |
| Rating of 2 on a 1–5 scale | Not listed (only ≤ 1) |
| Incomplete / draft reflection | Not listed |
| `day_off` shortcut self-reflection | No concern fields answered → nothing from that submission |
| Multiple low categories in one `rating_group` | Multiple inbox rows, one per category |
| Same reflection, concern + low rating | Two rows (different field keys) |
| Very long concern text | Truncated to 1,000 characters in the inbox; full text on **Open reflection** |
| Date range inverted (end before start) | Server swaps start/end |
| Range longer than 60 days | Server shortens to the last 60 days ending on `date_end` |

---

## For template administrators

To make a new question feed the Concerns Inbox:

1. Add a field to the reflection template schema.
2. Set `dashboard_role` to `open_concern` (text areas) or `primary_rating` / use
   a `rating_group` for scores.
3. Register the field key in the Field Key registry when your org uses it
   (expected key `open_concern` for the standard concern textarea).
4. Publish the template; only **completed** submissions after staff start using
   the field will produce inbox items.

The validator allows only one field per `dashboard_role` per template.

---

## FAQ

**Does marking read notify the author?**  
No. It is only your personal triage state.

**If I mark read, does the concern disappear for everyone?**  
No. Other supervisors have their own read state.

**Why don't I see a concern I know was submitted?**  
Common reasons: outside your date window, reflection not marked complete, you
lack visibility, answer was blank, or rating was above 1.

**Is this the same as "bunk concerns" on the Unit Head dashboard?**  
No. Bunk concerns come from Unit Head / Camper Care self-reflection fields that
flag specific bunks. The Concerns Inbox mines `open_concern` and low **ratings**
across eligible reflections.

**Will I get an email when a new concern is filed?**  
Not in the current release. Refresh the inbox or rely on related dashboards
during your shift.

---

## Technical reference

For API endpoints, `ConcernReadState`, and implementation details, see the
[Concerns Inbox section in `docs/dashboards.md`](../dashboards.md#concerns-inbox).

# 4_9 — Role Homepages: Madrich, Faculty, Director

**Wave:** 4 (TBE Fall 2026)
**Branch:** `prompt-4.9-role-homepages`
**Depends on:** `4_7_availability_calendar`, `4_8_challenge_log`, Wave 1 `TemplateAssignment` substrate
**Estimated scope:** large — expect to split into 4.9a (data + API), 4.9b (Madrich UI), 4.9c (Faculty UI), 4.9d (Director UI)

Build the three authenticated landing experiences for TBE: the Madrich homepage, the Faculty homepage, and the Director homepage. These are the primary surfaces every user sees on login; everything else in the app is reached from them.

---

## 0. Pre-flight audit — do this BEFORE writing any code

Read the codebase and report findings. Do not begin implementation until the audit is reported and any conflicts are resolved.

1. **Observations model.** Locate the converged `Observations` model (post `7_23`/`7_24`). Report: does it already carry a comment/reply trail, or is it flat? If it has a threading pattern, this prompt reuses that pattern rather than inventing a new one. Report the exact field names and any existing read/unread tracking.
2. **Rating chart component.** Find the component that renders rating trends on the CLC camper profile page. Report its path, props, and whether it can be driven by an arbitrary series without modification. Reuse it. Do not write a second chart component.
3. **Cohort semantics.** Confirm whether `AssignmentGroup` is the correct model for a TBE cohort (a Madrich's classroom or grade-level group). Report how a Madrich is currently associated with a classroom and with a supervising faculty member. If no faculty↔Madrich link exists, flag it — this prompt depends on it and it may need to land first.
4. **Availability calendar.** Report the model and API shipped by `4_7` for Sunday commitments, including field names for status values.
5. **Challenge log.** Report the model and API shipped by `4_8`, and whether its response mechanism can be expressed as the generic thread defined in §2 or is genuinely separate.
6. **Template assignment.** Confirm how `TemplateAssignment` resolves "which reflections is this Person assigned right now," and whether it exposes a due/period concept the homepage can render.
7. **Existing route structure.** Report the current React routing and role-gating pattern, and where a role-aware `/` landing redirect would live.

Output the audit as a markdown block before proceeding.

---

## 1. Global conventions

**Mobile-first, non-negotiable.** Design at 375px, then adapt up. Madrichim are teenagers on phones; that is the primary device. Tablet and laptop must look intentional, not like a stretched phone layout — at ≥1024px use a two-column layout, not a single centered column of full-width cards.

- Breakpoints: mobile `<640`, tablet `640–1023`, desktop `≥1024`. Use existing Tailwind config; do not add custom breakpoints.
- All homepage sections are **cards** rendered by a single shared `<HomeCard>` component: title, optional action link, optional unread badge, body, empty state. Every section on all three pages uses it.
- **Unread indicator:** a single shared `<UnreadDot count={n} />`. Appears on a card header (aggregate) and on individual list rows.
- Every list has an explicit empty state with copy appropriate to the role. Never render a bare empty card.
- Loading: skeleton placeholders per card, not a full-page spinner. Cards load independently; one slow endpoint must not block the page.
- **Touch targets** ≥44px. Rating inputs and attendance toggles are buttons, never sliders or dropdowns.
- **Localization:** all user-facing prompt text comes from `ReflectionTemplate.schema` localized dicts. Chrome/UI strings go through the existing i18n mechanism. TBE ships English-only, but no string is hardcoded in a way that blocks Spanish.
- Accessibility: semantic headings, keyboard-reachable cards, `aria-live` on the unread counts, sufficient contrast on chart colors.

**Color use:** the attendance calendar and rating trends should be genuinely colorful and legible at a glance. Use a consistent status palette across all three pages so a color means the same thing everywhere:

| Meaning | Use |
|---|---|
| Committed / complete / on track | green |
| Pending / not yet submitted / awaiting response | amber |
| Declined / missed / overdue | red |
| Informational / neutral | slate |

---

## 2. Data model additions

All new models live in `core`, carry `organization`, and use `OrgScopedManager` with an `all_objects` escape hatch, consistent with existing models.

### 2.1 Schema flags on `ReflectionTemplate` fields

No migration — these are additive keys inside the existing `schema` JSON. Update `docs/reflection-template-schema.md` and the schema validator to accept and validate them.

```json
{
  "key": "wins",
  "type": "text_list",
  "min_items": 3,
  "max_items": 3,
  "thread_enabled": true,
  "thread_scope": "item",
  "routes_to": null,
  "share_with_cohort": false,
  "prompts": { "en": "Three wins from this week" }
}
```

| Flag | Values | Effect |
|---|---|---|
| `thread_enabled` | bool, default `false` | Entry gets a comment thread and appears in the Madrich's expandable widgets |
| `thread_scope` | `"item"` \| `"field"`, default `"field"` | For `text_list`, whether each list item threads separately or the whole answer does |
| `routes_to` | `null` \| `"faculty"` \| `"director"` \| `"both"` | Puts the entry in that role's response queue. Requires `thread_enabled` |
| `share_with_cohort` | bool, default `false` | Publishes the entry to the cohort feed on submit |
| `trend_key` | string, `rating_group` fields only | Stable key for the trend series; defaults to field `key` |

Validation: `routes_to` set with `thread_enabled: false` is an error. `share_with_cohort` on a `rating_group` is an error.

TBE's `madrich_weekly` template updates to: `wins` → `thread_enabled`, `thread_scope: item`; `improvements` → `thread_enabled`, `thread_scope: item`; `question_or_concern` → `thread_enabled`, `routes_to: "director"`; new optional `shared_idea` field → `share_with_cohort: true`, `thread_enabled: true`.

### 2.2 `EntryThread`

A conversation attached to exactly one subject.

```python
class EntryThread(models.Model):
    organization = FK(Organization, CASCADE, related_name='entry_threads')
    program = FK(Program, CASCADE, related_name='entry_threads')

    reflection = FK(Reflection, null=True, blank=True, on_delete=CASCADE, related_name='threads')
    field_key = CharField(max_length=64, blank=True)
    item_index = IntegerField(null=True, blank=True)  # null when thread_scope == "field"

    cohort_share = FK('CohortShare', null=True, blank=True, on_delete=CASCADE, related_name='threads')

    subject_person = FK(Person, CASCADE, related_name='threads_about_me')  # whose entry this is
    routes_to = CharField(max_length=16, blank=True)  # snapshot of the schema flag at submit time
    resolved_at = DateTimeField(null=True, blank=True)

    created_at = DateTimeField(auto_now_add=True)
    last_message_at = DateTimeField(null=True, blank=True)
```

Constraints:
- DB `CheckConstraint`: exactly one of `reflection`, `cohort_share` is non-null.
- `UniqueConstraint` on `(reflection, field_key, item_index)` where `reflection` is not null.
- Index on `(organization, program, routes_to, resolved_at)` — this drives the response queues.
- Index on `(subject_person, last_message_at)`.

`routes_to` is snapshotted rather than read live from the template, so editing a template does not retroactively reroute existing open items.

### 2.3 `ThreadMessage`

```python
class ThreadMessage(models.Model):
    thread = FK(EntryThread, CASCADE, related_name='messages')
    author = FK(Person, PROTECT, related_name='thread_messages')
    author_role = CharField(max_length=32)  # snapshot of Membership.role at write time
    body = TextField()
    created_at = DateTimeField(auto_now_add=True)
    edited_at = DateTimeField(null=True, blank=True)
```

- Saving a message updates `thread.last_message_at`.
- A message authored by `thread.subject_person` renders as a self-update ("Update on November 12: …"), styled distinctly from a supervisor reply. This is a rendering distinction only — no separate model.
- Editing allowed by the author within 15 minutes; after that, immutable. No deletes in Tier 1.

### 2.4 `ThreadRead`

```python
class ThreadRead(models.Model):
    thread = FK(EntryThread, CASCADE, related_name='reads')
    person = FK(Person, CASCADE, related_name='thread_reads')
    last_read_at = DateTimeField()

    class Meta:
        unique_together = [('thread', 'person')]
```

Unread = `thread.last_message_at > read.last_read_at`, or no `ThreadRead` row and at least one message not authored by that person. This single rule powers every indicator on all three pages.

### 2.5 `CohortShare`

```python
class CohortShare(models.Model):
    organization = FK(Organization, CASCADE)
    program = FK(Program, CASCADE)
    assignment_group = FK(AssignmentGroup, null=True, blank=True, on_delete=SET_NULL,
                          related_name='cohort_shares')  # null = program-wide feed
    person = FK(Person, CASCADE, related_name='cohort_shares')
    reflection = FK(Reflection, CASCADE, related_name='cohort_shares')
    field_key = CharField(max_length=64)
    item_index = IntegerField(null=True, blank=True)
    body = TextField()  # snapshot at submit time
    is_hidden = BooleanField(default=False)  # director moderation
    created_at = DateTimeField(auto_now_add=True)
```

Created automatically on reflection submit for any field with `share_with_cohort: true` and a non-empty answer. Editing the reflection updates the snapshot; the share is never orphaned from its reflection.

Confirm cohort resolution in the audit: a Madrich's cohort is their `AssignmentGroup`. If a Madrich belongs to multiple groups, the feed is the union, deduplicated.

### 2.6 `ShareReaction`

```python
class ShareReaction(models.Model):
    cohort_share = FK(CohortShare, CASCADE, related_name='reactions')
    person = FK(Person, CASCADE, related_name='share_reactions')
    kind = CharField(max_length=16, default='like')
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('cohort_share', 'person', 'kind')]
```

Tier 1 ships `like` only. The `kind` field exists so adding reactions later is not a migration of user data.

---

## 3. API

All under `/api/v1/`. All org-scoped and fail-closed. All list endpoints paginated.

### Shared

| Method | Path | Notes |
|---|---|---|
| GET | `/threads/` | Filters: `routes_to`, `resolved`, `subject_person`, `assignment_group`, `unread=true`. Returns thread + subject entry snapshot + last message preview + unread flag |
| GET | `/threads/{id}/` | Full message list |
| POST | `/threads/{id}/messages/` | Body: `{ body }`. Author from request user's Person |
| POST | `/threads/{id}/read/` | Marks read; upserts `ThreadRead` |
| POST | `/threads/{id}/resolve/` | Director/faculty only. Sets `resolved_at` |
| GET | `/cohort/feed/` | Cohort shares visible to caller, newest first, with reaction counts, `liked_by_me`, comment count |
| POST | `/cohort/shares/{id}/react/` | Toggle like |
| GET | `/cohort/members/` | Persons in caller's cohort(s): name, grade level, avatar/initials |

### Madrich

| Method | Path | Notes |
|---|---|---|
| GET | `/home/madrich/` | Single composed payload for above-the-fold: next 4 Sundays commitment status, open assigned reflections count, unread thread count, last 3 entries per threaded field, available rating trend keys |
| GET | `/reflections/assigned/` | Open assignments with period and due date |
| GET | `/reflections/mine/` | Past submissions, newest first, with thumbnail summary (period, template name, completion) |
| GET | `/me/entries/?field_key=wins` | Reverse-chron list of that field's entries across all reflections, each with date, excerpt, thread unread flag |
| GET | `/me/trends/` | All rating series for the caller: `[{ trend_key, label, scale, points: [{date, value}] }]` |

### Faculty

| Method | Path | Notes |
|---|---|---|
| GET | `/home/faculty/` | Composed payload: response queue count, roster status summary, upcoming-Sunday coverage for their classroom(s), unanswered challenge-log count |
| GET | `/faculty/roster/` | Madrichim supervised by caller, each with: this-period reflection status, next-Sunday commitment, open threads count, last activity date |
| GET | `/faculty/roster/{person_id}/` | Drill-in: reflection history, trend series, observations, threads |
| GET | `/faculty/coverage/` | Next 4 Sundays × their classroom(s): committed / pending / declined counts and names |

### Director

| Method | Path | Notes |
|---|---|---|
| GET | `/home/director/` | Composed payload: program pulse metrics, question queue count, coverage gaps, faculty responsiveness summary |
| GET | `/director/pulse/` | Completion rate this period + prior 8 periods, active Madrichim count, submission trend |
| GET | `/director/coverage/` | Next 6 Sundays × all classrooms, flagged where committed < required |
| GET | `/director/faculty-activity/` | Per faculty: assigned Madrichim, open threads, median response latency, oldest unanswered item age |
| GET | `/director/themes/` | Aggregated anonymized reflection themes (Growth Dashboard feed) |
| GET | `/director/export/` | CSV export, filters by grade/period/template |

**Performance:** each `/home/{role}/` endpoint must resolve in a bounded number of queries. Write the query counts into the tests using `assertNumQueries`. No N+1 across roster rows.

---

## 4. Madrich homepage

Route `/` when the active membership role is `madrich`. Section order on mobile is the order below; on desktop, left column = Attendance, Reflections, Cohort; right column = Wins, Improvements, Questions, Trends.

### 4.1 Attendance (Sunday commitments)

- Shows the next 4 Sundays as a colorful horizontal strip (mobile: scrollable row of date chips; desktop: inline calendar row).
- Each Sunday chip: date, status color (committed / pending / declined), and a one-tap toggle inline. Toggling writes immediately and shows an optimistic state with rollback on failure.
- "Update my availability" link opens the full calendar view from `4_7`, which returns to the homepage on save.
- If any Sunday inside the two-week commitment window is still pending, the card header shows an amber badge.

### 4.2 Reflections

- Card shows count of open assigned reflections with a prominent CTA to the first one.
- "My reflections" link → list view: past submissions as thumbnails (period label, template name, submitted date, small completion indicator), newest first, infinite scroll.
- Tapping a thumbnail opens the expanded Reflection page: full answers, read-only, with each threaded entry showing its comment trail inline and an unread dot if there's a new reply.

### 4.3 Wins / Areas of Improvement / Questions for the Director

Three cards, rendered from the **same component** driven by `field_key` — do not write three components. Any threaded field on any assigned template gets a card automatically; card titles come from the template's localized prompt.

- Each card lists the most recent 3 entries: date + excerpt (2 lines, truncated) + unread dot if the thread has new activity.
- "View all" → full reverse-chron list for that field with dates.
- Tapping an entry opens the **Entry detail** view: the full entry text, its date, then the thread below it in chronological order.
- Thread rendering: supervisor messages and self-updates visually distinct (alignment or accent color, plus role label and date). Composer at the bottom, always available to the Madrich for self-updates.
- Opening the entry marks the thread read.
- The Questions card additionally shows a small "awaiting reply" state on entries where `routes_to='director'` and no non-author message exists yet, so a teen isn't left wondering whether it went anywhere.

### 4.4 Rating trends

- One chart per `rating_group` field across all assigned templates, discovered dynamically via `trend_key` — never hardcode the five TBE categories.
- Line chart over submission dates, y-axis pinned to the field's declared scale (e.g. 1–4) so a flat line reads as flat, not as noise.
- Each chart is its own small card with the category label; mobile shows one per row, desktop two per row.
- Fewer than 2 data points → show the single value with a "trend appears after your second reflection" empty state rather than a broken chart.

### 4.5 My Cohort

- Member list: other Madrichim in the caller's cohort(s), name + grade, compact avatars/initials.
- Feed: cohort shares newest-first, each with author name, date, body, like button with count, comment count.
- Tapping a post expands its thread; commenting uses the same thread composer as everywhere else.
- Own posts appear in the feed and are likeable by others but not self-likeable.
- Empty feed state should invite the first post rather than reading as broken.

---

## 5. Faculty homepage

Route `/` when active role is `faculty`. Faculty are classroom teachers supervising Madrichim. This page is a work surface: the top of it is always "what needs me."

### 5.1 Needs my response (primary card, top of page)

- Queue of open threads where `routes_to` is `faculty` or `both`, or where the Madrich has posted a self-update the faculty member hasn't read, scoped to their supervised Madrichim.
- Each row: Madrich name, field label ("Win", "Area to improve"), entry excerpt, age of the item ("4 days ago"), unread dot.
- **Sort by age ascending — oldest first.** The failure mode here is a teen's entry going unanswered for three weeks; the UI should make that impossible to miss. Items older than 7 days render with the amber accent, older than 14 with red.
- Tapping opens the entry detail with composer focused. Replying updates the row in place; the row leaves the queue when the faculty member replies or resolves.
- Header badge shows total open count.

### 5.2 My classroom

- Roster of supervised Madrichim. Each row: name, grade, this-period reflection status (submitted green / not yet amber / overdue red), next Sunday commitment status, open thread count.
- Row tap → Madrich detail: reflection history, their rating trend charts (same components as §4.4), observations about them, and all threads.
- Sort/filter by status so a teacher can pull up "who hasn't submitted" in one tap.

### 5.3 Upcoming Sundays

- Next 4 Sundays for their classroom(s): committed count vs expected, with names on expand.
- Amber when a Sunday inside the commitment window is under-committed; red when it's short with less than one week to go.
- Read-only from faculty; the fix lives with the Director and the Madrichim, so link to the Director's coverage view rather than exposing edit controls here.

### 5.4 Observations

- Quick-entry composer to record an observation about a specific Madrich, reusing the existing `Observations` model and its permissions.
- Recent observations list with the same expand/thread affordance used elsewhere.

### 5.5 Challenge log

- Compose a classroom challenge (semi-anonymous per `4_8`).
- Feed of peer challenges and faculty responses — the peer learning library. Unanswered challenges surface first.
- If `4_8`'s response mechanism can be expressed as `EntryThread` with `cohort_share`-like semantics, converge them; report the recommendation in the audit rather than deciding silently.

### 5.6 Program themes (read-only)

- Compact view of the Growth Dashboard: aggregated, anonymized reflection themes across cohorts. Read-only for faculty; no drill-down to individual Madrichim outside their own roster.

---

## 6. Director homepage

Route `/` when active role is `admin`. Do **not** introduce a `director` role — Director is the admin capability layer scoped to a TBE program. Confirm this in the audit; if a distinct role is genuinely required, flag it before implementing.

### 6.1 Program pulse (top card)

Four headline numbers with sparkline or trend arrow versus prior period:
- Completion rate this period (submitted / assigned)
- Active Madrichim
- Open items awaiting an adult response, program-wide
- Sundays in the next 6 weeks that are under-committed

Each number is a link into the relevant detail view. Numbers that are not links are decoration; make all four navigate.

### 6.2 Questions for the Director

- Queue of threads with `routes_to` in (`director`, `both`) and `resolved_at` null.
- Oldest first, same age-based color escalation as §5.1.
- Row: Madrich name, grade, question excerpt, age, unread dot. Tap → entry detail with composer.
- Reply and "mark resolved" are separate actions; replying does not auto-resolve, because a question can need follow-up.

### 6.3 Coverage

- Next 6 Sundays × classrooms as a grid (mobile: one Sunday per row, expandable).
- Cell color by committed-vs-needed. Tap a cell for the name list split by committed / pending / declined.
- Direct link to nudge pending Madrichim — reuse the existing reminder task from Wave 3 rather than building a new send path.

### 6.4 Roster and completion

- All Madrichim with filters by grade (8–12), cohort, and completion status.
- Per-row status matching §5.2, plus supervising faculty.
- Drill-in to the same Madrich detail view faculty use, with full history.
- CSV export honoring active filters, for board reporting.

### 6.5 Faculty activity

- Per faculty member: assigned Madrichim, open threads, median response latency, age of oldest unanswered item.
- This is the card that tells Rachel whether the loop is actually closing. Sort by oldest-unanswered descending by default.

### 6.6 Growth dashboard

- Aggregated, anonymized reflection themes across all cohorts, per the TBE Growth Dashboard scope.
- Aggregation must not be re-identifying: suppress any theme group with fewer than 5 contributing Madrichim and show a "not enough responses yet" state instead.

### 6.7 Cohort feed moderation

- Read access to all cohort feeds with the ability to hide a post (`is_hidden`).
- Hiding is soft and reversible; log who hid it and when.

---

## 7. Permissions

Enforce server-side. Frontend gating is convenience only; every endpoint must independently reject.

| Capability | Madrich | Faculty | Director/Admin |
|---|---|---|---|
| Read own reflections | ✅ | — | — |
| Read another Madrich's reflections | ❌ | only supervised | ✅ (in-program) |
| Post to a thread on own entry | ✅ | ✅ (supervised) | ✅ |
| Read `routes_to='director'` thread | own only | ❌ | ✅ |
| Resolve a thread | ❌ | ✅ (supervised, faculty-routed) | ✅ |
| Cohort feed read | own cohort | supervised cohorts | ✅ |
| Like / comment on cohort post | ✅ | ✅ | ✅ |
| Hide cohort post | ❌ | ❌ | ✅ |
| Coverage view | own commitments | own classroom | ✅ |
| Faculty activity view | ❌ | ❌ | ✅ |
| CSV export | ❌ | ❌ | ✅ |
| Template/assignment builder | ❌ | ❌ | ✅ (existing `admin_only_or_403`) |

Reuse `admin_only_or_403()` from `common.py` for the admin gates. Add a `supervises(faculty_person, subject_person)` helper in `common.py` and route every faculty-scoped check through it — one function, one place to get it wrong.

Cross-org isolation tests are required on every new endpoint.

---

## 8. Tests

**Backend (pytest):**
- Model: thread check constraint (exactly one subject), thread uniqueness per `(reflection, field_key, item_index)`, unread computation across all four cases, `CohortShare` auto-creation on submit including the no-op case when the field is empty, reaction uniqueness.
- Schema validation: `routes_to` without `thread_enabled` rejected; `share_with_cohort` on `rating_group` rejected; valid combinations accepted.
- Permissions: every table row in §7, including the negative cases. Faculty cannot read a non-supervised Madrich. Madrich cannot read another Madrich's `question_or_concern` thread. Cross-org access returns 404/403, never a leaked object.
- Queue correctness: routed items appear in the right role's queue, disappear on reply/resolve, and sort oldest-first.
- Trends: series built from arbitrary `rating_group` fields, not hardcoded categories; correct handling of 0 and 1 data points.
- Aggregation suppression: theme groups under the 5-contributor threshold are not returned.
- Query counts on all three `/home/{role}/` endpoints via `assertNumQueries`.
- Regression: submitting a reflection with no threaded fields creates no threads.

**Frontend (Vitest):**
- Each homepage renders every card, including all empty states.
- Unread dots appear and clear on read.
- Attendance toggle is optimistic and rolls back on API failure.
- Entry detail renders self-updates and supervisor replies distinctly.
- Trend charts render dynamically from an arbitrary series payload.
- Cohort like toggles optimistically; self-like is disabled.
- Role-based routing sends each role to the right homepage.

**Verification before PR:**
- `make test-backend` and `make test-frontend` both pass
- `ruff check` and `npm run lint` pass
- `npm run build` succeeds
- Manual smoke on staging at 375px, 768px, and 1440px for all three roles

---

## 9. Out of scope — name and park, do not silently build

- Push or SMS notifications for new replies. Email reminders reuse the existing Wave 3 task only.
- Rich text, image, or file attachments in threads. Plain text only.
- @-mentions and notification routing.
- Editing or deleting thread messages beyond the 15-minute author window.
- Parent visibility of any surface here.
- Cross-program or multi-year trend history (Tier 3).
- Streaks, badges, or gamification on the Madrich homepage.
- Real-time updates. Poll or refetch on focus; no WebSockets.
- Sentiment analysis, answer-quality detection, or any automated flagging of reflection content. Explicitly deferred — this is the wellness/escalation boundary and it stays outside Tier 1.
- Faculty self-assessment (Tier 2).

---

## 10. Delivery

- Branch: `prompt-4.9-role-homepages`, or `prompt-4.9a…d` if split.
- Commits use the step ID as conventional-commit scope so the migration dashboard detects them: `feat(4_9_role_homepages): …`
- PR title starts with the step ID. PR body includes: **What**, **Why** (link this prompt), **Testing**, **Acceptance criteria checklist**, **Risk assessment**, **Rollback plan**.
- Do not merge; leave open for review.
- Additive only. No changes to old CLC models. No new dependencies without confirmation — if a chart library beyond what the camper profile already uses seems necessary, stop and ask.

## Acceptance criteria

- [ ] Pre-flight audit reported and conflicts resolved before implementation
- [ ] Schema flags implemented, validated, and documented in `docs/reflection-template-schema.md`
- [ ] `EntryThread`, `ThreadMessage`, `ThreadRead`, `CohortShare`, `ShareReaction` migrate cleanly with constraints enforced at the DB level
- [ ] All three homepages render correctly at 375px, 768px, and 1440px
- [ ] Threaded fields, trend charts, and cohort cards are all driven by template schema — zero hardcoded TBE field names in components
- [ ] Unread indicators correct on all three pages
- [ ] Faculty and Director response queues sort oldest-first with age escalation
- [ ] Every permission row in §7 covered by a passing test, including negatives and cross-org isolation
- [ ] Query counts asserted on the three composed home endpoints
- [ ] Full backend and frontend suites, linters, and build all pass
- [ ] Nothing from §9 shipped

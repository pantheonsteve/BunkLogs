# Bunk Logs — Admin Experience UX Review

**Reviewed:** Assignments, Group detail, Groups list, Memberships, People
**Primary user:** Non-technical program directors — education directors, camp directors. They use Admin heavily for a week or two at the start of a season, lightly during it, and again at reporting time.
**Scope of this review:** information architecture, terminology and mental model, visual design and layout.

A note on method: these findings come from static screenshots, so a few of them are inferences about behavior rather than confirmed observations. Anything I'm guessing at is flagged as such. Nothing here requires you to take my word over what you know from watching real directors use it.

---

## The core problem

Every Admin screen is organized around the database, not around the job. The nav reads People, Memberships, Groups, Assignments, Templates, Madrich completion, Growth by grade, Field Keys, Settings — nine entities. A director's actual work is about four tasks: *get everyone into the system, put them in the right classes, make sure the right adults can log about the right kids, and see who's actually filling out their logs.*

The gap between those two lists is where almost every usability problem in these screenshots comes from. A director who wants to put a teacher in a class has to already know that this lives in Assignments and not in Groups — even though Groups also has an "Add member" box that does something adjacent. That's a knowledge burden the app is placing on someone who opens it four times a year.

The good news is that the underlying model looks sound. Most of what follows is renaming, merging, and resequencing rather than rebuilding.

---

## Findings by screen

Severity key: **P0** = risk of data loss or a director getting stuck; **P1** = predictable confusion or repeated wasted effort; **P2** = polish.

### 1. Assignments

**P0 — Two irreversible-looking actions sit next to routine ones with no guardrail.** "Unassign" is rendered as a red-outlined button beside "Assign Person," visually equal in weight. It appears clickable with nothing selected. If it acts on the whole class, one mis-click undoes a roster. Destructive actions need to be disabled until a valid selection exists, labeled with the count ("Unassign 3 people"), and confirmed.

**P1 — The right-hand panel is dead on arrival.** "People to assign" says *"Select a program to see eligible people."* But the Program filter defaults to "All programs" and sits at the top of the page, far from the panel that depends on it. So the default state of this screen is a column that does nothing, with an instruction that doesn't say where to go. Either default the Program filter to the current active program (there's only one live one), or put the program picker inside the panel that needs it.

**P1 — The tab labels are data-model notation.** "Faculty → Class," "Student → Class," "Supervisor status" with the subtitle "Who a person supervises + reflection visibility." Arrows and the word "reflection visibility" are engineering vocabulary. Try: *"Teachers in classes," "Students in classes," "Who can see whose logs."*

**P1 — "Show all assignment types (4 hidden)."** Hiding four of seven options and telling the user they're hidden is worse than either showing them or not mentioning them. Directors will click it to see what they're missing, find four things they don't understand, and now be less confident. If the four are genuinely rare, move them behind a clearly-labeled "Advanced" area. If they're for developers, hide them from this role entirely.

**P1 — "— → open" under each person is unreadable.** I believe this is start date → end date, with "open" meaning no end date. As written it's a glyph puzzle. Say *"From Aug 30, 2026 — no end date"* or, for the common case, say nothing at all and only show dates when they're unusual.

**P2 — "Select active" is an ambiguous verb.** Is it filtering the list to active people, or checking every active person's box? Two very different outcomes from the same three words. If it's a select-all, make it *"Select all active (18)."*

**P2 — The program name is repeated in full on every row.** "The Rabbi Leslie Yale Gutterman Religious School (RLYGRS) at Temple Beth-El Religious School 2026-27" appears under every class in the list, truncated, adding zero information — you already filtered to it. Suppress it when a single program is in scope, and use the space for something useful: member count, or how many people are currently assigned.

**P2 — Class ordering is alphabetical, not developmental.** Grade 7, Kindergarten, Madrichim, PreK appear in that sequence. Directors think PreK → K → 1 → 2 … → Madrichim. Sort by a stored display order, not by name.

**P2 — The "Active" status control has its caret overlapping its label.** Small, but it's the kind of thing that makes an app feel unfinished, and it appears in at least three places across these screenshots.

### 2. Group detail (Madrichim)

**P0 — This is the screen where the terminology problem becomes a data problem.** The page reports "0 subjects · 32 authors." Thirty-two authors and zero subjects in a classroom is either a genuine special case (Madrichim are teen aides, so plausibly all of them are logging *about others*) or a serious setup error — and the UI presents both identically, with no comment. Meanwhile the "Add member" role dropdown defaults to "Subject (observed)," which is the role that zero of the existing 32 members hold. A director adding the 33rd madrich gets it wrong unless they notice.

Two fixes: default the role to whatever the group predominantly is, and add a quiet inline note on groups with a lopsided or empty composition — *"No students in this class yet. Add students, or mark this as a staff group."*

**P0 — "Subject (observed)" and "Author" are the two most important words in the product, and neither is a word a director would use.** More on this in the terminology section below, but concretely on this screen: a person seeing "Author" badges next to 32 names has no reliable way to know whether that means *this person teaches this class* or *this person wrote something about this class.*

**P1 — Developer internals are on the page.** "classroom · slug: madrichim" and "Parent: *None* set parent." Slug should not be visible to this audience at all; if it must be editable, put it under an Advanced disclosure. "Parent" is an unexplained hierarchy concept — if it's meaningful to directors, call it *"Part of: (nothing)"* and explain what it does when they click.

**P1 — Deactivate is a gray link; Clone to program is a button.** The action that takes a class out of service is the least visually prominent thing in the header, styled like helper text. Reverse the emphasis: primary actions get buttons, destructive ones go into an overflow menu with confirmation.

**P1 — Per-row trash icons with (apparently) no confirmation or undo.** Removing someone from a class may orphan their log history. At minimum: confirm, state the consequence in plain terms, and offer undo for a few seconds.

**P2 — Adding 32 people one at a time.** The only path here is a single "Search by name…" field. There's an Import CSV on the Groups list, but nothing on this screen tells you that's an option. Add multi-select to the search field, and a "Add several at once" link that routes to the import.

**P2 — "Select all" with no visible bulk-action bar.** Checking boxes should reveal what you can do with the selection. Right now the affordance promises a capability that isn't shown.

### 3. Groups list

**P1 — The rows carry almost no information.** Each is a name, the same long program string repeated, and an "Active" badge that's redundant because you're already filtered to Active. A director scanning this list wants to know: how many students, does it have a teacher yet, are logs coming in. Those three facts would turn this page from a directory into a start-of-year checklist.

**P1 — The program selector doesn't read as a filter.** It's a wide bordered box with the full program name in it and a caret jammed into the last character. It looks like a text input someone typed into. Label it ("School year:") and style it as a dropdown, or better — see the global year switcher recommendation below.

**P2 — "Import CSV" with no visible template or preview.** For a non-technical director this button is scary. It needs a downloadable template, a preview-before-commit step, and a clear statement of what happens to rows that don't match.

**P2 — No search on this page**, though there's a "Filter classes…" box on Assignments. Same content, different affordances.

### 4. Memberships

**P0 — "Delete Program" is a bare red link directly beneath "Edit Program."** This is the most dangerous element in all five screenshots. Deleting a program presumably takes a year of logs with it, and it sits one click from a routine action with, as far as I can tell, only a standard confirm between it and disaster. Move it into an overflow menu on the program detail page, require typing the program name, and state exactly what will be destroyed. Consider making it archive-only for anyone below superadmin.

**P1 — This page overlaps almost entirely with People.** The right-hand identity card here (Joshua Abrams, First name / Last name / Preferred name / Email, with Delete and Send invitation) is the same card that appears on the People page. Two routes to the same editor, and no signal about which one is "correct." Directors will bookmark one and be confused when a colleague describes the other.

**P1 — Test data is indistinguishable from real data.** "…TBE 2026 Test" is listed as Active right beside the live 2026-27 program. In a production tool used by non-technical staff, there should be a visible sandbox marker, or test programs shouldn't render in the normal list.

**P1 — "Active · 2026-09-13" is ambiguous.** Start date or end date? The second program says "Active · 2026-08-26." Label it: *"Runs Sep 13, 2026 – Jun 2027"* or *"Starts Sep 13."*

**P2 — "Send invitation" with no invitation state.** The single most common director question in September is *"who hasn't logged in yet?"* Show per-person status — Never invited / Invited Aug 12 / Active — and let them filter and bulk-invite on it. This is probably the highest-value net-new feature on this list.

**P2 — No enrollment count on programs.** "127 people" under the program name is a one-line change that answers a question directors ask constantly.

### 5. People

**P0 — "Dedupe" is enabled with one record selected.** Merging is destructive and hard to reverse. It should be disabled below two selections, and when it fires it should show a side-by-side merge preview: which record survives, which fields win, what happens to the log history attached to the loser. Right now it's a red button that a curious director can press to find out.

**P1 — The list rows show name and email only.** You can filter by Role and Status, but you can't see either one in the results. So filtering is a leap of faith and the results can't be verified by eye. Add role and status to each row.

**P2 — "Last name starts with: Any letter" alongside a search field** is likely vestigial from a pre-search era. Two ways to narrow by name is one too many; the alphabet filter is the weaker one.

**P2 — Checkbox selection and the detail pane are conflated.** Joshua Abrams is both checked and shown in the detail pane, so it's unclear whether clicking a name selects it for bulk operations or just previews it. Separate the two: click the row to preview, click the checkbox to select.

**P2 — No visible Save on the identity form.** I can't tell from a screenshot whether it autosaves. If it does, say so ("Saved" indicator). If it doesn't, the button needs to be above the fold or in a sticky footer.

---

## Information architecture: a proposal

Nine Admin nav items map to roughly four jobs. Here's a consolidation that keeps every existing capability but arranges it the way a director thinks.

**Add a global context switcher in the header.** Right now the program has to be re-selected on Groups, on Assignments, on Memberships — independently, with different controls, and defaults that don't agree. Put one "School year: 2026-27 ▾" control in the top bar, persist it, and let every Admin page inherit it. This single change removes three confusing controls and eliminates a whole class of "why is this list empty" moments.

**Merge Groups and Assignments into one "Classes" area.** These are two views of one question — *who is in this class.* Today a director must know that students-and-staff-in-a-class lives in Assignments, while members-of-a-group lives in Groups, while the two lists overlap. Instead: a Classes list, and clicking a class opens one page with tabs for *Students*, *Teachers & staff*, and *Settings*. The bulk-assign flow becomes a "Add students" button on the Students tab.

**Merge Memberships into People.** Enrollment is an attribute of a person in a year. The person editor already exists in both places; keep one. Program/year creation and editing moves to a small "Setup" area, which is where a director goes twice a year and nowhere else.

**Group the reports.** Madrich completion and Growth by grade are both reports; they should live under a Reports heading, alongside the answer to "who hasn't submitted this week," which is the report directors want most and which I don't see anywhere in these screenshots.

The resulting nav:

| Today | Proposed |
|---|---|
| People, Memberships | **People** — everyone, their roles, invite status, which years they're enrolled in |
| Groups, Assignments | **Classes** — each class, with Students / Teachers & staff / Settings tabs |
| Templates, Field Keys | **Forms** — what the logs ask |
| Madrich completion, Growth by grade | **Reports** — plus a "who hasn't submitted" view |
| (scattered) | **Setup** — school years, roles, permissions, danger-zone actions |
| Settings | **Settings** |

**Add a start-of-year path.** The busiest, highest-stakes week of the year has no support in this IA. A guided "Set up 2027-28" flow — copy last year's classes, roll students up a grade, carry forward staff, review exceptions, send invitations — would be the single biggest reduction in director effort available here. The building blocks already exist ("Clone to program," Import CSV, Send invitation); they're just not sequenced.

---

## Terminology

This is the highest-leverage, lowest-cost change in the review. Most of it is find-and-replace.

| Current | Problem | Suggested |
|---|---|---|
| Subject (observed) | Nobody calls a child a "subject." Reads clinical. | **Student** (or **Camper** — make it configurable per organization) |
| Author | Suggests writing, not teaching. Ambiguous about role. | **Teacher** / **Counselor**, or **Writes logs** if the role really is broader |
| Program | Means a curriculum to most educators. Here it means a year. | **School year** / **Season** |
| Group | Generic. The list is already split into "classroom" types. | **Class** (**Bunk** for camps) |
| Membership | Database word. | **Enrollment** |
| Assignment | Collides with schoolwork "assignment." | Absorb into the Class page; no separate noun needed |
| slug | Internal identifier. | Hide from this role |
| Parent | Unexplained hierarchy. | **Part of** — with a one-line explanation |
| Field Keys | Opaque. | **Form fields** |
| Faculty → Class | Notation. | **Teachers in classes** |
| Reflection visibility | Two abstractions stacked. | **Who can see whose logs** |
| Reflections (sidebar) | The product is called Bunk Logs; the nav says Reflections. | Pick one word and use it everywhere |

That last row matters more than it looks. When the product name and the nav label disagree, every support conversation and training session pays a small tax.

Two supporting moves: define the four or five words that survive this pass in one short in-app glossary, linked from a "?" beside each first use; and make the student/camper noun a per-organization setting, since Bunk Logs serves both camps and religious schools and neither wants the other's vocabulary.

---

## Visual design and layout

**Cut the repetition.** The full program name appears under every single row on Groups, Assignments, and in the filters — a ~90-character string repeated a dozen times per screen, always truncated. With a global year switcher it disappears entirely, and those rows get room for information that actually varies.

**Give destructive actions a consistent, subordinate treatment.** Right now Delete Program is a red link, Deactivate is a gray link, Dedupe is a red button, Unassign is a red-outlined button, and removal is a trash icon. Five treatments, no rule. Establish one: destructive actions live in an overflow menu, are disabled until a valid selection exists, name their target and count, and confirm proportionally to their consequence.

**Standardize the three-panel cascade.** Assignments and Memberships both use list → detail → action, but with different column behaviors and different rules about what's live when. Pick one pattern and apply it identically, including the disabled and empty states.

**Make empty states do work.** "Select a program to see eligible people" is a passive instruction. Empty states should contain the control that resolves them — put the program picker right there, or the "Add your first student" button, rather than describing what the user should go do elsewhere.

**Fix the small stuff that reads as unfinished.** Carets overlapping their labels in at least three dropdowns; the lightest gray secondary text is likely below WCAG AA on white; the unlabeled sun icon in the header; the Classes list clipping mid-row at the fold.

**Add counts and status everywhere.** Members per class, enrollment per program, "0 of 11 classes have a teacher assigned," invitation state per person. Directors are constantly answering "is this set up correctly yet," and every count you add answers part of that question without them clicking.

---

## Where I'd start

If you only ship a handful of things:

1. **Guard the destructive actions** — Delete Program, Dedupe, Unassign, remove-member. Lowest effort, highest downside avoided.
2. **Rename subject/author to student/teacher, and program to school year.** Mostly find-and-replace; changes how the whole app reads.
3. **Global year switcher in the header**, inherited by every Admin page. Removes three inconsistent controls and a lot of empty-state confusion.
4. **Merge Groups + Assignments into Classes**, with Students / Staff tabs. The biggest IA win, and the one that stops directors having to guess which screen to open.
5. **Invitation status on People**, with filter and bulk-invite. Answers September's most-asked question.
6. **Counts on every list row.** Cheap, and it turns directories into checklists.

Then, when there's room for a bigger piece: the guided start-of-year flow. That's the one directors will remember.

---

## What I'd want to check before committing

A few things I can't determine from screenshots and would want confirmed: whether the identity editor autosaves; what Unassign and Dedupe actually do with no or one selection; whether removing a member deletes their log history or just hides them; whether the four hidden assignment types are director-relevant; and whether the 32-authors-zero-subjects state on Madrichim is intentional. Watching two directors do a real start-of-year setup, thinking aloud, would settle all five and probably surface three more worth more than anything in this document.

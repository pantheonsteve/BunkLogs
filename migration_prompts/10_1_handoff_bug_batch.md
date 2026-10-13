# 10_1 — Handoff bug batch

**Step ID:** `10_1_handoff_bug_batch`
**Estimated time:** 4–6 hours (one PR; split off item 2 if it grows)
**Mode:** lean
**Reference:** `docs/dashboard-catalog.md`, Steve's "Trips up" notes in pairs 1, 3 and 4

```
Fix the bugs and small rough edges Steve hit while using the app as a TBE
admin, faculty member and madrich. Each item: confirm the cause in a short
pre-flight note, then fix. Do not change how people are placed in groups or
any role/permission model (that is 10_2).

1. "View students" denies access to the madrich's own classroom.
   Repro: log in as Leo Sobel (TBE, madrich). Home shows one classroom
   ("Madrichim") under "My classrooms"; "View students" -> access denied.
   Leo is in classrooms 197 and 199, which don't appear.
   Likely cause (verify): the madrich home's MyClassroomCard lists
   classrooms from /madrich/challenges/classrooms/, which uses
   classroom_group_ids_for_role(role_in_group="subject"). The group
   dashboard (resolve_group_dashboard_context, step 6) only admits
   classroom AUTHORS. So the card links to groups Leo can't open and omits
   the ones he can.
   Fix: the card lists classrooms where the viewer is an author (the ones
   they can open and log in), using a new endpoint or a field on the
   madrich dashboard payload. Leave the challenges endpoint as is. Card
   copy goes through term() (no "Your students" literal).

2. Group Performance doesn't count TBE submissions.
   Repro: submit Leo's reflection; admin home Performance tab
   (?program=12&group_type=classroom) doesn't change.
   Cause (verified in api/dashboards/performance.py): completion only
   counts group_type == "bunk" groups, the camper template, and a single-
   day period. Classrooms always report expected = 0.
   Fix: completion for any group type = expected vs. submitted for the
   templates assigned to that group (TemplateAssignment with
   target_type=assignment_group, plus the existing camper-template path
   for bunks), using each template's cadence to pick the period that
   contains the selected date (daily -> that day, weekly -> that week).
   Expected = the group's members who should submit (authors matching the
   template's author_role_filter for self/author templates, or subjects
   for subject templates). Keep the bunk result identical for Crane Lake.
   Pre-flight: list which templates TBE has assigned to classrooms and
   their cadence/subject_mode, and confirm what "submitted" should mean for
   each before coding. Stop and report if it isn't clear-cut.

3. "Daily logs" nav link bounces to home.
   Repro: as Sadie Allspaw (TBE faculty), sidebar -> Daily logs ->
   /dashboards/logs -> lands back on the home screen.
   Find why the link renders for this user and why the page redirects.
   Fix: don't show a nav link to a page the viewer can't use. If the page
   should work for faculty (forms assigned to their classes), make it
   work; otherwise hide the link for them.

4. Navigation fixes:
   - Add the Coverage dashboard to the admin nav (it's in the sidebar for
     other roles but missing for admins).
   - "Concerns about my unit" (Sidebar.jsx) -> term('unit') based copy.
   - Faculty sidebar: fold "File a reflection" and "My reflections" under a
     single "Reflections" item; don't show "Reflections" twice.

5. Challenge detail pages (faculty/ChallengeDetail.jsx and
   madrich/ChallengeDetail.jsx):
   - Restyle with components/ui primitives (PageHeader, Card, ThreadView
     or the existing thread styling, Badge for status) so they match the
     rest of the app.
   - After a reply or a submitted challenge, show a clear primary action at
     the bottom: "Done" returning to the challenges list (faculty) or home
     (madrich). Keep the existing back link at the top.
   - Extract the shared layout into one component used by both pages.

Tests:
- Madrich home lists author classrooms; every listed link opens (200).
- Performance: a classroom with a weekly assigned template shows the
  submission after a madrich submits; bunk numbers unchanged for a camp
  fixture.
- Nav: no link to /dashboards/logs for a viewer who would be redirected.
- Challenge detail renders the Done action after replying.

Acceptance criteria:
- Each repro above no longer reproduces.
- Crane Lake behavior unchanged (camp fixtures pass).
```

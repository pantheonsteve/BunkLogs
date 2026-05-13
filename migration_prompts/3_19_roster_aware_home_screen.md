# Prompt 3.19 — Roster-aware home screen and submission flow

**Wave:** 3 (Crane Lake Summer 2026 Build) — Shared-roster observation pattern
**Estimated time:** 8-10 hours
**Prerequisite:** Prompts 3.17 and 3.18 complete.

**Use the context prompt at the top of `bunklogs-migration-prompts.md` before this session.**

---

```
Build the "what do I owe today?" home screen and the per-subject submission flow. Authors see their assigned rosters, completion state at a glance, and tap a subject to fill out a reflection about them.

CONTEXT:
This is the runtime UX that turns the data model into a product. It replaces the existing single-form-per-user "template-for-me" flow with a roster-aware list. Self-reflection still works (a self-reflection appears as one item on the list with no roster).

Refer to the conversation flow described earlier:
  Today's bunk logs (Bunk Maple)
    [○] Sarah  [○] Maya  [○] Aviva
    [✓] Eden   [○] Tali  [✓] Maya R
    [○] Lily   [✓] Naomi
  6 of 8 campers covered. You've logged 2.

Tasks:

1. Build a unified "tasks for today" API endpoint:
   GET /api/v1/reflections/my-tasks/?period={today | this_week}
   
   Returns a list of "task groups" the current user is responsible for. Each task group is one (template, assignment_group) pair. Structure:
   
   {
     "tasks": [
       {
         "id": "<stable hash of template_id + group_id + period>",
         "template": { ...template summary... },
         "assignment_group": { id, name, group_type } | null,
         "subject_mode": "single_subject" | "self" | "group" | "multi_subject",
         "period": { "start": "2026-06-15", "end": "2026-06-15" },
         "subjects": [
           {
             "person_id": ...,
             "name": "Sarah Levin",
             "preferred_name": "Sarah",
             "covered": true | false,
             "covered_by_me": true | false,
             "reflection_id": ... | null,
             "covered_by_name": "Counselor Mike" | null
           },
           ...
         ],
         "completion": { "covered": 6, "total": 8, "my_count": 2 },
         "self_status": { "submitted": false, "reflection_id": null }  // only for subject_mode='self'
       },
       ...
     ]
   }

2. Logic for what tasks appear:
   - For each ReflectionTemplate visible to the user's org and active:
     a) If subject_mode='self' and user has a Membership matching template.author_role_filter (or filter is empty):
        - Generate a self-reflection task with self_status reflecting submission state
     b) If subject_mode in ('single_subject', 'multi_subject') and user is in any AssignmentGroup as author with group_type in template.assignment_group_types:
        - For each such group: generate a task with the subject roster
        - Each subject's `covered` flag derived from existing Reflections in this period
     c) If subject_mode='group' and user is in any AssignmentGroup as author with matching group_type:
        - For each such group: generate a task with no subjects (just the group)
   - Period derived from template.cadence: 'daily' = today's date, 'weekly' = this calendar week, etc.
   - Order tasks: incomplete first, then by template.cadence (daily before weekly), then by template.name

3. Performance: this endpoint runs on every home-screen load, so query carefully. Aim for <300ms with realistic Crane Lake data (50 staff, 200 campers, 10-15 active templates). Use prefetch_related for memberships and select_related for templates. Add caching with a 60-second TTL keyed by user + period if needed.

4. Build the React home screen at /tasks (or replace existing /reflect home if appropriate). For Crane Lake counselors and TBE Madrichim, this should be the default landing page after login.

   Layout:
   - Header: "Today" or "This week" depending on date
   - Summary card at top: "3 tasks waiting. 1 completed." with progress bar
   - One section per task group, ordered as above
   - Each section header shows: template name, group name (if any), completion count
   - Body of each section depends on subject_mode (see below)

5. Section rendering by subject_mode:

   self:
   - Single card showing template name and "Your reflection" with status icon
   - Tap card -> existing reflection form (3.5/3.15 renderer)
   - Card shows ✓ + timestamp when submitted; tappable to view (read-only) or edit (if within edit window)
   
   single_subject:
   - Group header with completion count "6 of 8 covered"
   - Grid of subject pills (3 columns on mobile, 4-5 on desktop)
   - Each pill shows: status icon (○ uncovered / ✓ covered by anyone / ★ covered by me), preferred_name
   - Subject pill colors:
     * Uncovered: gray border, white background
     * Covered by someone else: green check, light green background
     * Covered by me: green check + small star, light blue background
   - Tap an uncovered pill: opens the reflection form pre-filled with subject and assignment_group
   - Tap a covered pill: shows a small popover "Logged at 4:23pm by Counselor Mike. View." Tap "View" to see read-only or edit (if you authored it)
   
   group:
   - Single card per group showing group name and status
   - Tap card -> reflection form pre-filled with subject_group
   
   multi_subject:
   - Defer to v2 — for v1, render this the same as single_subject (each subject as a pill, fill out one at a time)
   - Add a TODO comment in the code referencing prompt 3.21 (multi-subject batch submission) which is deliberately deferred

6. Update the reflection form (from 3.5, refined by 3.15) to handle the new context:
   - Accept route params: ?template={id}&assignment_group={id}&subject={person_id}
   - When subject is provided: render subject's name in form header ("About Sarah Levin")
   - When subject_mode='group': render group name in header ("Junior Boys unit reflection")
   - On submit: include subject, author (current user's Person), assignment_group, subject_group in payload
   - submission_id generated client-side as UUID, used to group multi-step submissions in future

7. Update existing self-reflection submissions to populate author = subject = current user's Person automatically. Migration of existing data already handled in 3.17.

8. Real-time refresh on coverage:
   - When a user submits a reflection, the home screen should reflect the change without requiring a full reload
   - For v1, simplest path: invalidate the my-tasks cache on submit, navigate back to home, refetch
   - Don't build websocket/polling for live multi-user updates; the use case is "I just submitted, let me see my list update"

9. Permissions on coverage info (for the popover that says "Logged at 4:23pm by Counselor Mike"):
   - Author names visible only to other authors of the same group (counselors see who else logged)
   - Subjects don't see authors
   - Org admins see everything
   - Add a serializer flag based on viewer's relationship to the group

10. Add a "Today's coverage" supervisor view at /supervisor/coverage:
    - Visible to anyone with role='admin' or any author membership in groups with children (e.g. unit head sees their bunks)
    - Lists groups in scope with completion percentages
    - Drill into a group to see the same subject grid the counselors see
    - This is a precursor to the dashboard work in 3.20 — keep it simple, just completion data

11. Tests:
    - my-tasks returns correct tasks for self-reflection only user (TBE Madrich)
    - my-tasks returns correct tasks for shared-roster user (Crane Lake counselor in two bunks)
    - my-tasks returns no tasks if no eligible templates or memberships
    - Coverage state correctly reflects existing reflections
    - covered_by_me flag accurate
    - Subject pill tap routes to form with correct prefill
    - Submitting a reflection updates coverage state
    - Coverage popover shows author name only to authorized viewers
    - Supervisor view scopes to user's responsibility correctly
    - Frontend tests cover all three section types (self, single_subject, group)
    - Multi-bunk counselor sees both bunks with separate sections

12. Accessibility:
    - Subject pills have aria-label combining name and coverage status ("Sarah Levin, not yet logged" vs "Eden Cohen, logged by Counselor Mike")
    - Color is not the only signal — icons (○ vs ✓) carry meaning too
    - Touch targets meet minimum size (44x44px) for mobile use

Acceptance criteria:
- Counselor in Bunk Maple sees Bunk Maple's roster with accurate coverage
- Counselor in two bunks sees both as separate sections
- TBE Madrich sees their self-reflection task
- Submitting a log about a camper updates the home screen on next render
- Other counselors in the same bunk see the camper as covered (with optional author attribution)
- Form submission correctly populates subject, author, assignment_group
- Self-reflection flows continue to work end-to-end
- Supervisor coverage view loads under 500ms with realistic data
- Full test suite passes including frontend
- Commit structure: 1) my-tasks endpoint, 2) home screen layout, 3) section renderers per subject_mode, 4) form pre-fill + submit updates, 5) supervisor coverage view, 6) tests + a11y

Out of scope:
- Multi-subject batch submission (3.21, deferred)
- Coverage trend graphs and color heatmaps (3.20)
- Notifications for "Bunk Maple is missing 2 logs at 9pm" (future, after observing real usage)
```

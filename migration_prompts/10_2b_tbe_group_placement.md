# 10_2b — Move TBE onto the shared camp/school model

**Step ID:** `10_2b_tbe_group_placement`
**Estimated time:** 5–7 hours
**Mode:** full (production data for a live customer)
**Depends on:** 10_2a
**Run when:** not on a Sunday or the day before; take a prod snapshot first (`make sync-prod-db`), dry-run against it locally

```
Goal: TBE uses the same structure as a camp.
  Madrich = Counselor: writes reflections, logs on students in their class
  Faculty = Unit Head: supervises the madrichim in their class, answers
            challenges; may also write about students
  Student = Camper: written about, no login
  Class   = Bunk
Today import_tbe_roster places madrichim in each classroom as BOTH subject
and author, and faculty as author. Faculty "observe" madrichim as subjects;
students are not the subjects. Steve's intended model is the one above.

Pre-flight audit (report, then STOP for Steve to confirm before applying):
1. Every consumer of a madrich's classroom placement, especially
   role_in_group="subject" for madrichim: classroom challenges
   (classroom_group_ids_for_role, is_classroom_subject), faculty roster and
   dashboard, director coverage, availability, cohort, reflection
   visibility, reminders, group dashboards, performance.
2. Current TBE counts per classroom: madrichim (subject/author), faculty,
   students (subject), Supervision rows.
3. The terminology each TBE screen will show after the change (see below),
   for a faculty user, a madrich user and an admin.

Changes:
1. Group config for TBE (Organization.settings["group_types"]) via a data
   migration scoped to slug "tbe":
     classroom: madrich author; student subject;
                faculty author + supervises_group
2. Switch every consumer found in audit item 1 from "madrich is a subject
   of the classroom" to "madrich is an author of the classroom" (e.g. a
   madrich can file a challenge for classrooms they author). Faculty
   roster/"who's out" lists the group's madrich authors, not its subjects.
3. Data migration (idempotent, reverse noop, slug "tbe" only):
   - deactivate (is_active=False, don't delete) madrich subject placements
     in classrooms; ensure their author placement is active
   - run the 10_2a supervision sync for faculty in each classroom
   - log counts of what changed
4. import_tbe_roster: place madrichim as authors only. Mark the command
   deprecated in favor of the 7.4 generic importer when that lands.
5. TBE terminology (data migration + setup_tbe.py CANONICAL_ORG_SETTINGS):
     camper -> student/students
     counselor -> madrich/madrichim
     unit_head -> faculty/faculty
     bunk, group -> class/classes
     director -> Ed Team; cohort -> Teaching Team; program -> school year
   Update screens that currently use term('camper') or term('counselor')
   to mean madrichim or faculty so the words match the new model
   (faculty home roster -> term('counselor'), etc.).
6. Copy fixes: MyClassroomCard copy through term(); replace the hardcoded
   "Temple Beth-El staff" in madrich/ReflectionForm.jsx with the org's
   display name.

Tests:
- Migration on a TBE fixture: madrich subject rows deactivated, author rows
  active, faculty Supervision rows created; rerun is a no-op; clc untouched.
- Madrich can open their classroom dashboard and log on a student.
- Madrich can still file and read challenges; faculty still see them.
- Faculty profile's Supervision tab lists the madrichim in their classes.
- Faculty home labels madrichim with term('counselor') -> "madrichim".
- No "Temple Beth-El" literal in frontend/src outside tests/orgSlug.js.

Acceptance criteria:
- Same structure at TBE as at Crane Lake; only the words differ.
- Every TBE flow that worked before (3-2-1, challenges, availability,
  cohort, director coverage) still works.
```

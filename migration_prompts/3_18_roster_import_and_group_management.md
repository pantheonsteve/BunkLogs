# Prompt 3.18 — Roster import and group management

**Wave:** 3 (Crane Lake Summer 2026 Build) — Shared-roster observation pattern
**Estimated time:** 6-8 hours
**Prerequisite:** Prompt 3.17 complete.

**Use the context prompt at the top of `bunklogs-migration-prompts.md` before this session.**

---

```
Populate AssignmentGroups and their memberships from real-world data sources. Extend the Campminder importer to create bunks. Build admin UI for managing groups and rosters. Add write API endpoints with appropriate permissions.

CONTEXT:
The data model from 3.17 is empty. This prompt makes it real for Crane Lake's Summer 2026 launch and provides reusable infrastructure for TBE classrooms and any future customer's roster import.

Tasks:

1. Extend the Campminder import command from prompt 3.9 (`core/management/commands/import_campminder_staff.py`) — or create a sibling command if 3.9 isn't yet built — to also handle camper rosters and bunk assignments. Rename the command if scope warrants: `import_campminder_roster.py`.

   New CSV format support (additive — keep existing staff-only format working):
   - Required columns: campminder_id, first_name, last_name, role
   - Optional columns: email, language_preference, tags
   - NEW optional columns: bunk_name, unit_name, division_name (for hierarchy)
   - NEW optional columns: caseload_name (for wellness team subjects)

2. Import logic for new columns:
   - When bunk_name is present:
     * get_or_create AssignmentGroup with group_type='bunk', name=bunk_name, program=current_program
     * If unit_name also present: get_or_create the unit AssignmentGroup, set as parent of the bunk
     * If division_name also present: get_or_create the division, set as parent of the unit
     * Create AssignmentGroupMembership(group=bunk, person=person, role_in_group based on Membership.role)
       - role_in_group='subject' for campers
       - role_in_group='author' for counselors, junior_counselors, etc. assigned to that bunk
   - When caseload_name is present:
     * get_or_create AssignmentGroup with group_type='caseload'
     * The caseload owner (a wellness staff member) is determined by a separate column or pre-existing convention; for now require caseload_owner_campminder_id column when caseload_name is set
     * Add caseload owner as author, listed campers as subjects

3. Idempotency: re-running the import with the same CSV must not duplicate AssignmentGroups or memberships. Match groups by (program, group_type, slug-of-name). Match memberships by (group, person, role_in_group).

4. Add a `--reconcile` flag that, in addition to creating new memberships, deactivates memberships present in the database but not in the CSV (e.g. a camper switched bunks mid-summer). Default behavior is additive only; --reconcile is opt-in.

5. Document the workflow in docs/campminder-roster-import.md with:
   - Full CSV format spec
   - Sample CSV showing all column types
   - Common workflows: initial summer import, mid-summer roster change, end-of-summer cleanup
   - Troubleshooting: what happens when a Person exists but their bunk_name doesn't match anything

6. Build a TBE classroom roster importer at `core/management/commands/import_tbe_roster.py`. Lighter than Campminder — TBE typically gets a CSV from ShulCloud. Format:
   - Required: first_name, last_name, role, classroom_name, grade_level
   - Optional: email, parent_email, faculty_email (for the classroom's faculty)
   - Creates AssignmentGroup with group_type='classroom' for each unique classroom_name
   - Madrichim go in as subjects (since faculty observes them) AND as authors of their own self-reflection (a Madrich is the author of their own weekly 3-2-1)
   - Faculty go in as authors of the classroom

7. Admin UI extensions for AssignmentGroup and memberships:
   - In Django admin: list_display, list_filter on group_type, search on name, raw_id_fields for parent
   - Inline AssignmentGroupMembership editing on AssignmentGroup detail page
   - In the user-facing admin app (under /admin/groups/): a CRUD UI for org admins
     * List of groups grouped by group_type
     * Detail page with two columns: subjects and authors
     * Add member: search Person by name/email, assign role_in_group
     * Remove member: soft (set is_active=False) by default; hard delete with confirm
     * Bulk actions: import roster (file upload triggers a background task)

8. API endpoints (extending 3.17's read-only set with writes):
   - POST /api/v1/assignment-groups/ — create new group (org admin or super admin)
   - PATCH /api/v1/assignment-groups/{id}/ — update name, parent, metadata
   - DELETE /api/v1/assignment-groups/{id}/ — soft delete (is_active=False); reject if reflections reference it
   - POST /api/v1/assignment-groups/{id}/memberships/ — add a person with role_in_group
   - DELETE /api/v1/assignment-groups/{id}/memberships/{membership_id}/ — remove (soft)
   - POST /api/v1/assignment-groups/{id}/import-roster/ — accepts a CSV upload, kicks off a background import task; returns a task ID for status polling
   
   Permissions:
   - Read: any authenticated user in the org
   - Write: org admin or super admin (use IsOrgAdminOrSuperuser from 3.13)

9. Background import task `core/tasks.py::import_roster_task(csv_path, program_id, importer_type, options)`:
   - Wraps the management command logic so it runs async via Celery
   - Returns a structured result: counts, warnings, errors by row
   - Stores the result in a small new model `RosterImportLog` so admins can review past imports

10. Add RosterImportLog model:

class RosterImportLog(models.Model):
    organization = ForeignKey(Organization, on_delete=CASCADE)
    program = ForeignKey(Program, on_delete=CASCADE)
    importer_type = CharField(max_length=64)  # 'campminder', 'tbe_shulcloud', etc
    initiated_by = ForeignKey(User, null=True, on_delete=SET_NULL)
    status = CharField(max_length=32)  # pending, running, completed, failed
    summary = JSONField(default=dict)  # counts, warnings, errors
    csv_filename = CharField(max_length=255, blank=True)
    started_at = DateTimeField(auto_now_add=True)
    completed_at = DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']

Apply OrgScopedManager.

11. Tests:
    - Campminder import creates bunks with parent unit and division correctly
    - Re-running same CSV is idempotent
    - --reconcile flag deactivates removed memberships
    - TBE classroom import creates classrooms with Madrichim as subjects and faculty as authors
    - A Madrich is correctly added as both subject (in classroom) and author (of their self-reflection — which doesn't need an assignment group, but verify Membership role still works)
    - API write endpoints respect IsOrgAdminOrSuperuser
    - Cross-org isolation: an org admin cannot create groups in another org
    - DELETE blocked when reflections reference the group
    - Background task runs and writes RosterImportLog
    - Failed imports surface row-level errors in the log

12. Smoke test on staging with a representative Crane Lake CSV (use synthetic data; real PII not required for this test). Verify:
    - Expected number of bunks created
    - Camper count matches CSV
    - Counselor-to-bunk assignments correct
    - Hierarchy (bunk -> unit -> division) intact

Acceptance criteria:
- Both Campminder and TBE roster import commands work
- Idempotency holds across re-runs
- Admin UI lets org admins manage groups without touching CSVs
- API write endpoints work with permission gates
- Background task pattern works end-to-end
- RosterImportLog captures useful diagnostics
- Documentation written
- Full test suite passes
- Commit structure: 1) Campminder roster extension, 2) TBE classroom importer, 3) admin UI, 4) write API + permissions, 5) background tasks + log model, 6) docs

Out of scope:
- Roster-aware home screen (3.19)
- Coverage dashboards (3.20)
- Multi-program roster overlap UI (e.g. a camper who's also in religious school) — defer until a customer needs it
```

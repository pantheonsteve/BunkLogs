# 10_2a — Org roles and group-type configuration

**Step ID:** `10_2a_org_roles_and_group_types`
**Estimated time:** 8–10 hours (two PRs: backend, then admin UI)
**Mode:** full (touches group access and supervision)
**Reference:** `docs/dashboard-catalog.md`, pair 1 and pair 4 notes
**Next:** 10_2b moves TBE onto this configuration

```
Goal: an org admin can set up who exists in their org and how groups work
without Steve. Today the role list, which roles go in which group type, and
who supervises whom are hardcoded in several places. Make them per-org
configuration with defaults that reproduce current behavior exactly.

Today (verify in pre-flight):
- People -> Add person shows every Membership.ROLES value
  (frontend MEMBERSHIP_ROLE_OPTIONS in components/admin/PersonProfilePanel.jsx).
- pages/admin/groups/groupTypes.js hardcodes SUBJECT_BEARING_TYPES,
  SUPERVISABLE_TYPES and authorTermKey(); the group page's Members/Staff tabs
  use term('camper') / term('counselor'|'staff').
- api/dashboards/group_dashboard_common.py resolve_group_dashboard_context
  grants author access per group type with hardcoded role lists
  (bunk -> COUNSELOR_ROLES, classroom -> CLASSROOM_AUTHOR_ROLES).
- Supervision rows (core.Supervision) are created by hand on the
  Supervision tab; adding a faculty member to a classroom creates none, so
  their person profile says "nothing supervised yet".
- A person's admin profile says "Not in any groups" with no way to add one.
- Program type in Setup is a free-text field.

Pre-flight audit (report before writing code):
1. Every hardcoded list of roles, group types, or role_in_group decisions
   in backend api/ + core/ and frontend admin pages, with what each
   decides.
2. How Supervision rows are created today for unit heads (camp) and
   faculty/director (TBE), and every resolver that reads them.
3. Current TBE and CLC data shape: roles in use per org; per group type,
   which roles are placed as author vs subject.

Design:
1. core/org_config.py
   - enabled_roles(org) -> list of role slugs. Organization.settings
     ["roles"] if set, else the roles that have any Membership in the org,
     plus "admin". (No data change needed for clc/tbe.)
   - group_type_config(org) -> dict keyed by group_type:
       {"enabled": bool,
        "members": [{"role": "<slug>", "placed_as": "author"|"subject",
                     "supervises_group": bool}]}
     Organization.settings["group_types"] if set, else defaults that match
     today's behavior:
       bunk: counselor/junior_counselor/general_counselor author;
             camper subject
       classroom: madrich author+subject (current TBE shape, changed in
             10_2b), faculty author; student subject
       unit/division: unit_head supervises_group; camper_care via caseload
             as today
     "supervises_group": adding that person to the group creates an active
     Supervision(target_type=ASSIGNMENT_GROUP) row for that group; removing
     them end-dates it.
   - Validation: roles must be in Membership.ROLES; a role can't be both
     author and subject in one group type unless explicitly listed twice.
2. Group dashboard access: replace the hardcoded steps 5 and 6 in
   resolve_group_dashboard_context with "active author in this group whose
   Membership.role is configured as author for this group type". Keep
   admin, LT, unit head and camper care steps as they are. Counselors
   still get no rollup to parent groups.
3. Supervision sync: a service function that creates/end-dates Supervision
   rows from group placement for roles with supervises_group. Called from
   the group membership add/remove endpoints. Management command
   sync_group_supervision --org <slug> [--apply] (dry run default) to
   backfill existing placements.
4. Expose enabled_roles and group_type_config in the admin API payloads
   the People and Groups pages already load.

Admin UI:
5. People -> Add/Edit person: role dropdown shows only enabled roles,
   labeled through terminology.
6. Person profile: where it says "Not in any groups", an "Add to group"
   button -> pick group -> placement is chosen from the group type config
   (ask only if the role can be placed more than one way).
7. Group page: the Members/Staff tabs and their "Add …" buttons come from
   the group type config (one button per configured role, labeled with
   that role's term). Every member row shows pills: role (term) and
   placement (author/subject/supervisor in plain words).
8. Settings -> "Roles" card: checkboxes for enabled roles, with terminology
   labels and a one-line description each. Disabling a role that still has
   active members is blocked with a message naming how many.
9. Settings -> "Groups" card: per enabled group type, which roles can be
   added and how (writes / is written about / supervises). Plain-language
   labels; no slugs on screen.
10. Setup -> Program: Program type is a select of Program.PROGRAM_TYPES
    ("Summer camp", "Religious school").

Tests:
- Defaults reproduce today's behavior: snapshot enabled roles and group
  config for clc and tbe fixtures; existing group-dashboard access tests
  pass unchanged.
- A role added as author via config can open the group dashboard; a role
  not configured cannot.
- Adding a supervises_group member creates a Supervision row; removing it
  end-dates it; sync command dry run writes nothing; apply is idempotent.
- Role dropdown excludes disabled roles; disabling a role with active
  members is rejected.
- Program form only offers valid types.

Acceptance criteria:
- Crane Lake and TBE behave exactly as before with no settings written.
- An admin can: limit roles to their org, add a person to a group from
  the person page, see each group member's role, and have supervision
  follow group placement, all in the app.
```

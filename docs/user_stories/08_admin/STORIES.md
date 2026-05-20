# Admin Flow — Stories 54-60

## Configuration primitives this flow exposes

| Primitive | Defined in | Admin's relationship |
|---|---|---|
| Organization | Migration prompts 2.1 | Operates within one |
| Program | Migration prompts 2.2 | Creates, configures, archives |
| Person | Migration prompts 2.3 | Creates, edits, deactivates |
| Membership | Migration prompts 2.4 | Assigns roles, dates, tags |
| Supervision | `../00_cross_cutting/supervision_relationship.md` | Configures all instances |
| Camper Care caseload | Story 18 | Configures via same Assignments surface |
| ReflectionTemplate | Stories 51, 57 | Authors and oversees |
| Visibility model | `../00_cross_cutting/visibility_model.md` | Sees everything; platform-level config |
| Org settings | Story 58 | Configures |

## Story 54: Sign in and see Admin home dashboard

### Acceptance criteria

1. Sign-in per Story 1. Multi-org Admin sees org switcher per Story 1 criterion 5.
2. Post-login is Admin dashboard, scoped strictly to org.
3. Sections: **Header** (org name, date, active programs summary), **Org snapshot** (counts: active people, memberships by role, today's completion rate, open Camper Care orders, open Maintenance tickets, active Camper Care flags), **Attention required** (criterion 5), **Recent activity** (criterion 6), **Navigation** (People/Assignments/Templates/Programs and settings/Org-wide reading views), **My reflection** card (optional per Story 60).
4. Visually distinct from operational role dashboards.
5. Attention required (six conditions Tier 1, per A2):
   1. **Stale Maintenance tickets** — open older than configured threshold
   2. **Stale Camper Care orders** — open past equivalent threshold
   3. **Unresolved Camper Care flags older than 7 days**
   4. **Pending template review** — newly published LT templates
   5. **Digest delivery failures** — Maintenance or other digest emails failed 3+ consecutive days
   6. **Translation pipeline failures** — sustained translation failures across reflections
6. Recent activity: significant events including new Memberships, deactivated Memberships, templates published/archived, Assignments changed, sensitive notes authored (count only), flags raised, order/ticket terminal closures. Rate-limited: routine submissions/notes not included.
7. Attention cards and activity entries deep-link to detail.
8. First contentful paint under 2s. Each section independent.

### Decisions

- A1: Cross-org Admin not a customer-facing role.
- A2: Six conditions Tier 1.

## Story 55: Manage people

### Acceptance criteria

1. **People** view lists all Person records in user's org.
2. Per person: name (preferred in parens if different), email, active Memberships (role + program each), status (Active/Inactive), language preference.
3. List supports: search by name/email (debounced, virtualized per Story 25), filter by role (any active Membership matches), program, status, tag.
4. Tap person opens profile: **Identity** (first/last/preferred name, DOB, email, language preference, external IDs), **Memberships** (all, active and historical, role/program/dates/tags), **Recent activity** (submissions, notes authored, orders submitted, last 30 days).
5. Admin edits identity directly. Audit-logged with actor, timestamp, diff.
6. Admin can: Add new Membership (Membership editor: role, program, start date, optional end date, tags); Edit existing Membership; Deactivate Membership (is_active=false, preserves historical content).
7. Admin creates new Person manually: identity required (name, email), at least one Membership required at creation, optional email invitation per criterion 11.
8. Admin CANNOT delete a Person. Deactivation of all Memberships is closest equivalent; reactivation permitted.
9. Email conflict at creation: shows existing record, offers to add Membership instead of duplicate.
10. Bulk imports: Campminder CSV (camp orgs) per migration Story 3.9, TBE roster CSV (religious-school) per migration Story 4.3. Dry-run preview + transactional + idempotent commits.
11. Email invitation: trigger immediately or stage and invite later (batch invitations to cohort).
12. All edits audit-logged per Story 59 audit standards.

### Decisions

- A3: Bulk Membership deactivation at end-of-program via End Program action.

## Story 56: Manage assignments

### Acceptance criteria

1. **Assignments** view, sub-tabs per assignment type:
   1. Counselor → Bunk (and JC, GC, bunk-attached Specialists)
   2. Unit Head → Counselor (Supervision; transitively UH → Bunk)
   3. Camper Care → Caseload (CamperCareCaseload via Supervision target_type=BUNK)
   4. Leadership Team → Team (Supervision to role-group)
   5. Camper → Bunk (camp orgs) / Student → Grade (religious-school orgs)
2. Each sub-tab consistent UX: two-pane (left assigner, right assignee), drag-or-tap, existing row shows parties/start/optional end/status/tags, filters by program/date/participant.
3. All time-bounded: required start, optional end, mid-season changes supported (end one, start another, contiguous or overlapping).
4. Backdated corrections supported. Per A4: backdated does NOT retroactively reattribute historical content. Historical reflections/notes/orders remain attached to original bunk/team. Audit log shows correction.
5. Bulk operations: move multiple counselors to different bunks at once, end all assignments for given program (called from Program End in Story 58), assign batch of Camper Care to caseload pattern in one action.
6. All changes audit-logged with before/after.
7. Visual indicators: Active, Ending within 7 days, Recently ended (last 30 days, de-emphasized), Future-dated.
8. Validation prevents: assigning person to role they don't hold Membership in, Membership-less assignment, date inversions.
9. Conflict warnings (not blocks): overlapping bunk assignments same Counselor (allowed for co-coverage), Camper Care caseload overlapping bunks across staff (allowed per CC2).

### Decisions

- A4: Backdated forward from correction date only.
- A5: Non-Admin assignment authority deferred to Tier 2.
- A6: Admin owns tag vocabulary; UH/LT apply existing only.

## Story 57: Author and oversee templates org-wide

### Acceptance criteria

1. Admin has same template builder access as LT per Story 51.
2. Admin's template library: every template in org across authors, grouped by Draft / Published / Archived / System-provided (per A7, shipped with platform, cloneable not editable).
3. Admin can: edit any non-system template regardless of author (new version per save), clone any (incl. system), archive any (un-archive permitted for non-superseded), author new without role restriction.
4. **Pending template review** workflow-light:
   1. Newly published LT templates appear in Admin Attention required (Story 54 criterion 5.iv).
   2. Mark template as **Reviewed** (flag, no gating) or **Needs revision** (flag with optional note to author).
   3. No approval gating per LT8.
5. Admin can **Disable active assignment** mid-period.
6. View all responses to all templates per Story 59 full read. Templates surface deep-links into Story 53 response views.

### Decisions

- A7: System-template management by Anthropic/Steve at platform release.

## Story 58: Program and org settings

### Acceptance criteria

1. **Org Settings**:
   1. **Identity** — org name, slug (read-only post-creation), org type (camp/religious_school/other)
   2. **Localization** — timezone, supported languages (subset of platform languages, Tier 1: English/Spanish/Hebrew), default UI language at org, day-rollover hour
   3. **Notifications** — Maintenance digest recipient email + send time (Story 36), reflection reminder schedules per role
   4. **Tag vocabulary** — Admin-maintained tag values
   5. **Curated lists** — Camper Care item list (Story 7), Maintenance category list (Story 8, fixed enums Tier 1 with Admin requests to platform changes)
2. **Programs** view: list with name, type, dates, member count, status (Planned/Active/Archived).
3. Per-program settings: Identity (name/slug/type/dates/description), Cadences and reminders (per-role reflection cadences, reminder schedules, expected-by time), Order age thresholds (Maintenance + Camper Care row prominence), Languages supported (subset of org-supported).
4. Admin can: Create new Program (e.g., stage Summer 2027 in March), Edit metadata anytime, **End Program** (terminal action ending all active Memberships scoped to program in single transaction per A3), Archive (preserves attached content).
5. Validation: date ranges (end >= start), cannot end Program with active Memberships unless End Program action handles deactivation in same transaction, cannot archive Program with open orders/active flags.
6. Day-rollover defaults at org-creation: camp 04:00 in org timezone, religious-school 00:00. Admin changes with confirmation: *"Changing the rollover hour affects which day reflections are counted toward. Existing data is not retroactively recategorized."*
7. Tag vocabulary: add, rename, archive. Archived remain on existing Memberships, not applicable to new. Rename updates all. Cannot delete in-use.
8. All changes audit-logged.

### Decisions

- A8: Logo only Tier 1.
- A9: Email reminder body customization out of Tier 1.

## Story 59: See everything within my org

### Acceptance criteria

1. Admin opens any role's dashboard view in org. Renders same content the role's user would see.
2. Header on role-specific view as Admin: *"Viewing as Admin — [role name]"*.
3. Admin sees all per consolidated visibility model: all reflections, all Camper Care notes (incl. sensitive), all Specialist notes (incl. sensitive), all Maintenance notes (regardless of team-only vs. submitter-visible flag), all flags + resolution history.
4. Reflections in original language with auto-translations per Story 44. Toggle to view originals only per Story 44 criterion 6.
5. Access to all aggregate views + CSV exports.
6. **Global search** from dashboard header: People (name, email, external IDs), Reflections (author, content, free-text), Notes (author, content, sensitive included), Orders/tickets (submitter, content, status, age), Templates (name, prompt content).
7. Global search scoped to active org. No cross-org.
8. Admin **edit-as-Admin** actions (editing reflection by another role, closing order/ticket directly, resolving flag normally another's authority, modifying sensitive note authored by Camper Care/Specialist) require **explicit Admin override** affordance with required reason note. Audit-logged distinctly as "Edited as Admin" with actor, action type, reason, before/after.
9. Audit trail from any content's detail view, Admin only.
10. Admin's audit trail accesses themselves logged (meta-audit).

### Decisions

- A10: PostgreSQL FTS Tier 1; sub-2-second for typical org.
- A11: Lifetime of org audit retention.

## Story 60: Submit Admin reflection (optional)

### Acceptance criteria

1. Admin reflection template assigned via Story 52: **My reflection** card per Story 16.
2. No template assigned: card does NOT appear. No pressure to reflect.
3. Where present: same rules as other self-reflections (edit window until rollover, prior periods read-only, history view).
4. Visibility: user, other Admins in same org, platform super-admin scope.
5. NOT visible to non-Admin roles incl. LT.
6. **Private** toggle per Story 50 criterion 11: restricts to author + platform support.

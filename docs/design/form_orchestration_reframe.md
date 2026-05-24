# Form Orchestration Reframe — Design Doc

**Status:** Draft — pending Steve's review of open questions in §6
**Author:** Steve Bresnick (drafted with Claude, 2026-05-23)
**Target window:** Post-Crane-Lake-Summer-2026 stabilization → before Crane Lake Summer 2027 prep (roughly August–November 2026)
**NOT in scope for June 5, 2026:** This doc describes a multi-week arc that comes AFTER the existing role flows are live for Summer 2026. Nothing in this doc should distract from getting `7_6`, `7_7`, …, `7_18` shipped by June 5.

---

## 1. The reframe in one paragraph

BunkLogs today has nine fully-tightened role flows, each with its own hard-coded set of forms (camper reflection, self-reflection, specialist note, etc.). The reframe makes the **form** the platform's primary configurable object. A form (a published `ReflectionTemplate`) becomes assignable, with explicit configuration of who fills it out, about whom, how often, and whether it's required. Tasks on dashboards are *derived* from those assignments. Landing pages are *role-tuned views* over the same substrate. Adding a new survey or rating instrument becomes a builder-and-assign action, not a code change.

---

## 2. What already exists (gap analysis)

**Updated 2026-05-24 after codebase audit.** The original draft of this section underestimated how much form-orchestration substrate is already shipped. The single biggest finding: `TemplateAssignment` already exists as a Django model with a full API surface. What §3 of the original draft called "FormAssignment" is mostly an extension of `TemplateAssignment`, not a new model. This section is updated to reflect that.

### 2.1 Already shipped

| Capability | Where it lives | Notes |
|---|---|---|
| `TemplateAssignment` model | `core.models.TemplateAssignment` | Has template FK, target_type (role/individuals/tag_group), target_payload (JSON), start_date, end_date, cadence_override, status (scheduled/active/ended/cancelled), replaces (chain), created_by. OrgScopedManager. |
| Assignment CRUD API | `api/leadership_team/assignments.py` | POST creates with conflict detection (replace/run_both/cancel); PATCH edits end_date safely; DELETE cancels scheduled. Audit-logged. |
| `resolve_members(assignment, as_of_date)` helper | same file | Materialises an assignment into a queryset of Memberships per its target_type. |
| Conflict resolution (FA3's pattern) | same file | End-date prior + create new + chain via `replaces` FK. Already implemented. |
| Template versioning & lifecycle | `ReflectionTemplate.version` + status enum | Draft → published → archived. Clone, fork-on-edit, language gap checks all working. |
| Template builder UX (LT-scoped) | `frontend/src/pages/leadership-team/...`, prompt `7_12` | Mature; FA-E will extend this with an "Assign form" dialog. |
| Author/subject role filtering on templates | `ReflectionTemplate.author_role_filter`, `subject_role_filter` | Already declares who fills it out and who it's about. |
| Group-based subject scoping | `AssignmentGroup` + `AssignmentGroupMembership` | Bunk/unit/caseload/cohort all already modeled. |
| `subject_mode` field | `ReflectionTemplate.subject_mode` (`self`, `single_subject`, `multi_subject`, `group`) | The four shapes of "about whom" are already declared. |
| `assignment_scope` field | `ReflectionTemplate.assignment_scope` | "One per subject in group" vs. "one per group" vs. "no group context" already modeled. |
| `required_per_subject_per_period` | On `ReflectionTemplate` | Per-template numeric required-ness. |
| `Reflection.team_visibility` axis | + `ReflectionTemplate.supports_privacy` | Privacy toggle exists and is tested. |
| RBAC two-axis design | `Membership.role` × `Membership.capability` | Settled; permission checks stable. |
| Per-role visibility paths | `core.permissions.visibility.reflections_visible_to` | Six visibility paths settled. |
| Per-role dashboard endpoints | `api/{counselor,unit_head,specialist,camper_care,leadership_team,kitchen_staff,madrich,admin_flow}/dashboard.py` + companion `bunk_dashboard.py`, `camper_dashboard.py`, `team_dashboard.py` | **Each one hard-codes its template lookups via per-role helpers in `common.py`.** This is the main surface area FA-B has to refactor. |
| Notes module spec | `docs/user_stories/10_notes_platform/` + `migration_prompts/7_19_notes_platform.md` | Designed, not yet implemented. |

### 2.2 What is genuinely new for the reframe

| Missing piece | Why it's needed | Rough size |
|---|---|---|
| **`assignment_group` FK on `TemplateAssignment`** | Today TemplateAssignment targets role, specific individuals, or a tag group — but cannot target "every counselor on Bunk Maple". FA1 requires per-group assignment. Solved by adding a nullable `assignment_group` FK that, when set, narrows the resolved audience to Memberships within that group. | Small |
| **`is_required` flag on `TemplateAssignment`** | Today every assignment is implicitly required. FA5 separates required (tasks) from optional (form library). Solved by adding a boolean. | Trivial |
| **`title` field on `TemplateAssignment`** | FA1 specifies a per-assignment display title for dashboard widgets, distinct from `template.name`. Today the dashboard label is derived from the template, which forces a new template version when the LT user just wants a different label. | Small |
| **Per-role dashboard refactor** | The hard-coded template resolvers in each role's `common.py` (e.g., `camper_reflection_template()`, `counselor_self_template()`) need to consult `TemplateAssignment` rows instead of querying `ReflectionTemplate` directly. This is the main work of Wave 1. | Medium |
| **`assignment_group` resolution in `resolve_members`** | The existing helper handles role/individuals/tag_group targets. It needs a new branch for the `assignment_group` case (resolve to Memberships whose role matches the template's `author_role_filter` AND who are active in the group). | Small |
| **Admin capability gate on assignment endpoints** | Today the assignments API restricts mutation to `program_lead` capability. FA7 widens that to `program_lead OR admin`. | Trivial |
| **Seeding for Summer 2026** | TemplateAssignment rows for Crane Lake Summer 2026 don't exist yet because the per-role dashboards haven't been reading from them. The seeding command creates these as part of FA-S. | Small |
| **"Assign form" dialog in builder UX** | Today the assignments API exists but the LT template builder UX does not surface an assignment step. FA1's flow (publish template → click "Assign form" → dialog with group, title, cadence, required, dates) needs a new UI surface. | Medium-Large |
| **Numeric color-coded tabular display** | The platform has individual `TrendCell` and grids for rating-group data, but no general "render any numeric form responses as a color-coded sortable table" component scoped to a subject. | Medium |
| **Palette library** | FA4 specifies a library of named palettes per scale length. None exists today. | Small-Medium |
| **Subject landing page (form-aware profile view)** | Camper profiles exist; the form-aware aggregation per FA6 ("every form ever filled out about this subject") is new. | Medium-Large |
| **Author-side "tasks for me, grouped by assignment" widgets** | Existing dashboard rendering is per-role and ad-hoc. The reframe wants a unified widget framework driven by assignments. | Medium-Large |

---

## 3. The proposed data model addition

**Updated 2026-05-24.** The original draft proposed a new `FormAssignment` model. The codebase audit revealed `TemplateAssignment` already exists with most of the needed shape. This section now describes the **extension** of `TemplateAssignment` rather than a new model.

### 3.1 Three small additions to `TemplateAssignment`

```python
class TemplateAssignment(models.Model):
    # === EXISTING (unchanged) ===
    organization = ForeignKey(Organization)
    program = ForeignKey(Program)
    template = ForeignKey(ReflectionTemplate)
    target_type = CharField(choices=[
        ('role', 'Role (dynamic)'),
        ('individuals', 'Individual memberships (static)'),
        ('tag_group', 'Tag group (dynamic)'),
        ('assignment_group', 'Assignment group (dynamic)'),  # NEW
    ])
    target_payload = JSONField()
    start_date = DateField()
    end_date = DateField(null=True)
    cadence_override = CharField(null=True)
    replaces = ForeignKey('self', null=True)
    status = CharField(choices=Status.choices)
    created_by = ForeignKey(Membership)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    # === NEW ===
    assignment_group = ForeignKey(
        AssignmentGroup,
        null=True,
        blank=True,
        on_delete=CASCADE,
        help_text=(
            "When target_type='assignment_group', the group this assignment "
            "targets. Memberships are resolved to those whose role matches "
            "the template's author_role_filter AND who hold an active "
            "AssignmentGroupMembership in this group with role_in_group='author'."
        ),
    )
    is_required = BooleanField(
        default=True,
        help_text=(
            "When True, the assignment produces tasks in the per-role "
            "dashboards. When False, it appears in the role's optional "
            "forms library and does NOT affect the 'all set' state."
        ),
    )
    title = CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=(
            "Per-assignment display title for dashboard widgets. "
            "Falls back to template.name when blank."
        ),
    )
```

### 3.2 What `target_type='assignment_group'` resolves to

The existing `resolve_members(assignment, as_of)` helper in `api/leadership_team/assignments.py` gains a new branch:

```python
if target_type == TemplateAssignment.TargetType.ASSIGNMENT_GROUP:
    group_id = (assignment.assignment_group_id or
                (assignment.target_payload or {}).get('assignment_group_id'))
    if not group_id:
        return base.none()
    # Resolve to Memberships whose role matches the template's author_role_filter
    # AND who are active in the group as authors.
    author_roles = assignment.template.author_role_filter or []
    if not author_roles:
        return base.none()
    author_person_ids = AssignmentGroupMembership.objects.filter(
        group_id=group_id,
        role_in_group='author',
        is_active=True,
    ).values_list('person_id', flat=True)
    return base.filter(person_id__in=author_person_ids, role__in=author_roles)
```

Note: `assignment_group_id` is stored on the FK column, not in `target_payload`, even though the existing `role` and `tag_group` types use the payload. This is an intentional break from the existing pattern — a foreign key with a database-level constraint is cleaner than a JSON-encoded ID, and the migration path is straightforward.

### 3.3 What this *doesn't* change

Critically, the extension is **additive**:

- `ReflectionTemplate` schema is untouched. All existing template-builder, versioning, and language-gap logic continues to work.
- `Reflection` is untouched. Submitted reflections continue to reference `template_id` directly.
- The capability/role model is untouched.
- The visibility model is untouched.
- The Notes module (prompt `7_19`) is untouched.
- The existing `target_type` values (role, individuals, tag_group) continue to work exactly as today. Existing seeded data, if any, remains valid.

### 3.4 How task derivation changes

Today each role's `common.py` has helpers like `camper_reflection_template()` that query `ReflectionTemplate` directly with hard-coded filters. After Wave 1, those helpers consult `TemplateAssignment` rows instead:

```python
# BEFORE: hard-coded template lookup
def camper_reflection_template(organization, program):
    return ReflectionTemplate.all_objects.filter(
        subject_mode='single_subject',
        cadence='daily',
        assignment_group_types__contains=['bunk'],
    ).first()

# AFTER: assignment-driven lookup
def camper_reflection_template_for_bunk(viewer, organization, program, bunk):
    # Find the active TemplateAssignment targeting this bunk + viewer's role
    # that produces a single_subject template; return its template.
    assignment = resolve_active_assignment(
        program=program,
        target_assignment_group=bunk,
        viewer_role='counselor',
        as_of=get_today(organization),
    )
    return assignment.template if assignment else None
```

The key point: **the dashboard endpoints' API contracts don't change**. They still return the same shape of payload. Only the internal resolution logic changes.

### 3.5 No backfill (per FA10(a))

Under the aggressive rollout, there is no live data to migrate. The Summer 2026 launch is the *first* time the new task derivation runs against real users. Seeding (FA-S) creates the TemplateAssignment rows that the new dashboards need, in the same release that ships the dashboards' new resolution logic.

If the existing per-role dashboard logic is producing tasks today (against seeded test data on staging), that test data will produce no tasks after FA-B ships until FA-S seeds the assignments. This is expected and is part of the cutover.

---

## 4. The landing-page model

The reframe says: "every role has a landing page that's a tuned view over the form-orchestration substrate." Defining what each landing page *is* is the design work.

### 4.1 Subject landing pages (for people who are subjects of forms)

Examples: camper landing page, counselor landing page (when viewed *as* a subject — e.g., a UH writing about them).

Common shape:

- **Header**: photo (or placeholder), name, ID number, group memberships (linked), profile metadata
- **Form responses widget**: tabular display, one row per submitted reflection where this person is the subject, numeric fields color-coded
- **Specialist notes widget**: Specialist notes about this subject (per visibility model)
- **Notes widget**: Notes referencing this subject as `camper_reference` (per Story 66 criterion 2.iv)
- **Trend widgets**: rating-group categories over time (already exists as `TrendCell` / Subject Trend Grid; reused)

Each widget is conditionally rendered based on the viewer's visibility into the relevant content type.

### 4.2 Author landing pages (for people whose main job is filling out forms)

Examples: counselor landing page (the typical "what do I owe today" view), Madrich landing page, Specialist landing page.

Common shape:

- **Header**: profile, group memberships I'm an author in, current program/session
- **Assignment widgets**: one per active `FormAssignment` targeting this person's role
  - Header: assignment name (the template name), cadence, required/optional flag
  - Body: list of subjects (when `subject_mode=single_subject` or `multi_subject`) or "you" (when `subject_mode=self`) or "this group" (when `subject_mode=group`)
  - Gauge: "7/12 completed this period"
  - Color-coded status per subject: green (done), yellow (pending), gray (not yet due)
- **Completion celebration**: rendered when all required assignments for the period are complete (Story 9 pattern generalized)
- **Tickets widget**: orders submitted (Camper Care / Maintenance) with status (existing surface; integrated)
- **Notes widget**: unread Notes (existing surface from `7_19`; integrated)
- **Quick-action buttons**: Submit a Note, Submit an order — surfaces consistent across the platform

### 4.3 Supervisor landing pages

Examples: UH landing page, Camper Care landing page, LT landing page.

Common shape:

- **Header**: profile, what I supervise (units, caseload, groups)
- **Supervised-group widgets**: one per supervised group
  - Header: group name, group type, supervisor's primary contact for this group
  - Body: completion rollup across all required assignments for this group, with drill-down to per-author and per-subject status
  - Attention badges: ones that today drive UH attention badges (help requested, off-camp, bunk concerns, low completion) become the generalized "attention" surface, derived from assignment statuses
- **Personal assignment widgets**: assignments where the supervisor is themselves the author (UH self-reflection, etc.) — rendered same as author landing pages
- **Notes widget**, **Tickets widget**: same as author pages

### 4.4 Operator landing pages

Example: Maintenance landing page.

These don't fit the author/supervisor/subject shape neatly. They're workflow-driven (ticket queue) rather than form-driven.

- **Ticket queue**: tickets assigned to me, with status, priority, in-app notes
- **Notes widget**: same as author pages
- **Optional personal assignment widgets**: if Maintenance ever has self-reflection assignments (kitchen-staff-style), they appear here

The maintenance landing page in the reframe is mostly the *existing* maintenance flow with the Notes module integrated — not a substantial redesign.

---

## 5. Mapping to existing stories and prompts

For traceability, here's where the reframe touches existing canonical work:

| Existing artifact | What the reframe changes |
|---|---|
| `docs/user_stories/01_counselor/02_dashboard.md` (Story 2) | Will be revised to render assignment-driven widgets. Header and "all set" semantics carry forward. |
| `docs/user_stories/02_unit_head/...` | UH dashboard gets supervised-group widgets driven by assignments. |
| `docs/user_stories/04_specialist/...` | Specialist note creation may eventually become a `FormAssignment` flow. Out of scope for v1 of the reframe; revisit. |
| `docs/user_stories/07_leadership_team/...` (template builder Stories 49–53) | The "Save as Form" assignment dialog extends the builder UX. |
| `docs/user_stories/10_notes_platform/...` | No change. Notes is a hard dependency; reframe lands on top. |
| `migration_prompts/3_19_my_tasks.md` (or wherever the my-tasks endpoint shipped) | The endpoint's data source changes from implicit-template-applicability to `FormAssignment` joins. Cutover is part of the reframe rollout. |
| `migration_prompts/7_12_template_builder.md` | Extended to add the "Save as Form" UX; existing publish/clone/version flows untouched. |
| `migration_prompts/7_6_counselor_flow.md`, `7_7_unit_head_flow.md`, etc. | Their dashboard surfaces get rewired to consume the new widget framework. Not rewritten — rewired. |

---

## 6. Open questions — RESOLVED

**Status:** All ten decisions resolved by Steve on 2026-05-23. Resolutions are canonical in `docs/user_stories/00_cross_cutting/decisions.md` under the **Form Assignment** section (entries FA1–FA10). This section is preserved as a historical record of the reasoning at the time of the design draft.

If you are reading this document for the first time and want to know what was decided, **read `decisions.md`, not this section.**

### Resolutions at a glance

| # | What was decided | Notes |
|---|---|---|
| FA1 | **Explicit assignment only.** Publish does nothing on its own. "Assign form" dialog captures: target group, title, cadence, required flag, start date, end date. | The hybrid I originally recommended was rejected as too implicit. Steve's call is cleaner. |
| FA2 | **Multiple assignments per template allowed.** | Accepted recommendation. |
| FA3 | **End-date-and-create-new for cadence/scope changes.** Never destructive in-place. | Accepted recommendation. |
| FA4 | **Palette-based color coding.** A library of named palettes; each declares its scale length; builder offers scale-compatible palettes for each field. Custom color-per-value override allowed. Numeric value + hatched pattern overlay for accessibility. Initial 5-point palette specified with hex values. | Steve specified the 5-point palette explicitly; "library of named palettes" expands the original "lower_is_better flag" recommendation. |
| FA5 | **Optional assignments surfaced separately from tasks.** Don't affect "all set." | Accepted recommendation. |
| FA6 | **Subject landing pages for non-campers: yes, visibility-filtered.** | Accepted recommendation. |
| FA7 | **LT and Admin can create/modify assignments.** UH view-only. | Steve expanded from LT-only to LT+Admin. Requires widening the existing template-builder permission gate. |
| FA8 | **Notes stay separate from FormAssignment-driven tasks.** | Accepted recommendation. |
| FA9 | **Tickets/orders stay separate from FormAssignment.** | Accepted recommendation. |
| FA10 | **AGGRESSIVE rollout: ship FormAssignment substrate BEFORE June 5, 2026.** | Steve chose the aggressive path over the conservative "ship after June 5" alternative. See §7 for resequenced work plan. |

### Implications of FA10(a) being chosen

FA10's resolution is the single decision with the largest impact on the rest of the doc. Specifically:

1. **The reframe is no longer a "post-Summer-2026" arc.** It's on the June 5 critical path.
2. **There is no backfill step.** Existing seeded test data on the new architecture is overwritten as part of the cutover. No live production data exists on the new architecture yet (per Steve's reasoning: RBAC still under test with seeded data).
3. **Existing canonical user stories (Stories 2, 3, 5, 9, UH attention badges, etc.) must be re-verified against the new substrate before June 5.** Most will likely pass without code change; this is a re-verification pass, not a rewrite pass.
4. **Wave 1 is FA-A, FA-B, FA-S** — three prompts totaling 9–15 hours (revised after codebase audit revealed `TemplateAssignment` already exists with most of the needed shape).
5. **The pre-June-5 budget has real slack now.** 9–15 hours fits comfortably in 20–30 hours of available time. See §7 risk section for what could still go wrong.

## 7. Proposed sequencing — REVISED FOR FA10(a)

Under FA10(a), the FormAssignment substrate must ship before June 5, 2026 staff onboarding. This re-sequences the work into two distinct waves with very different urgency levels.

### Wave 1: Pre-June-5 critical path (MUST ship)

**Resized 2026-05-24 after codebase audit revealed `TemplateAssignment` already exists.** Wave 1 is now substantially smaller than the original estimate — the model exists, the CRUD API exists, the conflict-resolution pattern exists. What remains is extending the model with three fields, refactoring the per-role dashboard helpers, and seeding rows for Summer 2026.

| # | Prompt | Goal | Size |
|---|---|---|---|
| FA-A | **Extend `TemplateAssignment` and `resolve_members`** | Add `assignment_group` FK, `is_required` flag, `title` field. Add `'assignment_group'` to `target_type` choices. Migration. Extend `resolve_members(assignment, as_of)` with the new branch. Widen the assignments API permission gate from `program_lead` to `program_lead OR admin` (FA7). Tests. | 3–5 hrs |
| FA-B | **Per-role dashboard refactor** | Replace hard-coded template resolvers in each role's `common.py` with TemplateAssignment-aware lookups. Roles in scope: counselor, unit_head, specialist, camper_care, leadership_team, kitchen_staff, madrich, admin_flow. Each role's dashboard endpoint payload contract stays identical; only internal resolution changes. Updated tests. | 4–6 hrs |
| FA-S | **Seed TemplateAssignments for Summer 2026** | Idempotent management command that creates the assignment rows Crane Lake Summer 2026 needs: camper bunk log, counselor self-reflection, UH reflections, wellness team reflections, kitchen staff reflections, and any others currently produced by the implicit derivation. Run on staging, verify with Alyson, then production. | 2–4 hrs |
| | **Wave 1 total** | | **9–15 hrs** |

### Wave 1 risk surface

Not honest about this would be malpractice. Even with the smaller-than-expected scope, FA10(a) carries real risk:

1. **Eight per-role dashboard files to refactor.** The work is mechanical but the surface area is wide. A subtle bug in one role's resolver could break that role's dashboard silently. Mitigation: each role gets its own commit within FA-B with its own tests passing.
2. **Existing canonical user stories must be re-verified.** Stories 2, 3, 5, 9, the UH attention-badges story, etc. are written against the implicit-template-applicability model. After Wave 1 lands, each canonical story's acceptance criteria need a pass-through verification: do they still hold on the new substrate? Estimated 3–5 hours of careful reading and test execution. **This time is not in the 9–15 hour estimate above.**
3. **No live customers yet on the new architecture.** This is what makes FA10(a) viable. But it also means if Wave 1 ships broken, you find out during Crane Lake staff onboarding, not before. There's no "is it working in production?" signal until the very moment it has to work. Mitigation: thorough staging verification with Alyson before deploying to production.
4. **Rollback plan needed.** If Wave 1 ships broken and is detected pre-go-live, the rollback path is: revert the migration, revert the dashboard refactor commits, leave the implicit-derivation code intact. Cost: a few hours. Plan for it explicitly.
5. **Helena's buy-in is the single biggest external constraint.** Per the financial model, every other variable can flex but family time cannot. With the smaller Wave 1 scope this is less of an immediate risk, but still applies if the work expands during execution.

### Wave 1 acceptance criteria

Wave 1 is "done" when ALL of the following are true:

- FormAssignment model migrations applied cleanly on staging
- `my-tasks` endpoint returns identical task lists for every seeded test counselor between the staging environment with FormAssignment and a snapshot of staging with the old logic (this comparison is the one-time "shadow check" before old code is removed)
- All ten existing role-flow stories' acceptance criteria pass on the new substrate (re-verification pass)
- Backend test suite passes (`pytest`)
- Frontend test suite passes (`npm test`)
- The seeding command produces a deterministic, reviewed set of FormAssignment rows that Alyson signs off on for Summer 2026

If any of these fail by **June 3**, the contingency is to ship without Wave 1 — revert to the existing implicit-derivation code, plan FA10(b) post-summer, and protect June 5.

### Wave 2: Post-June-5 reframe completion (target: late July–early September)

The rest of the reframe — the UX work that makes FormAssignment user-visible. None of this is on the June 5 critical path. Sequenced to land before Summer 2026 ends and before TBE's September launch.

| # | Prompt | Goal | Size |
|---|---|---|---|
| FA-E | **"Assign form" dialog in builder** | Extend LT template builder UX with the explicit assignment step per FA1. Cadence picker, group scoping, required flag, start/end dates. Permission gate widened to LT + Admin per FA7. | 6–9 hrs |
| FA-P | **Palette library and color-coded rating fields** | Implement the named-palette library per FA4. Builder UI surfaces palette picker per field; custom color-per-value override allowed. Initial 5-point palette ships built-in. | 4–6 hrs |
| FA-F | **Numeric color-coded tabular component** | Reusable subject-level form-response grid using the palette library. Sortable columns, drill-down to individual reflections. Numeric value + hatched pattern overlay for accessibility (FA4). | 5–8 hrs |
| FA-G | **Author landing page revisions** | Counselor, Madrich, and Specialist landing pages rewired to consume FormAssignment-driven widgets. "Optional forms" library section added per FA5. | 7–11 hrs |
| FA-H | **Subject landing pages** | Camper landing page first (highest-value); counselor-as-subject lens second per FA6. Tabular display + specialist notes + Notes + profile. | 7–11 hrs |
| FA-I | **Supervisor landing page revisions** | UH and Camper Care landing pages rewired. Generalized attention badges. | 6–9 hrs |
| | **Wave 2 total** | | **35–54 hrs** |

### Critical ordering constraints

1. **Wave 1 ships as an atomic block before June 5.** No partial states.
2. **Wave 2 cannot start until Wave 1 is in production and the existing role flows are running on it without regression for at least one week.** This is the validation that FA10(a) actually worked.
3. **`7_19` (Notes) must ship before any of FA-G, FA-H, FA-I.** The landing pages assume Notes is available. Notes is currently sized at 10–14 hours; it cannot be on the June 5 critical path. Target Notes for late June after Wave 1 stabilizes.
4. **FA-P (palette library) must ship before FA-F (tabular component).** FA-F uses palettes.
5. **FA-G, FA-H, FA-I are parallelizable** after FA-F lands.

### Total work footprint

| Wave | Hours | When |
|---|---|---|
| Wave 1 (TemplateAssignment extension + dashboard refactor + seeding) | 9–15 | Before June 5, 2026 |
| Re-verification of existing stories | 3–5 | Before June 5, 2026 |
| `7_19` Notes module | 10–14 | Late June 2026 |
| Wave 2 (reframe UX completion) | 35–54 | July–September 2026 |
| **Total** | **57–88 hrs** | **May 24 – September 2026** |

At 10–15 hours/week, this is 4–9 months of BunkLogs time. Roughly aligned with the Summer 2026 → TBE September launch arc. Wave 1 fits in ~1 week of BunkLogs time with real slack.

### What this does NOT cover

- Cross-program assignments (assignments that span multiple Programs in one Organization). Out of scope; not a real customer need yet.
- Template marketplace / sharing assignments across Organizations. Out of scope; tier 3 grant-funded scope.
- Auto-suggested assignments based on customer onboarding answers. Out of scope; nice-to-have for a future prompt set.

---

## 8. Decision-by-decision summary for the `decisions.md` append

If §6 recommendations are accepted, the following entries get added to `docs/user_stories/00_cross_cutting/decisions.md` under a new **Form Assignment** section:

| # | Decision | Resolution | Status |
|---|---|---|---|
| FA1 | Implicit vs explicit assignment | Hybrid — publish creates a default program-wide assignment; builder UI allows narrowing to groups before publish | ⏳ |
| FA2 | Multiple assignments per template | Allowed; different `(assignment_group, cadence)` tuples coexist | ⏳ |
| FA3 | Mid-flight assignment changes | End-date old + create new (no destructive in-place edits); audit-logged | ⏳ |
| FA4 | Numeric color-coding | Per-field, scale-derived thresholds, `lower_is_better` flag on rating-group fields, numeric value always rendered + pattern overlay for accessibility | ⏳ |
| FA5 | Optional assignments | Surfaced separately from tasks; do not affect "all set" semantic | ⏳ |
| FA6 | Subject landing for non-campers | Yes, visibility-filtered; supervisors_only content shows as placeholder | ⏳ |
| FA7 | Who can create assignments | LT (`program_lead`) only; UH and Admin can view but not modify | ⏳ |
| FA8 | Notes in tasks queue | Stays separate from FormAssignment-driven tasks | ⏳ |
| FA9 | Tickets/orders relative to FormAssignment | Stays separate | ⏳ |
| FA10 | Backfill cutover strategy | Shadow mode for a week of staging traffic; atomic production cutover with rollback plan | ⏳ |

---

## 9. What to do with this doc

Once Steve has reviewed and resolved (or amended) the open questions in §6:

1. Move the resolved decisions to `docs/user_stories/00_cross_cutting/decisions.md` under a new Form Assignment section.
2. Update `docs/user_stories/README.md`'s status table to note the reframe as a planned post-Summer-2026 arc.
3. Add a new directory `docs/user_stories/11_form_assignment/` with stories for each of the prompts FA-A through FA-I, written in the same shape as the existing role-flow stories.
4. Begin writing the prompts FA-A onward, **but not until 7_19 (Notes) has shipped and the existing Summer 2026 role flows are stable in production.**

This doc itself stays in `docs/design/` as the "why" reference. Stories in `11_form_assignment/` will be the "what." Prompts will be the "how."

---

## 10. What this doc deliberately doesn't do

- **Doesn't pretend the reframe is small.** It's 6–10 weeks of work. Naming that upfront protects against scope creep into Summer 2026.
- **Doesn't reinvent the form-builder.** The existing builder (per `docs/template_builder.md`) is mature. The reframe extends it; it does not rewrite it.
- **Doesn't second-guess the capability model.** `Membership.capability` is settled and the reframe stays within its bounds.
- **Doesn't propose new content types.** No "Surveys are different from Reflections." A survey is just a `ReflectionTemplate` with `subject_mode=self` and `cadence=one_time`. The reframe collapses these into one substrate, which is the whole point.
- **Doesn't address mobile-vs-desktop UX in detail.** The landing pages have to work on phones; the design notes assume mobile-first per existing conventions. The actual layout work happens in the stories and prompts.

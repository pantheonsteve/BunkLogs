# Subject Dashboard — Design Document and Data Model Audit

**Prompt:** 3.13  
**Status:** Design only — no code changes, no migrations  
**Date:** 2026-05-26  
**Author:** Engineering (for review by Alyson / Brent before implementation)

---

## Executive Summary

The subject dashboard is the central place where everything known about a single person — a camper at Crane Lake, a Madrich at Temple Beth-El, eventually any tracked participant — is surfaced for counselors, specialists, unit heads, and leadership to consult before check-ins, care conversations, and parent calls.

The good news: the data model is already closer than it looks. Crane Lake's old per-camper daily logs (`BunkLog`) mapped one-to-one to campers, and the new `Reflection` model preserves that fidelity — one reflection row per subject per day — while also supporting self-reflections (where the author is the subject) and multi-subject batch submissions. The `Reflection.person` ambiguity called out in the prompt has **already been resolved** in migration `0010`: the field was renamed `subject` and a separate `author` field was added. A skeleton subject dashboard API and frontend already exist.

What is missing is the **ad-hoc notes layer** — a `SubjectNote` model for observations that are not template-driven (swim instructor quick note, wellness check-in, camper care observation). This document audits the legacy model, confirms the current model state, evaluates three design options for subject linkage, proposes the `SubjectNote` model, maps dashboard access to the capability layer, and defines the minimum viable scope for Crane Lake Summer 2026.

All decisions that require Alyson or Brent's input before implementation can begin are surfaced in the [Open Questions](#open-questions) section.

---

## 1. Audit — Old Crane Lake Models

### File locations

| Model | File |
|-------|------|
| `BunkLog` | `backend/bunk_logs/bunklogs/models.py` |
| `CamperBunkAssignment` | `backend/bunk_logs/campers/models.py` |
| `Camper` | `backend/bunk_logs/campers/models.py` |
| `Bunk`, `Unit`, `Session` | `backend/bunk_logs/bunks/models.py` |

### One BunkLog per camper per day (not per bunk)

The `BunkLog` model is keyed to `CamperBunkAssignment` + `date`:

```python
class BunkLog(TestDataMixin):
    bunk_assignment = models.ForeignKey(
        "campers.CamperBunkAssignment",
        on_delete=models.PROTECT,
        related_name="bunk_logs",
    )
    date = models.DateField()
    class Meta:
        unique_together = ("bunk_assignment", "date")
```

Since `CamperBunkAssignment` links one `Camper` to one `Bunk` for a session, the `unique_together` constraint enforces exactly **one log per camper per day**. There is no bunk-level aggregate row. A counselor with 8 campers submits 8 separate `BunkLog` rows.

### Per-camper field shape: scalar columns, no JSON

All per-camper data lives directly on the `BunkLog` row as typed database columns:

| Field | Type | Purpose |
|-------|------|---------|
| `social_score` | `PositiveSmallIntegerField(1–5, nullable)` | Social behavior rating |
| `behavior_score` | `PositiveSmallIntegerField(1–5, nullable)` | Behavior rating |
| `participation_score` | `PositiveSmallIntegerField(1–5, nullable)` | Participation rating |
| `not_on_camp` | `BooleanField` | Camper absent that day |
| `request_camper_care_help` | `BooleanField` | Flag for camper care team |
| `request_unit_head_help` | `BooleanField` | Flag for unit head |
| `description` | `TextField` | Narrative note |
| `counselor` | FK → `AUTH_USER_MODEL` | Who submitted |
| `date` | `DateField` | Log date |

No JSON blob. No related "per-camper line items" table. Derived properties like `needs_attention` and `overall_score` are computed via `@property` methods on the same model instance.

### Legacy "all data about this camper" query pattern

The primary API path is `CamperBunkLogViewSet.get` in `backend/bunk_logs/api/views.py` (line ~1428), registered at `campers/<camper_id>/logs/`:

```python
camper = Camper.objects.get(id=camper_id)
assignments = CamperBunkAssignment.objects.filter(camper=camper)
bunk_logs = BunkLog.objects.filter(
    bunk_assignment__in=assignments,
).select_related("bunk_assignment__bunk")
```

Response shape: `{camper: {...}, bunk_logs: [...], bunk_assignments: [...]}`.

There was no cross-context note layer (no specialist observations, no wellness notes, no camper care freeform entries). The only narrative data was `description` on `BunkLog`.

### Old fields with no equivalent in the new design

The new `Reflection.answers` JSON replicates the old scalar columns via `camper_scores` (rating_group) and `daily_report` (textarea). One gap exists:

| Legacy field | New equivalent | Gap? |
|---|---|---|
| `social_score`, `behavior_score`, `participation_score` | `answers["camper_scores"]["social/behavior/participation"]` | **None** — fully covered |
| `request_camper_care_help` | `answers["request_camper_care_help"]` yes/no field | **None** — fully covered |
| `request_unit_head_help` | `answers["request_unit_head_help"]` yes/no field | **None** — fully covered |
| `not_on_camp` | `answers["not_on_camp"]` yes/no field | **None** — fully covered |
| `description` | `answers["daily_report"]` textarea | **None** — fully covered |
| `counselor` FK (User) | `author` (Person) + `submitted_by` (User) | **Richer** — new model separates "who wrote it" from "who clicked submit" |
| `bunk_assignment` → unit/bunk context | `assignment_group` FK | **Richer** — hierarchical groups |
| No ad-hoc notes layer | **Does not exist yet** | **GAP** — see SubjectNote design below |

The one genuine gap is the absence of an ad-hoc observation model. The old system had none; the new system needs one because the dashboard prompt requires it and because specialist roles (swim, athletics, arts) and camper care staff need a place to record observations that are not template-driven.

---

## 2. Audit — Current New-Model State for Subject Queries

### `Reflection.person` ambiguity: already resolved

The original `Reflection` model (migration `0006`) had a `person` FK that was ambiguous — it was used as the submitter (counselor) in some places and logically referred to the subject in others.

**Migration `0010`** (`backend/bunk_logs/core/migrations/0010_assignmentgroup_assignmentgroupmembership_and_more.py`, lines 228–268) resolved this explicitly:

```python
migrations.RenameField(
    model_name="reflection",
    old_name="person",
    new_name="subject",
),
migrations.AddField(
    model_name="reflection",
    name="author",
    field=models.ForeignKey(
        ...,
        help_text="Who FILLED OUT this reflection (may equal subject for self-reflection)",
    ),
),
```

**Migration `0011`** backfilled `author_id = subject_id` for all existing rows (which were all self-reflections at the time of the migration).

**Current model state** (`backend/bunk_logs/core/models.py`, lines ~855–968):

| Field | Meaning |
|-------|---------|
| `subject` | FK to `Person` — **who the reflection is ABOUT** (nullable when `subject_mode='group'`) |
| `author` | FK to `Person` — **who filled out the form** (equals `subject` for self-reflections) |
| `submitted_by` | FK to `User` — **audit trail** for who clicked "Submit" |
| `subject_group` | FK to `AssignmentGroup` — set when `subject_mode='group'` |
| `submission_id` | UUID — **groups multi-subject submissions** (one row per subject, same UUID) |

**Zero remaining usages of `reflection.person`** in the runtime codebase. All code uses `reflection.subject`, `reflection.subject_id`, `reflection.author`, `reflection.author_id`, or `reflection.submitted_by`.

Example from `backend/bunk_logs/api/counselor/self_reflection.py` line 269:
```python
if reflection.author_id != viewer.id or reflection.subject_id != viewer.id:
    raise PermissionDenied(...)
```

Example from `backend/bunk_logs/api/dashboards/subject.py` lines 187–188:
```python
Reflection.objects.filter(
    subject_id=person_id,
    ...
)
```

### Are there reflections with subject ≠ author in dev/staging?

Yes. The seed command (`backend/bunk_logs/core/management/commands/seed_rbac_test_users.py`, lines 725–731) creates counselor-authored reflections where `author` is the counselor Person and `subject` is a camper Person. The `answers` for these look like:

```json
{
  "not_on_camp": "no",
  "request_unit_head_help": "no",
  "request_camper_care_help": "no",
  "camper_scores": {"behavior": 4, "participation": 5, "social": 4},
  "daily_report": "RBAC fixture: solid day across the bunk."
}
```

This is the per-camper daily reflection shape, authored by a counselor (`author = counselor_person`), about a camper (`subject = camper_person`). The data is scoped to one subject per row.

### `answers` JSON shape for a counselor daily reflection

The `answers` field is a **flat dictionary** keyed by template field `key`s. For the Crane Lake counselor daily template:

```json
{
  "not_on_camp": "no",
  "request_unit_head_help": "no",
  "request_camper_care_help": "no",
  "camper_scores": {
    "behavior": 4,
    "participation": 5,
    "social": 3
  },
  "daily_report": "Had a great swim session. Got nervous at archery."
}
```

Crucially: this is **per-camper** data — one `Reflection` row per camper, not per bunk. The counselor submits N rows (one per camper) in a single UI session, grouped by a shared `submission_id` UUID.

For TBE Madrich self-reflections, `author == subject` and the answers are self-assessment fields (wins, improvements, questions):

```json
{
  "wins": ["Punctual every session", "Helped student lead Torah"],
  "improvements": ["Plan ahead more"],
  "weekly_rating": 4
}
```

### Current subject dashboard endpoint and frontend

The subject dashboard exists and is functional:

- **Backend:** `GET /api/v1/dashboards/subject/{person_id}/` — `backend/bunk_logs/api/dashboards/subject.py`
- **Frontend:** `SubjectDetail.jsx` + `SubjectDetailPage.jsx`

The endpoint aggregates `Reflection` rows where `subject_id = person_id`, groups by template, computes KPIs, rating sparklines, recent text responses, and concerning patterns (low ratings, downward trends). There is no ad-hoc notes panel.

---

## 3. Design — Subject Linkage Model

### Current state

The `Reflection` model already implements **Option (a)** — a single `subject` FK — with an additional `submission_id` mechanism to link rows from multi-subject batch submissions. This was an intentional design decision made in migration `0010`.

For completeness and stakeholder communication, all three options are evaluated below.

---

### Option A — Single FK `subject` on `Reflection` (current implementation)

```python
subject = models.ForeignKey(
    Person,
    null=True,
    blank=True,
    on_delete=models.CASCADE,
    related_name="reflections_about",
    help_text="Who this reflection is ABOUT. Null when subject_mode='group'.",
)
```

Multi-subject submissions create one `Reflection` row per subject, grouped by shared `submission_id`.

**Pros:**
- Already implemented and in production use
- Simple query: `Reflection.objects.filter(subject=person)`
- Per-subject `answers` are naturally isolated to their row
- `submission_id` preserves the "batch submission" concept for UI without complicating the data model
- Works perfectly for the Crane Lake counselor case (one submission → one row per camper)
- Works for TBE self-reflections (author == subject, one row per submission)
- Works for specialist observations (one submission, one subject)

**Cons:**
- Multi-subject submissions generate N rows; if the template has questions that are NOT per-subject (e.g., a general "how was the session?" field shared across all campers), that shared answer is repeated in every row, not stored once
- No built-in way to express "this reflection referenced multiple subjects but not all answers apply to each one" without abusing the `answers` JSON
- Unit-level leadership reflections that mention specific people by name can only link to one subject per row; they cannot express "this reflection is about the whole unit AND references camper X and counselor Y"

**Verdict:** Correct for 90% of current use cases. The "shared answers duplicated across rows" concern is cosmetic — storage is cheap and the dashboard never aggregates across subjects in a single row. The multi-person LT reference case is addressed by future free-text `SubjectNote`s rather than bending Reflection.

---

### Option B — M2M `subjects` on `Reflection`

```python
subjects = models.ManyToManyField(
    Person,
    related_name="reflections_about",
    blank=True,
)
```

**Pros:**
- Natural fit for "this submission is about these 3 people"
- No row duplication for multi-subject submissions

**Cons:**
- No per-subject `answers`: all answers are submission-level, not subject-level
- Breaks the Crane Lake counselor case: counselors need per-camper scores and notes, not one score for all campers in the submission
- Subject dashboard query becomes `Reflection.objects.filter(subjects=person)` with an extra join
- The existing `submission_id` mechanism already covers the "link related rows" need without sacrificing per-subject answers

**Verdict:** Does not preserve Crane Lake's old fidelity. Rejected.

---

### Option C — `ReflectionSubject` join model

```python
class ReflectionSubject(models.Model):
    reflection = models.ForeignKey(Reflection, on_delete=models.CASCADE)
    subject = models.ForeignKey(Person, on_delete=models.CASCADE)
    subject_answers = models.JSONField(
        default=dict,
        help_text="Per-subject subset of answers within this submission"
    )
```

**Pros:**
- Cleanly separates submission-level answers from subject-level answers
- Could allow a single Reflection row to cover a whole unit with per-person detail in child rows
- Explicit join table is flexible and query-able

**Cons:**
- Much higher complexity for all existing query paths; every join through `Reflection` for a subject now requires going through `ReflectionSubject`
- Existing `answers` JSON validation logic and dashboard aggregation code would need significant refactoring
- No current use case requires submission-level answers + per-subject answers in the same row; this would be premature abstraction
- Splitting `answers` across two JSON columns invites confusion about which fields live where
- Substantially higher migration risk (existing reflection data would need backfilling into the join table)

**Verdict:** Overly complex for current requirements. Rejected unless a concrete use case emerges that cannot be handled by Option A.

---

### Recommendation: Option A (status quo) — confirmed correct

The existing implementation is correct. **No changes to the `Reflection` model are needed for subject linkage.** The `subject` FK + `submission_id` pattern handles all four use cases in this prompt:

| Use case | How it works |
|---|---|
| Crane Lake counselor daily (1 submission, N campers each with scores/notes) | N `Reflection` rows, same `submission_id`, each with full per-camper `answers` |
| TBE Madrich self-reflection (subject == author) | 1 row, `author_id == subject_id`, template's `subject_mode = "self"` |
| Specialist observation (1 submission, 1 subject) | 1 row, `subject` set, `author` = specialist |
| LT biweekly (unit-level, may reference individuals) | 1 row per unit group reflection, future `SubjectNote`s for specific individual callouts |

---

## 4. Design — `SubjectNote` Model

### Rationale

The `Reflection` model covers template-driven, structured, periodic observations. But specialists (swim, athletics, arts), camper care staff, and wellness teams need to record **ad-hoc observations** that are:

- Not scheduled or periodic
- Not template-driven (free text, maybe a context tag)
- Often from a single observer about a single subject
- Potentially sensitive (visible to camper care but not counselors)
- Cross-context (a swim instructor's note sits beside a unit head's note in the same dashboard view)

No such model exists today. This is the primary new model needed before the subject dashboard can be considered complete for Crane Lake Summer 2026.

### Proposed model sketch

```python
class SubjectNote(models.Model):
    """Ad-hoc, non-template-driven observation about a subject Person.

    Complements Reflection (structured/periodic) by capturing free-text
    observations from specialists, camper care, wellness, and other staff
    who interact with the subject outside the structured reflection workflow.

    subject + program + created_at is the primary dashboard query axis.
    """

    class Visibility(models.TextChoices):
        # Visible to anyone who can view the subject dashboard
        TEAM = "team", "Team"
        # Visible only to supervisors and above (unit heads, LT, camper care, admin)
        SUPERVISORS_ONLY = "supervisors_only", "Supervisors Only"
        # Visible only to domain specialists and above (health center, camper care, admin)
        DOMAIN_ONLY = "domain_only", "Domain Specialists Only"
        # Visible only to admins
        ADMIN_ONLY = "admin_only", "Admin Only"

    organization = models.ForeignKey(
        "core.Organization",
        on_delete=models.CASCADE,
        related_name="subject_notes",
    )
    program = models.ForeignKey(
        "core.Program",
        on_delete=models.CASCADE,
        related_name="subject_notes",
    )
    subject = models.ForeignKey(
        "core.Person",
        on_delete=models.CASCADE,
        related_name="subject_notes",
        help_text="Who this note is about.",
    )
    author_person = models.ForeignKey(
        "core.Person",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_subject_notes",
        help_text="The Person who wrote the note (may differ from submitted_by for admin-entered notes).",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_subject_notes",
        help_text="The User who clicked submit (audit trail; may be an admin entering on behalf).",
    )
    context = models.CharField(
        max_length=64,
        blank=True,
        help_text=(
            "Context tag for where/how this observation arose. "
            "Examples: 'swim_instruction', 'dining_hall', 'wellness_checkin', "
            "'specialist_observation', 'camper_care', 'health_center'."
        ),
    )
    body = models.TextField(
        help_text="The note text.",
    )
    visibility = models.CharField(
        max_length=32,
        choices=Visibility.choices,
        default=Visibility.TEAM,
    )
    is_sensitive = models.BooleanField(
        default=False,
        help_text="If True, applies extra read-access restrictions (same semantics as Reflection.is_sensitive).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SubjectNoteScopedManager()  # org-scoped, see note below
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["subject", "program", "created_at"],
                name="subjectnote_subject_program_created_idx",
            ),
            models.Index(
                fields=["organization", "created_at"],
                name="subjectnote_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Note on {self.subject} by {self.author_person} ({self.created_at:%Y-%m-%d})"
```

### Manager sketch

```python
class SubjectNoteScopedManager(models.Manager):
    """Filters to notes where the requesting org matches (set by middleware)."""

    def get_queryset(self):
        from bunk_logs.core.organization_context import current_organization_id
        org_id = current_organization_id()
        if org_id is None:
            return super().get_queryset().none()
        return super().get_queryset().filter(organization_id=org_id)
```

This mirrors the pattern used by `OrgScopedManager`, `MembershipScopedManager`, etc. in `core/managers.py`.

### `context` field: string or tag list?

**Recommendation: `CharField(max_length=64)`** — a single context tag, not a list.

Rationale: the dashboard groups or filters notes by context ("all swim notes," "all wellness notes"). A many-to-many tag system adds join complexity without clear benefit for v1. If a note genuinely spans two contexts (e.g., wellness team + camper care), the author should write two notes or pick the primary context.

A `context` choice list should not be hard-coded in the model — context types vary by program (Crane Lake has swim/athletics/arts; TBE has religious school/social/academic). The implementation prompt should consider whether `context` is a free-form CharField with suggestions, a FK to a `NoteContext` lookup table, or a validated list from `Organization.settings`.

### Should `SubjectNote` share a base class with `Reflection`?

**No.** Reasons:

1. `Reflection` has `template`, `answers`, `period_start`, `period_end`, `submission_id`, `subject_group`, and `assignment_group` — none of which apply to ad-hoc notes
2. The visibility semantics overlap conceptually but are implemented differently: `Reflection` uses `team_visibility` (2 values) + `is_sensitive`; `SubjectNote` needs finer-grained `visibility` (4 values) because notes can be more sensitive than reflections
3. Django multi-table inheritance adds a hidden join on every query; abstract base classes would not express the genuinely shared fields (only `organization`, `program`, `created_at`, `updated_at` overlap)
4. The subject dashboard query is already a union of two separate querysets; a shared base class would not simplify this

A thin shared `OrgProgramMixin` abstract model (providing `organization`, `program`, `created_at`, `updated_at`) is acceptable if the team wants DRY field declarations, but it is not required for v1.

---

## 5. Design — Dashboard Access by Capability Layer

### Access matrix

| Capability | Can view subject dashboard for... | Can author `SubjectNote` about... | Can read `SubjectNote`s by others |
|---|---|---|---|
| `participant` | Self only (if `subject_visible=True` on template) | None (not applicable for v1) | None |
| `supervisor` | Direct-report subjects (their assignment group members) | Direct-report subjects | Notes authored within own assignment group context |
| `program_lead` | All subjects in program | All subjects in program | All notes in program (except `ADMIN_ONLY`) |
| `domain_specialist` | All subjects in program | All subjects in program | Notes with visibility `TEAM`, `SUPERVISORS_ONLY`, or `DOMAIN_ONLY` |
| `admin` | All subjects in org | All subjects in org | All notes in org |

### Notes on specific cells

**`participant` viewing self:** The existing `reflections_visible_to` filter already supports this via `subject_mode` and `subject_visible` flags on the template. The subject dashboard endpoint does not currently enforce "participant can only view self"; it relies on the calling UI to gate navigation. This should be made explicit in the implementation prompt.

**`supervisor` scope:** "Direct-report subjects" means members of `AssignmentGroup`s where the supervisor is a group leader (`role_in_group = "author"`). The `author_group_ids_with_descendants` helper in `core/permissions/visibility.py` computes this.

**`domain_specialist` (health_center, special_diets):** These roles see reflections that are `is_sensitive=True` because they are the intended audience for sensitive content. The same logic should apply to `SubjectNote`.

**`program_lead` (leadership_team):** Currently sees all reflections for their org (modulo the self-reflection LT privacy rule). Dashboard access for all subjects in program is consistent with this.

### Capability vs. role gating: explicit flag

**This is the first feature that requires the capability layer to actively gate a UI navigation path** (who can navigate to `SubjectDetailPage` for a given `person_id`).

Current code: the subject dashboard endpoint at `GET /api/v1/dashboards/subject/{person_id}/` has `permission_classes = [IsAuthenticated]` and relies on `reflections_visible_for_user` to filter down the data — but it does not explicitly check whether the viewer is allowed to view *this person's* dashboard at all. A `supervisor` querying `/dashboards/subject/1234/` for a camper not in their bunk would receive an empty payload (no reflections pass the visibility filter), which is a soft gate but not an explicit 403.

**Recommendation:** The implementation prompt should add an explicit permission check:

```python
def _can_view_subject_dashboard(viewer_person, subject_person, org):
    """Return True if viewer has permission to see subject's dashboard."""
    viewer_cap = _viewer_capability(viewer_person, org)
    if viewer_cap in ("program_lead", "admin"):
        return True
    if viewer_cap == "domain_specialist":
        return True
    if viewer_cap == "supervisor":
        return _viewer_supervises_subject(viewer_person, subject_person)
    if viewer_cap == "participant":
        return viewer_person.id == subject_person.id
    return False
```

**Flag for stakeholder review:** whether `domain_specialist` (health center, special diets) should see the full subject dashboard (all reflection streams) or only the streams relevant to their domain. Currently `reflections_visible_for_user` gates `is_sensitive=True` reflections behind capability; non-sensitive reflections (counselor daily bunk logs) are visible to health center staff. Alyson should confirm whether health center staff should see daily behavioral scores.

---

## 6. Design — Minimum Viable Scope for Crane Lake Summer 2026

### In scope for v1

**Subject types:**
- Campers only. Staff self-reflections (counselors, specialists, kitchen, maintenance) are authored and visible in other views; the subject dashboard for staff needs additional stakeholder discussion before building (see Open Questions).

**Data streams:**
- **Stream 1 — Structured reflections:** Counselor daily bunk logs (`Reflection` where `subject` is a camper). Existing subject dashboard endpoint and frontend already handle this.
- **Stream 2 — Ad-hoc notes:** `SubjectNote`s from specialists, camper care, wellness. Requires the new model (Prompt 3.15).

**Capabilities with dashboard access:**
- `supervisor` (unit heads, camper care) — their direct-report campers
- `program_lead` (leadership team) — all campers in program
- `admin` — all campers in org

**Capabilities with note-authoring:**
- `supervisor` — for their direct-report campers
- `domain_specialist` (health center, camper care) — for any camper
- `program_lead` + `admin` — for any camper

**Visibility levels for SubjectNote v1:**
- `TEAM` — visible to supervisors and above (default)
- `DOMAIN_ONLY` — visible only to health center, camper care, admin

**UI:**
- Existing reflection cards (already built)
- New "Notes" section showing `SubjectNote`s for the subject (new, requires Prompt 3.15 + Prompt 3.16)

### Deferred

| Feature | Reason |
|---|---|
| AI summaries and trend recommendations | Requires separate model + AI infrastructure; out of scope for 2026 |
| Trend visualizations beyond current sparklines | Nice-to-have; existing sparklines cover the core need |
| Parent-facing exports | Requires consent/privacy framework not yet designed |
| Cross-program longitudinal views (camper across multiple summers) | Requires `Person` identity resolution across programs; distinct roadmap item |
| Staff subject dashboards (counselors, specialists as subjects) | Stakeholder input required — see Open Questions |
| `SubjectNote` context taxonomy (swim/arts/athletics etc.) | Needs org-specific config; defer to program settings |
| `participant` self-view of own dashboard | Low priority for Crane Lake 2026; confirm with Alyson |

### Unblocked vs. blocked items

The existing subject dashboard API and frontend are **unblocked** — they work with current model state. The only change needed to make them production-ready is:

1. Add explicit capability-based access control to the API endpoint (Prompt 3.14)
2. Build `SubjectNote` model + API + frontend panel (Prompts 3.15–3.16)

---

## 7. Open Questions

These require customer or stakeholder input before implementation begins. Do not implement Prompts 3.14–3.17 until the questions marked **[BLOCKING]** are answered.

### [BLOCKING] Q1 — Should staff have subject dashboards?

Counselors, specialists, JCs, kitchen, maintenance are tracked subjects of their own reflections (e.g., unit head biweekly review). Should a unit head be able to open a "subject dashboard" for a counselor in their bunk? Should leadership be able to open one for a unit head?

*Impact:* If yes, the v1 scope expands to include staff subject types and the access matrix needs a "supervisor can view direct-report staff" row. If no, add a server-side guard to reject dashboard requests for non-camper subjects.

### [BLOCKING] Q2 — Should health center staff see counselor daily behavioral scores?

The current `reflections_visible_for_user` filter lets health center staff (capability `domain_specialist`) see non-sensitive counselor daily logs. The subject dashboard would show them `social_score`, `behavior_score`, `participation_score`, and counselor narrative notes.

*Impact:* If health center should only see their own domain (wellness-tagged reflections + health-tagged SubjectNotes), a domain filter must be added to the subject dashboard endpoint.

### [BLOCKING] Q3 — What is the `context` taxonomy for `SubjectNote`?

The note context tag ("swim_instruction", "dining_hall", "wellness_checkin", etc.) needs to be defined. Options:
- **Free text** — simplest, but hard to filter/group; risk of inconsistent tagging
- **Org-configurable list in `Organization.settings`** — flexible but requires UI for admins to manage
- **Hard-coded choices per program type** — predictable but inflexible for new customers

*Impact:* Determines the `context` field implementation in Prompt 3.15.

### Q4 — Who can edit or delete a SubjectNote?

Can an author edit their own note after submission? Can a `program_lead` delete a note? Is edit history needed?

*Impact:* API surface area for the SubjectNote CRUD endpoints.

### Q5 — `SUPERVISORS_ONLY` note visibility: does it include camper care?

Camper care has capability `supervisor`. If a unit head writes a note with `SUPERVISORS_ONLY` visibility, should camper care be able to read it? What about the reverse?

*Impact:* Whether `SUPERVISORS_ONLY` should be subdivided (e.g., `UNIT_HEAD_ONLY` vs `CAMPER_CARE_ONLY`) for v1.

### Q6 — Should `participant` (campers) ever see their own subject dashboard?

Technically feasible — `subject_visible` flag on templates already allows campers to see their own structured reflections. But for Crane Lake 2026, it is unclear whether we want campers to view their behavioral scores. Parent-facing is a separate question.

*Impact:* Determines whether `participant` access row in the capability table is implemented in v1.

### Q7 — Is a `SubjectNote` a Reflection?

Could specialist observations be modeled as a very simple `Reflection` with a minimal template (body + context tag) rather than a new model? This would reuse the entire existing visibility, dashboard aggregation, and export infrastructure.

*Impact:* If yes, Prompt 3.15 becomes "create a SubjectNote template type" rather than "create a SubjectNote model." Needs team discussion before Prompt 3.15 is written.

---

## Next Prompts

### Prompt 3.14 — Subject dashboard access control

Add explicit capability-based permission check to `GET /api/v1/dashboards/subject/{person_id}/`. Return 403 for `participant` viewing someone else's dashboard, or `supervisor` viewing a non-direct-report. Update tests.

*Prerequisite:* Resolution of Open Questions Q1 and Q2.  
*Risk:* Low. No model changes. May surface existing implicit access that was previously unguarded.

### Prompt 3.15 — `SubjectNote` model and API

Add `SubjectNote` model (fields, manager, indexes, migration). Add DRF endpoints: `POST /api/v1/subjects/{person_id}/notes/`, `GET /api/v1/subjects/{person_id}/notes/`, `PATCH/DELETE /api/v1/subjects/{person_id}/notes/{note_id}/`. Enforce visibility and capability-based access.

*Prerequisite:* Resolution of Q1, Q3, Q4, Q5. This prompt is blocked until the context taxonomy and access rules are confirmed.  
*Risk:* Medium. New model + migration. Visibility rules need careful implementation.

### Prompt 3.16 — Subject dashboard frontend: Notes panel

Add a "Notes" section to `SubjectDetail.jsx` showing `SubjectNote`s. Add `SubjectNote` authoring UI (form with body + context + visibility selector). Wire to API from Prompt 3.15.

*Prerequisite:* Prompt 3.15 shipped.  
*Risk:* Low. Frontend-only. No model changes.

### Prompt 3.17 — Subject dashboard production hardening

Add explicit org-scoping guard to the subject dashboard endpoint (currently trusts org from middleware but does not verify subject belongs to org). Add pagination or count limits on the reflections query (unbounded today). Add explicit capability check from Prompt 3.14.

*Prerequisite:* None. Can be done in parallel with Prompt 3.15.  
*Risk:* Low. Defense-in-depth changes, no user-visible behavior change.

### Prompt 3.18 — Staff subject dashboards (conditional)

If Q1 resolves to "yes, staff have dashboards," add support for staff subject types. Extend capability access matrix. Add UI navigation from the unit head / LT views.

*Prerequisite:* Q1 confirmed by Alyson/Brent.  
*Risk:* Medium. Requires access policy decisions that affect multiple views.

---

## Appendix — Model Field Summary (for implementation reference)

### `Reflection` (existing — no changes needed)

```python
organization     ForeignKey(Organization)
program          ForeignKey(Program)
subject          ForeignKey(Person, null=True)        # who the reflection is ABOUT
subject_group    ForeignKey(AssignmentGroup, null=True)  # when subject_mode='group'
author           ForeignKey(Person, null=True)        # who filled it out
submitted_by     ForeignKey(User, null=True)          # audit trail
assignment_group ForeignKey(AssignmentGroup, null=True)
submission_id    UUIDField                            # groups multi-subject batch
template         ForeignKey(ReflectionTemplate)
period_start     DateField
period_end       DateField
answers          JSONField
language         CharField
team_visibility  CharField (team / supervisors_only)
is_complete      BooleanField
is_sensitive     BooleanField
client_submission_id  UUIDField
submitted_at     DateTimeField
updated_at       DateTimeField
```

### `SubjectNote` (new — proposed in this document)

```python
organization     ForeignKey(Organization)
program          ForeignKey(Program)
subject          ForeignKey(Person)                   # who the note is ABOUT
author_person    ForeignKey(Person, null=True)        # who wrote it
submitted_by     ForeignKey(User, null=True)          # audit trail
context          CharField(max_length=64)             # e.g. "swim_instruction"
body             TextField
visibility       CharField (team / supervisors_only / domain_only / admin_only)
is_sensitive     BooleanField
created_at       DateTimeField (auto_now_add)
updated_at       DateTimeField (auto_now)

Meta.indexes:
  - (subject, program, created_at) -- primary dashboard query
  - (organization, created_at) -- org-wide admin views
```

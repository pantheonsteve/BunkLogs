# 4_8: Challenge Log — Semi-anonymous classroom challenges with faculty response

**Wave:** 4 (TBE Tier 1 — Fall 2026 Religious School)
**Estimated time:** 10–14 hours of agentic work (lean mode: one PR)
**Prerequisite:** Steps 3_17 (AssignmentGroup), 3_18 (roster import), 4_3 (TBE roster), 4_7 (availability — independent but same release train), and 7_14 (Madrich flow) complete or stacked.

**Use the context prompt at `migration_prompts/0_0_context_prompt.md` before this session.**

---

## Context

TBE Madrichim work inside **classrooms** (`AssignmentGroup` with `group_type='classroom'`). Faculty (rabbi/educator) observes Madrichim; Madrichim sometimes encounter **classroom challenges** — behavior issues, missing materials, schedule confusion, interpersonal friction — that need faculty attention **during the session** or shortly after, but **without turning every friction into a graded reflection**.

The **Challenge Log** is a lightweight, classroom-scoped operational channel:

- A **Madrich author** submits a short challenge report tied to their classroom.
- **Peer Madrichim** in the same classroom see that *a* challenge was raised (category + timestamp) but **not which Madrich submitted it** — semi-anonymous to peers.
- **Faculty** assigned to that classroom see the full thread including **author identity** (they must follow up in person).
- **Director / TBE Admin** see author identity and can filter across classrooms.

This replaces the stub empty state in `frontend/src/components/ClassroomDashboard.jsx` ("Reflections aren't configured for classrooms yet") with a real **Challenges** section for faculty, while giving Madrichim a **Report a challenge** entry point from their dashboard (classroom picker when assigned to multiple rooms).

**Not a Reflection:** do not create `Reflection` / `ReflectionTemplate` rows for challenges. Do not mix into weekly 3-2-1 history. Do not expose on Crane Lake bunk dashboards.

**Canonical classroom model:** see `docs/data-model.md` § "TBE Classroom — Faculty Observes Madrichim".

**Semi-anonymity rules (decision MA7 — new):**

| Viewer | Sees author name? | Sees body? | Sees peer identity on other challenges? |
|--------|-------------------|------------|----------------------------------------|
| Author (self) | Yes | Yes | No |
| Peer Madrich in same classroom | No (display "A Madrich") | Yes | No |
| Faculty (author role on classroom) | Yes | Yes | Yes (faculty need full context) |
| Director / Admin | Yes | Yes | Yes |

Faculty identity is always shown on **responses** (faculty replies are attributed).

---

## ClassroomChallenge model

Add to `backend/bunk_logs/core/models.py` (default) or a focused `challenges` app if you strongly prefer separation — **default to `core`** for lean Tier 1.

### `ClassroomChallenge`

```python
class ClassroomChallenge(models.Model):
    CATEGORY_BEHAVIOR = "behavior"
    CATEGORY_ENVIRONMENT = "environment"
    CATEGORY_SCHEDULE = "schedule"
    CATEGORY_MATERIALS = "materials"
    CATEGORY_OTHER = "other"
    CATEGORY_CHOICES = [
        (CATEGORY_BEHAVIOR, "Student behavior"),
        (CATEGORY_ENVIRONMENT, "Room environment"),
        (CATEGORY_SCHEDULE, "Schedule / timing"),
        (CATEGORY_MATERIALS, "Materials / curriculum"),
        (CATEGORY_OTHER, "Other"),
    ]

    STATUS_OPEN = "open"
    STATUS_ACKNOWLEDGED = "acknowledged"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
        (STATUS_RESOLVED, "Resolved"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    assignment_group = models.ForeignKey(
        AssignmentGroup,
        on_delete=models.CASCADE,
        related_name="challenges",
        limit_choices_to={"group_type": AssignmentGroup.GROUP_TYPE_CLASSROOM},
    )
    author = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="classroom_challenges_authored",
    )
    session_date = models.DateField(
        help_text="Sunday session this challenge pertains to; defaults to upcoming or current session",
    )
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    body = models.TextField(max_length=2000)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="classroom_challenges_resolved",
    )

    class Meta:
        indexes = [
            models.Index(fields=["assignment_group", "session_date", "status"]),
            models.Index(fields=["program", "created_at"]),
            models.Index(fields=["author", "created_at"]),
        ]
        ordering = ["-created_at"]
```

Apply `OrgScopedManager`. `clean()` validates:

- `assignment_group.group_type == 'classroom'`
- `author` has active `AssignmentGroupMembership` with `role_in_group='author'` **or** `'subject'`? **Correction:** Madrichim are **subjects** in the classroom group per import model. Author of a challenge is the Madrich **Person** who is a **subject** in that classroom. Validate active AGM: `(group, person, role_in_group='subject')`.
- `session_date` is a Sunday and ideally in `program.settings["session_dates"]` (same list as Step 4_7).

### `ClassroomChallengeResponse`

```python
class ClassroomChallengeResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge = models.ForeignKey(
        ClassroomChallenge,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    author = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="classroom_challenge_responses",
    )
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
```

Validation: `author` must be faculty with active AGM `role_in_group='author'` on the same classroom **or** hold admin/director supervision over the program (admin override reply allowed in Tier 1).

### Audit trail

Hook create / status change / reply events into existing audit infrastructure (Step 7_4) with entity type `classroom_challenge`. Capture `author_role_at_write` on responses.

### Django admin

Read-only inline responses on challenge change page; filters by program, classroom, status, category.

---

## API endpoints

Base path: `/api/v1/classroom-challenges/` (org-scoped via middleware). All serializers must apply **viewer-dependent author redaction** (see Semi-anonymity table).

### Shared serializer behavior

```python
def serialize_author(person, *, viewer, challenge):
    if viewer_is_peer_madrich(viewer, challenge) and person.id != viewer.id:
        return {"display": "A Madrich", "redacted": True}
    return {
        "id": person.id,
        "display_name": person.display_name,
        "redacted": False,
    }
```

Never leak author `id` to peer Madrichim in JSON (omit or null when `redacted=True`).

---

### Madrich endpoints

Namespace: `/api/v1/madrich/challenges/`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/madrich/challenges/classrooms/` | Classrooms the Madrich belongs to (subject AGM) |
| `GET` | `/api/v1/madrich/challenges/` | List challenges in those classrooms (peer view rules) + own submissions |
| `POST` | `/api/v1/madrich/challenges/` | Create challenge |
| `GET` | `/api/v1/madrich/challenges/{id}/` | Detail with responses |
| `POST` | `/api/v1/madrich/challenges/{id}/close/` | Author may withdraw if `status=open` and no faculty response yet |

**`GET /classrooms/`** response:

```json
{
  "classrooms": [
    {
      "assignment_group_id": 12,
      "name": "Grade 9 — Room 204",
      "session_date_default": "2026-09-13"
    }
  ]
}
```

**`POST /` body:**

```json
{
  "assignment_group_id": 12,
  "session_date": "2026-09-13",
  "category": "behavior",
  "body": "Two students were disruptive during Hebrew drill; we paused twice."
}
```

- 400 if body empty after strip or category invalid.
- 403 if Madrich not subject in classroom.
- Returns 201 with detail payload (author sees own name).

**List filters:** `?classroom={id}`, `?session_date=`, `?mine=1` (own submissions only).

**Peer list item shape:**

```json
{
  "id": "uuid",
  "category": "behavior",
  "category_label": "Student behavior",
  "session_date": "2026-09-13",
  "body_preview": "Two students were disruptive…",
  "status": "open",
  "author": {"display": "A Madrich", "redacted": true},
  "response_count": 1,
  "created_at": "..."
}
```

**Withdraw (`POST .../close/`):** sets a soft-delete flag **or** deletes row if no responses — prefer **`status='withdrawn'`** hidden from peer/faculty lists (add `STATUS_WITHDRAWN` only if needed; otherwise hard-delete when zero responses). Lean: **hard delete** when `responses.count()==0`; else 403.

---

### Faculty endpoints

Namespace: `/api/v1/faculty/challenges/`

Create minimal `api/faculty/` package mirroring `api/madrich/` (`urls.py`, `common.py` with `viewer_or_403` for faculty membership).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/faculty/challenges/` | Challenges for classrooms faculty authors |
| `GET` | `/api/v1/faculty/challenges/{id}/` | Full detail (author identity visible) |
| `POST` | `/api/v1/faculty/challenges/{id}/responses/` | Reply |
| `PATCH` | `/api/v1/faculty/challenges/{id}/` | Update status: `acknowledged` or `resolved` |

**`GET /` query params:** `classroom`, `status`, `session_date`. Default sort: open first, then `-created_at`.

**Faculty list item includes:**

```json
{
  "author": {"id": 42, "display_name": "Alex Cohen", "redacted": false},
  "assignment_group": {"id": 12, "name": "Grade 9 — Room 204"},
  ...
}
```

**`POST /responses/` body:** `{"body": "Thanks — I'll address this next week."}`

- On first faculty response, auto-transition `status` from `open` → `acknowledged` if still open.

**`PATCH /` body:** `{"status": "resolved"}` sets `resolved_at`, `resolved_by`.

---

### Admin / Director endpoints

Reuse admin auth from Step 4_4:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/classroom-challenges/` | Org-wide list with filters |
| `GET` | `/api/v1/admin/classroom-challenges/export.csv` | CSV export |

No admin reply in Tier 1 (Director uses faculty account or in-person follow-up).

---

### Classroom dashboard payload integration

Extend `build_classroom_dashboard_payload` in `backend/bunk_logs/api/dashboards/group_payloads.py`:

Replace the stub-only payload with:

```json
{
  "challenges": {
    "open_count": 2,
    "recent": [ /* last 3 faculty-visible summaries */ ],
    "list_url": "/faculty/challenges?classroom=12"
  },
  ...
}
```

Gate `challenges` block: only when viewer is faculty author on classroom (not for Madrich viewing classroom dashboard — Madrich uses `/madrich/challenges`).

---

## Madrich views

### Dashboard entry

Add **Report a challenge** card on `frontend/src/pages/madrich/Dashboard.jsx` below availability (4_7) and reflection cards:

- Copy: *"Something need faculty attention in your classroom?"*
- CTA opens `/madrich/challenges/new` or modal composer.
- If Madrich has zero classroom assignments, hide card.

### Challenge list — `frontend/src/pages/madrich/ChallengeLog.jsx`

Route: `/madrich/challenges`

- Tabs: **Our classroom** (peer-safe list) | **My reports** (`?mine=1`)
- Our classroom: cards with category chip, session date, body preview, status, response count; author always "A Madrich" unless own submission in **My reports** tab.
- Empty state: *"No challenges reported for this classroom yet."*

### New challenge — `frontend/src/pages/madrich/ChallengeForm.jsx`

Route: `/madrich/challenges/new`

- Classroom select (if >1), session date default from API, category select, body textarea (2000 char counter).
- Disclosure footer: *"Faculty and your Director can see who submitted this. Other Madrichim in your classroom cannot."*
- Submit → navigate to detail or list with toast.

### Challenge detail — `frontend/src/pages/madrich/ChallengeDetail.jsx`

Route: `/madrich/challenges/:id`

- Full body, status badge, chronological responses (faculty attributed).
- Author line: show own name if viewer is author; else "Submitted by A Madrich".
- Withdraw button when allowed (no responses, open, own submission).

### Navigation

No new sidebar item (Story 61 stripped nav). Entry via dashboard card only.

---

## Faculty views

### Challenge inbox — `frontend/src/pages/faculty/ChallengeInbox.jsx`

Route: `/faculty/challenges`

- Table/cards grouped by classroom (if multiple).
- Filters: status, session date.
- Row: author name, category, preview, status, created_at.
- Tap → detail.

### Challenge detail — `frontend/src/pages/faculty/ChallengeDetail.jsx`

Route: `/faculty/challenges/:id`

- Full author + body + status controls (Acknowledge / Resolve).
- Reply composer at bottom (textarea + Send).
- Resolved threads read-only except admin.

### Classroom dashboard section

Update `frontend/src/components/ClassroomDashboard.jsx`:

- Remove amber stub banner for faculty users when challenges API returns data.
- Section **Open challenges** with count badge, list of top 3, link to inbox.
- Madrich viewing classroom dashboard (if ever routed there) still sees stub or redirect — **Madrich should not use GroupDashboard for challenges** in Tier 1.

### Routing and auth

- Register faculty routes in `frontend/src/App.jsx` (or route module) gated on `user.role === 'Faculty'` or capability check matching backend.
- Default landing: faculty without other home continue using `/dashboards`; add optional **Challenges** link in AppLayout when faculty membership detected (minimal — inbox linked from classroom dashboard is sufficient for Tier 1).

---

## Testing

Lean mode — meaningful behavior coverage, not exhaustive matrices.

### Backend pytest

Create `backend/bunk_logs/api/tests/test_classroom_challenges.py`:

1. **Create:** Madrich subject submits; 403 for non-member; 400 for bad category/body.
2. **Peer redaction:** second Madrich in same classroom GET list — author redacted, body present.
3. **Self view:** author GET detail — author not redacted.
4. **Faculty:** faculty author lists with full author; reply creates `ClassroomChallengeResponse`; status auto-acknowledged.
5. **Resolve:** faculty PATCH resolved sets timestamps.
6. **Withdraw:** author DELETE/close before response succeeds; after response fails.
7. **Admin:** admin list + CSV includes author names.
8. **Cross-org:** Crane Lake user 403 on all endpoints.
9. **Classroom dashboard payload:** faculty sees `open_count`; Madrich peer not in faculty payload path.

### Frontend vitest

1. `ChallengeForm` — submits POST with mocked API.
2. `ChallengeLog` — peer tab renders "A Madrich".
3. `ChallengeDetail` (Madrich) — own vs peer author label.
4. `ChallengeInbox` (Faculty) — renders author names from mock.
5. `ClassroomDashboard` — open challenges section replaces stub when mock provides data.

### Manual smoke (document in PR)

1. Seed TBE dev data with 2 Madrichim + 1 faculty in one classroom.
2. Madrich A submits behavior challenge.
3. Madrich B sees redacted author on list.
4. Faculty replies and resolves.
5. Admin CSV export downloads.

Run:

```bash
make test-backend
make test-frontend
```

---

## Branch Name

`feat/tbe-challenge-log`

---

## Execution Notes for Cursor

**Mode:** lean — one PR, backend + frontend + tests together. Do not split model/API/UI unless diff exceeds ~1500 lines.

**Order of work:**

1. Models + migration + admin registration.
2. Shared redaction helper + serializers (`api/classroom_challenges/serializers.py` or under madrich/faculty packages).
3. Madrich endpoints + tests for create/list/redaction.
4. Faculty endpoints + reply/status tests.
5. Admin list + CSV.
6. Extend `build_classroom_dashboard_payload`.
7. Madrich frontend (form, list, detail, dashboard card).
8. Faculty frontend (inbox, detail, ClassroomDashboard section).
9. Record **MA7** in `docs/user_stories/00_cross_cutting/decisions.md`.
10. `seed_tbe_dev_data` — one open challenge + one resolved with response for local QA.

**Do not:**

- Create ReflectionTemplate for challenges.
- Reuse Notes platform (7_19) — different semantics, audience, and lifecycle.
- Show peer identity "leaked" via API ids, error messages, or audit endpoints visible to Madrichim.
- Enable Crane Lake program types — guard with `program_type == 'religious_school'`.

**Reuse:**

- `AssignmentGroup` / AGM from 3_17–3_18.
- `viewer_or_403` patterns from `api/madrich/common.py` — extract shared org/program context helper if duplication exceeds ~30 lines.
- `AudienceDisclosure`-style footer copy component if available; otherwise inline paragraph.
- Tailwind card patterns from Madrich dashboard.

**Commit / PR:**

```
feat(4_8_challenge_log): semi-anonymous classroom challenges for TBE
```

PR title: `4_8: Classroom challenge log with faculty response`

**Completion gates (from context prompt):**

- `make test-backend` exit 0
- `make test-frontend` exit 0
- Step ID `4_8` verbatim in commit message
- Push branch and open PR with `gh pr create`

**Files likely touched:**

| Area | Paths |
|------|-------|
| Models | `backend/bunk_logs/core/models.py`, migration |
| API | `backend/bunk_logs/api/madrich/challenges.py`, `api/faculty/*`, `api/admin/classroom_challenges.py`, `api/urls.py` |
| Dashboard | `backend/bunk_logs/api/dashboards/group_payloads.py` |
| Tests | `backend/bunk_logs/api/tests/test_classroom_challenges.py` |
| Frontend | `frontend/src/pages/madrich/Challenge*.jsx`, `frontend/src/pages/faculty/Challenge*.jsx`, `ClassroomDashboard.jsx`, `Dashboard.jsx`, routes |
| Seed | `backend/bunk_logs/core/management/commands/seed_tbe_dev_data.py` |
| Docs | `docs/user_stories/00_cross_cutting/decisions.md` (MA7) |

---

## Out of Scope

- Push/email notifications on new challenge (Tier 2 — observe usage first).
- Parent visibility (MA4).
- File attachments / photos.
- Upvoting or "+1 me too" on peer challenges.
- Anonymous-to-faculty mode (faculty always see author in Tier 1).
- Challenge analytics / trend dashboards.
- Integration with weekly 3-2-1 reflection ("1 question or concern" remains separate).
- Crane Lake bunk-level "challenge log" analog.
- Real-time websocket updates (manual refresh per LT12).
- Faculty submitting challenges (Madrich-initiated only Tier 1).

---

## Acceptance Checklist

- [ ] `ClassroomChallenge` + `ClassroomChallengeResponse` migrated
- [ ] Madrich can submit from `/madrich/challenges/new`
- [ ] Peer Madrich sees redacted author on classroom list
- [ ] Faculty inbox shows author identity at `/faculty/challenges`
- [ ] Faculty can reply and mark resolved
- [ ] Admin CSV export works
- [ ] `ClassroomDashboard` shows open challenges for faculty (stub removed)
- [ ] Cross-org isolation verified
- [ ] MA7 documented in decisions.md
- [ ] `make test-backend` + `make test-frontend` pass

---

## PR Guidance

- **Branch:** `feat/tbe-challenge-log`
- Single squash-merge PR preferred
- Include screenshots: Madrich form with disclosure, peer list with "A Madrich", faculty inbox with names
- Call out semi-anonymity rules explicitly in PR description so reviewers verify redaction tests
- Migration is additive — safe deploy before frontend

---

## Related

| Artifact | Relationship |
|----------|--------------|
| `migration_prompts/3_17_subject_author_and_assignment_group_models.md` | Classroom AGM roles |
| `migration_prompts/3_18_roster_import_and_group_management.md` | TBE classroom import |
| `migration_prompts/4_3_tbe_madrachim_roster_import.md` | Madrichim as classroom subjects |
| `migration_prompts/4_7_availability_calendar.md` | Same release train; shared `session_dates` |
| `migration_prompts/4_4_tbe_admin_dashboard.md` | Admin auth + CSV patterns |
| `migration_prompts/7_14_madrich_flow.md` | Madrich dashboard namespace |
| `migration_prompts/7_19_notes_platform.md` | Distinct primitive — do not merge |
| `docs/data-model.md` | Classroom diagram |
| `frontend/src/components/ClassroomDashboard.jsx` | Replace stub section |
| `backend/bunk_logs/api/dashboards/group_payloads.py` | `build_classroom_dashboard_payload` |

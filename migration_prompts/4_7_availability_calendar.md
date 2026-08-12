# 4_7: Availability Calendar — Sunday commitment tracking for Madrichim

**Wave:** 4 (TBE Tier 1 — Fall 2026 Religious School)
**Estimated time:** 6–8 hours of agentic work (lean mode: one PR)
**Prerequisite:** Steps 4_1 (TBE org), 4_3 (roster import), and 7_14 (Madrich flow) complete or in flight on the same branch stack.

**Use the context prompt at `migration_prompts/0_0_context_prompt.md` before this session.**

---

## Context

Temple Beth-El's religious school program runs on **Sundays**. Madrichim (grades 8–12) are scheduled into classrooms week by week. Rachel (Director) and faculty need a lightweight staffing signal: **which Madrichim plan to be present on each upcoming Sunday session** — without mixing that operational data into the weekly 3-2-1 reflection form.

This step adds a **Sunday availability calendar** scoped to the active TBE `religious_school` Program:

- **Madrich view:** a month-forward calendar on the Madrich dashboard where the Madrich marks each program Sunday as *Available*, *Unavailable*, or *Tentative*, with an optional short note.
- **Director / TBE Admin view:** a read-only matrix (Madrichim × upcoming Sundays) for staffing decisions, exportable to CSV for Rachel's offline planning.
- **Faculty view (read-only):** faculty assigned to a classroom can see availability counts for Madrichim in that classroom only — not the full-org matrix.

This is **operational scheduling**, not evaluation. It must **not** appear in reflection history, team dashboards, or Crane Lake surfaces. Build entirely on the new multi-tenant models (`Organization`, `Program`, `Person`, `Membership`). Do **not** extend legacy Session/Unit/Bunk models.

**Product alignment:**

- Complements Stories 61–65 (`docs/user_stories/09_madrich/STORIES.md`). Story 62 explicitly says there is **no day-off toggle on reflections**; availability is a separate concern.
- Decision **MA1** (Monday–Sunday week boundary) applies to reflection periods only. Availability is keyed to **calendar session dates** (Sundays), not reflection week boundaries.
- TBE Tier 1 is **English only** — all UI copy inline English; no `t()` wrapping in this step.

**Session dates source of truth:**

Program `settings` gains a canonical list of session dates:

```json
{
  "session_dates": ["2026-09-13", "2026-09-20", "..."]
}
```

The `setup_tbe` command (Step 4_1) should seed a reasonable default list for the 2026–27 year (every Sunday from `SCHOOL_YEAR_START` through `SCHOOL_YEAR_END`, excluding known holiday skips documented inline in the command). Admins can edit the list later via Django admin `Program.settings` JSON until a dedicated admin UI ships in Tier 2.

---

## Acceptance Criteria

### AC1 — Data model and migration

1. Add `MadrichAvailability` model in `backend/bunk_logs/core/models.py` (or a small `scheduling` app if you prefer separation — default to `core` to match other TBE Tier 1 additions):

```python
class MadrichAvailability(models.Model):
    STATUS_AVAILABLE = "available"
    STATUS_UNAVAILABLE = "unavailable"
    STATUS_TENTATIVE = "tentative"
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_UNAVAILABLE, "Unavailable"),
        (STATUS_TENTATIVE, "Tentative"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="availability_commitments")
    session_date = models.DateField(help_text="A program session Sunday")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    note = models.CharField(max_length=280, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["program", "person", "session_date"],
                name="uniq_madrich_availability_per_session",
            ),
        ]
        indexes = [
            models.Index(fields=["program", "session_date"]),
            models.Index(fields=["person", "session_date"]),
        ]
```

2. Apply `OrgScopedManager` consistent with other tenant models. Default queryset filters by `organization_context`.

3. Migration is **additive only** (new table). No changes to existing tables beyond optional `Program.settings` documentation in `setup_tbe`.

4. Validation rules enforced in model `clean()` and serializers:
   - `session_date` must be a Sunday (`weekday() == 6`).
   - `session_date` must appear in `program.settings["session_dates"]` when that list is non-empty; reject with 400 otherwise.
   - `person` must have an active `Membership` with `role='madrich'` in the same program at write time.

5. Django admin: list view filterable by program, session_date, status; search by person name/email.

### AC2 — Madrich availability API

New endpoints under `/api/v1/madrich/availability/`:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/madrich/availability/` | List viewer's commitments for upcoming sessions |
| `PUT` | `/api/v1/madrich/availability/{session_date}/` | Upsert one session (create or update) |
| `DELETE` | `/api/v1/madrich/availability/{session_date}/` | Clear commitment (revert to "unset") |

**`GET` response shape:**

```json
{
  "program": {"id": 1, "name": "TBE Religious School 2026-27", "slug": "religious-school-2026-27"},
  "timezone": "America/New_York",
  "edit_deadline_rule": "saturday_18:00_eastern",
  "sessions": [
    {
      "session_date": "2026-09-13",
      "label": "Sun Sep 13",
      "editable": true,
      "commitment": {
        "status": "available",
        "note": "",
        "updated_at": "2026-09-10T22:15:00Z"
      }
    },
    {
      "session_date": "2026-09-20",
      "label": "Sun Sep 20",
      "editable": true,
      "commitment": null
    }
  ]
}
```

Rules:

- Return only sessions from `session_dates` where `session_date >= today` in the program timezone, capped at **16 weeks forward** (performance guard).
- `commitment: null` means the Madrich has not set a status yet (distinct from `unavailable`).
- **`editable` flag:** `false` when current time in program timezone is after **Saturday 18:00 Eastern** immediately preceding that Sunday (decision **MA6** — see Implementation Notes). Past sessions are never editable.
- Auth: same gate as other Madrich endpoints (`viewer_or_403` in `api/madrich/common.py`) — active `madrich` Membership in a `religious_school` program for the org context.
- Cross-org isolation: a Madrich in TBE cannot read or write Crane Lake availability (no rows leak).

**`PUT` body:**

```json
{"status": "available", "note": "Need to leave by 12:30"}
```

- `status` required; must be one of the three choices.
- `note` optional, max 280 chars, stripped whitespace.
- Returns the updated session object from the list shape above.
- 403 when `editable` is false.
- 400 when session_date invalid or not in program session list.

**`DELETE`:** removes the row; returns 204. Same edit-window gate as PUT.

Wire URLs in `backend/bunk_logs/api/madrich/urls.py` and register in root API router.

### AC3 — Madrich calendar UI

1. Extend `GET /api/v1/madrich/dashboard/` payload with an `availability` summary block (keep the dedicated availability endpoint as the source of truth for the full calendar):

```json
"availability": {
  "upcoming_unset_count": 2,
  "next_session_date": "2026-09-13",
  "next_session_status": null,
  "calendar_url": "/madrich/availability"
}
```

2. New page `frontend/src/pages/madrich/AvailabilityCalendar.jsx` at route `/madrich/availability`:
   - Month-grouped list of upcoming session cards (mobile-first; no heavy calendar widget dependency).
   - Each card: date label, three-way segmented control (Available / Tentative / Unavailable), optional note field (collapsible on mobile).
   - Unset sessions show neutral styling with helper copy: *"Tap a status so your Director knows your plan."*
   - Disabled state when `editable: false` with explanation: *"Availability for this Sunday locked Saturday at 6:00 PM."*
   - Optimistic UI optional; at minimum refetch after each save.
   - Link from Madrich dashboard section **My availability** (new card below reflection cards, above history shortcut).

3. Dashboard card copy (English Tier 1):
   - Title: **My availability**
   - Subtitle when unset: *"{N} upcoming Sundays not marked yet"*
   - Subtitle when set: *"Next session ({date}): Available"* (or Tentative/Unavailable)
   - CTA: **Update availability**

4. Styling matches existing Madrich dashboard (`Dashboard.jsx`) — Tailwind, dark mode, 44px touch targets.

5. **Out of dashboard scope per Story 61:** do not show other Madrichim's availability on this page.

### AC4 — Director / Admin staffing overview

1. New endpoint `GET /api/v1/admin/madrich-availability/`:
   - Auth: `admin` capability or TBE Director via `program_lead` supervising the Madrich cohort (reuse supervision checks from admin reflections dashboard, Step 4_4).
   - Query params: `program` (slug, default active religious_school program), `from` / `to` date (optional, default next 8 sessions).
   - Response: matrix payload suitable for UI + CSV:

```json
{
  "program": {...},
  "sessions": ["2026-09-13", "2026-09-20"],
  "rows": [
    {
      "person_id": 42,
      "display_name": "Alex Cohen",
      "grade_level": 10,
      "cells": [
        {"session_date": "2026-09-13", "status": "available", "note": ""},
        {"session_date": "2026-09-20", "status": null, "note": ""}
      ]
    }
  ],
  "summary": {
    "available_counts": {"2026-09-13": 8, "2026-09-20": 5},
    "unset_counts": {"2026-09-13": 2, "2026-09-20": 5}
  }
}
```

2. `GET /api/v1/admin/madrich-availability/export.csv` — same filters, CSV download for board/offline staffing (Content-Disposition attachment). Columns: `session_date`, `first_name`, `last_name`, `grade_level`, `status`, `note`, `updated_at`.

3. Frontend: extend TBE admin reflections area (`frontend/src/pages/admin/reflections/`) with tab or sub-route **Availability** rendering the matrix:
   - Rows = Madrichim sorted by grade then name.
   - Columns = upcoming session dates.
   - Cell colors: green / yellow / red / gray (unset) with icon + text (not color-only — a11y).
   - Summary row at bottom with available counts per session.

4. Faculty classroom-scoped read: `GET /api/v1/faculty/classrooms/{group_id}/availability/` returns only Madrichim who are **subjects** in that `AssignmentGroup` (classroom) with the same cell shape. Auth: faculty with `classroom_author` access per `group_dashboard_common.py`. No CSV export for faculty in Tier 1.

### AC5 — Session configuration, edit deadlines, and reminders

1. Update `setup_tbe` / `CANONICAL_PROGRAM_SETTINGS` to include `session_dates` for the 2026–27 year. Document excluded dates (e.g. winter break Sundays) in a comment block inside the command — Rachel can adjust the JSON list in admin before launch.

2. Edit deadline (**MA6**): commitments for session Sunday *S* may be created/updated/deleted until **Saturday 18:00 America/New_York** on the calendar day immediately before *S*. Implement in a shared helper `core/scheduling/availability_windows.py` used by API and tests.

3. Optional nudge (lightweight, in scope): when `upcoming_unset_count > 0` and today is **Wednesday**, include `"availability_nudge": true` in the Madrich dashboard payload so the client can show a dismissible banner: *"Please mark your availability for upcoming Sundays."* Do **not** send a separate email in this step — Wednesday email remains reflection-only (Step 4_5 / MA2).

4. Seed command `seed_tbe_dev_data` creates sample availability rows for 3 of 5 dev Madrichim so the admin matrix is testable locally.

---

## Out of Scope

- **Crane Lake** availability or non-Sunday cadences. Guard all UI routes and API namespaces behind `program_type='religious_school'`.
- **Automatic roster assignment** based on availability (Director still assigns classrooms manually).
- **Parent-facing** availability or notifications (MA4 — no parent visibility Tier 1).
- **iCal export / Google Calendar sync** (Tier 2).
- **Substitute request workflow** ("I need coverage") — future Notes or messaging integration.
- **Editing past sessions** or retroactive corrections by Madrichim (Admin may override via Django admin only in Tier 1).
- **Dedicated admin UI** for editing `session_dates` (JSON in Django admin is sufficient for Tier 1).
- **Push notifications** for unset availability.

---

## Testing Requirements

Lean mode — one happy path, one auth/permission, one critical edge per endpoint family:

### Backend (`pytest`)

1. **Model:** unique constraint, Sunday validation, session_date membership in program list.
2. **Madrich GET:** returns upcoming sessions with correct `editable` flags across timezone boundary (freeze time with `freezegun` at Friday vs Saturday 19:00 Eastern).
3. **Madrich PUT:** upsert available → tentative → unavailable; 403 after deadline; 400 for non-session date.
4. **Madrich DELETE:** clears row; 403 after deadline.
5. **Cross-org:** Crane Lake madrich/counselor receives 403 on TBE availability URLs.
6. **Admin matrix:** TBE admin sees all madrichim; counts correct; CSV export headers and row count.
7. **Faculty scoped:** faculty sees only classroom subjects; cannot hit admin matrix endpoint.
8. **Dashboard payload:** `availability.upcoming_unset_count` matches DB state.

### Frontend (`vitest`)

1. **AvailabilityCalendar:** renders sessions; changing status calls PUT with correct body; disabled when `editable: false`.
2. **Dashboard card:** shows unset count; links to calendar route.
3. **Admin matrix:** renders grid with status labels (mock API).

Run before PR:

```bash
make test-backend
make test-frontend
```

---

## Implementation Notes

1. **Namespace placement:** Prefer `api/madrich/availability.py` + `api/admin/madrich_availability.py` mirroring existing split. Faculty endpoint can live under `api/faculty/` (create minimal package if absent) or under `api/dashboards/` — pick the smallest diff that matches existing TBE routing.

2. **Do not overload Reflection:** availability rows are not reflections. No `ReflectionTemplate`, no completion semantics, no Wednesday reminder task changes beyond the optional dashboard nudge flag.

3. **Unset vs unavailable:** UI must never conflate "hasn't answered" (null) with "can't come" (`unavailable`). Director matrix uses gray for unset.

4. **Performance:** Admin matrix is O(madrichim × sessions). TBE soft launch is 8–10 Madrichim × ~8 sessions — trivial. Index `(program, session_date)` as specified.

5. **Timezone:** All deadline math in `America/New_York` from org settings. Use existing org timezone helpers if present; otherwise add a small helper next to `current_week_period` in `api/madrich/common.py`.

6. **Decision MA6 (new):** Saturday 18:00 lock — document in `docs/user_stories/00_cross_cutting/decisions.md` Madrich table as part of this PR.

7. **Lean docstrings:** 5–10 lines per module max. No role_flow markdown file unless asked.

8. **Frontend routing:** Register `/madrich/availability` in the Madrich route table alongside dashboard/history. Strip nav remains per Story 61 — no new sidebar items required; dashboard card is the entry point.

---

## Acceptance Checklist

Before opening the PR, confirm:

- [ ] `MadrichAvailability` model migrated; admin registered
- [ ] `session_dates` seeded in `setup_tbe` for 2026–27
- [ ] Madrich can mark availability for upcoming Sundays on `/madrich/availability`
- [ ] Edit lock enforced at Saturday 18:00 Eastern before each session
- [ ] TBE Admin sees matrix + CSV export at `/admin/reflections/availability` (or equivalent tab)
- [ ] Faculty sees classroom-scoped availability only
- [ ] Crane Lake users cannot access any new endpoints (403/404)
- [ ] Madrich dashboard shows **My availability** summary card
- [ ] `make test-backend` and `make test-frontend` pass
- [ ] MA6 recorded in decisions doc

---

## PR Guidance

- **Branch:** `feat/tbe-availability-calendar`
- **Commit message:** `feat(4_7_availability_calendar): add Sunday availability calendar for TBE Madrichim`
- **PR title:** `4_7: Availability calendar for TBE Madrichim`
- **PR body sections:** Summary (3 bullets), Test plan (checklist mirroring Acceptance Checklist), Screenshots (Madrich calendar + admin matrix)
- **Scope:** single PR — backend + frontend + tests + `setup_tbe` session_dates seed + MA6 decision line
- **Deploy note:** backwards-compatible additive migration; safe to deploy before frontend if API is unused

---

## Branch Name

`feat/tbe-availability-calendar`

---

## Related

| Artifact | Relationship |
|----------|--------------|
| `migration_prompts/4_1_tbe_organization.md` | Program + org setup; extend `setup_tbe` settings |
| `migration_prompts/4_3_tbe_madrachim_roster_import.md` | Madrichim rows appear in admin matrix |
| `migration_prompts/4_4_tbe_admin_dashboard.md` | Admin auth patterns; matrix lives alongside reflections admin |
| `migration_prompts/4_5_tbe_reminder_schedule.md` | Wednesday reminder stays reflection-only |
| `migration_prompts/4_6_tbe_soft_launch_runbook.md` | Soft launch verifies staffing workflow |
| `migration_prompts/7_14_madrich_flow.md` | Madrich dashboard + API namespace |
| `docs/user_stories/09_madrich/STORIES.md` | Stories 61–65; no day-off on reflections |
| `docs/data-model.md` | TBE classroom AssignmentGroup pattern for faculty scoped view |
| `backend/bunk_logs/api/madrich/common.py` | `viewer_or_403`, period helpers |
| `frontend/src/pages/madrich/Dashboard.jsx` | Extend with availability card |

# Unit Head Flow — Step 7_7 (Stories 10-17)

## Overview

A Unit Head (UH) supervises one or more bunks within a program and
files their own daily self-reflection. The flow surfaces:

1. **Dashboard** — supervised bunks with attention badges, plus the UH's
   own reflection card.
2. **Bunk drill-down** — Bunk Dashboard for one supervised bunk, scoped
   so the UH sees only their own caseload.
3. **Camper drill-down** — Camper Dashboard for one camper within a
   supervised bunk.
4. **Self-reflection** — daily UH reflection with a Day-Off shortcut
   and a `bunk_concerns_bunks` multi-select that resolves dynamically
   from the supervised bunk list.

## Invariants

- A UH viewer must have an active Membership with `role="unit_head"`
  in the current org/program. `viewer_or_403(request)` enforces both
  the role and the supervision footprint.
- The UH dashboard is scoped by the active `Supervision` rows where
  `supervisor_membership=<uh>` AND `target_type="bunk"`. Bunks outside
  this list never appear, even if the UH is a member of the same
  program.
- The UH self-reflection's `bunk_concerns_bunks` field uses
  `option_source="supervised_bunks"`. The dashboard endpoint already
  emits the legal bunk list; the frontend splices it into the schema
  before rendering and the backend validates submitted IDs against the
  same query.
- Edit window for self-reflections: until rollover (`get_today(org)`).
  Older reflections are read-only.

## Backend endpoints

| Method | Path | Story |
|--------|------|-------|
| GET | `/api/v1/unit-head/dashboard/` | 10 |
| GET | `/api/v1/unit-head/bunks/<bunk_id>/` | 11 |
| GET | `/api/v1/unit-head/campers/<camper_id>/` | 12 |
| POST/PATCH | `/api/v1/unit-head/self-reflection/[<id>/]` | 16-17 |
| GET | `/api/v1/unit-head/self-reflection/history/` | 17 |

## Attention badges (Story 10 c6)

Per-bunk badge ordering in `ATTENTION_BADGE_ORDER`:

1. `help_requested` — at least one camper with an open Camper Care
   request from this UH's supervised set.
2. `bunk_concerns` — any active UH self-reflection that references
   this bunk via `bunk_concerns_bunks` for the current period.
3. `off_camp` — at least one camper in the bunk is currently off-camp.
4. `low_completion` — counselor reflection completion is below 50% of
   expected by the program's `expected_by_time` (default 18:00 local).

Badged bunks rise to the top of the dashboard; unbadged bunks sort
alphabetically below.

## Self-reflection flow

```
            ┌────────────────────────────────────────────┐
            │ GET /unit-head/self-reflection/<id>/        │
   start ─► │   (or dashboard.self_reflection.template_id) │
            └────────────────────────────────────────────┘
                          │
                          ▼
            ┌────────────────────────────────────────────┐
            │ If today's reflection exists → redirect to  │
            │ /unit-head/self-reflection/<id>/edit         │
            └────────────────────────────────────────────┘
                          │
                          ▼
            ┌────────────────────────────────────────────┐
            │ POST /unit-head/self-reflection/   (create) │
            │ PATCH /unit-head/self-reflection/<id>/      │
            └────────────────────────────────────────────┘
```

- Idempotency: `client_submission_id` (UUID) on POST. A second POST
  with the same id returns the original row.
- Day off: setting `day_off=true` blanks out `answers` server-side and
  marks the row `is_complete=True`.
- Language: `language` stays as originally submitted unless the user
  explicitly changes it; the frontend prompts for confirmation before
  switching on edit.

## Frontend pages

| Route | Component |
|-------|-----------|
| `/unit-head` | `UnitHeadDashboard.jsx` |
| `/unit-head/bunks/:bunkId` | `UnitHeadBunkDashboardPage.jsx` |
| `/unit-head/campers/:camperId` | `UnitHeadCamperDashboardPage.jsx` |
| `/unit-head/self-reflection[/...]` | `UnitHeadSelfReflectionPage.jsx` |
| `/unit-head/self-reflection/history` | `UnitHeadSelfReflectionHistoryPage.jsx` |

The bunk / camper drill-downs share the `BunkDashboard` and
`CamperDashboard` components used elsewhere, but mount them with the
UH scope so reflections + flags + concerns are filtered to the
supervised set.

## Caching

The dashboard endpoint stores a 30s entry per `(organization, viewer,
day)`. Writes to a UH or counselor reflection bump the same generation
key the counselor dashboard uses so the freshness story is consistent
across roles.

## Deliberate non-goals

- No write access to camper records from the UH surface — UH reads
  notes / orders / reflections; counselors and Camper Care write them.
- No cross-program supervision — `Supervision.target_program` always
  pins the UH's caseload to a single program.
- No off-camp scheduling from the UH dashboard — that flow lives in
  the counselor surface; UH consumes the resulting `off_camp` badge.

# Maintenance Staff Flow

**Step:** 7_10 | **Stories:** 30–36

## Overview

Maintenance staff see a single ticket queue immediately after sign-in. There is no self-reflection requirement for this role. The queue shows all tickets for the program; it is a team queue — every maintenance staff member sees all tickets.

## Key invariants

- Ticket states: `new → in_progress → fulfilled | unable_to_fulfill`. Both terminal states can reopen to `in_progress`.
- Urgency: `low | normal | urgent`. Urgent requires a non-empty `urgent_reason`.
- Queue default sort: urgency (Urgent first) then age (oldest first).
- Notes use `OrderActivityEvent(event_type='note')`. Visibility stored in `metadata["visibility"]`: `team_only` (default) or `submitter_visible`.
- Note edit window: 24 hours from original submission, original author only.
- State transition correction window: 5 minutes, shared with the camper-care state machine (Step 7_2).

## Endpoints (Step 7_10)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/maintenance/queue/` | Active/closed queue with filter + search |
| GET | `/api/v1/maintenance/tickets/<id>/` | Full ticket detail + activity + photos |
| POST | `/api/v1/maintenance/tickets/<id>/notes/` | Add note (visibility required) |
| PATCH | `/api/v1/maintenance/tickets/<id>/notes/<note_id>/` | Edit note within 24h |
| GET | `/api/v1/maintenance/notes/audience/` | Audience disclosure label for form |
| POST | `/api/v1/maintenance/<id>/transition/` | State transition (Step 7_2) |
| POST | `/api/v1/maintenance/<id>/correct-last/` | Undo last transition (5-min window) |
| POST | `/api/v1/maintenance/bulk-transition/` | Bulk fulfill (Step 7_2) |

## Queue filters

`?filter=open` (default) | `new` | `in_progress` | `closed` | `all`

Closed filter also accepts `?search=<text>` (matches description, location, category, note bodies) and `?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`.

## Note visibility

| Value | Visible to |
|-------|-----------|
| `team_only` | Maintenance staff, Admin |
| `submitter_visible` | Submitting counselor, Unit Head, Maintenance staff, Leadership Team, Admin |

## Daily digest email (Story 36)

Configured per org in `Organization.settings`:
- `maintenance_digest_email` — recipient address (required to enable)
- `maintenance_digest_time` — HH:MM in org timezone, default `"06:00"`

The Celery Beat task `maintenance.dispatch_daily_digests` runs hourly and fans out one `send_maintenance_digest` task per eligible org/program. Consecutive send failures are counted in `Organization.settings["maintenance_digest_consecutive_failures"]`; three or more consecutive failures emit a `logger.error` for Datadog alerting.

## Frontend routes

| Path | Component |
|------|-----------|
| `/maintenance` | `pages/maintenance/Queue.jsx` |
| `/maintenance/tickets/:ticketId` | `pages/maintenance/TicketDetail.jsx` |

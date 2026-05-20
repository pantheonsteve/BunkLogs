# Step 7_10: Maintenance Flow

**Goal:** Implement the Maintenance Staff flow per Stories 30-36.

**Canonical product spec:** `docs/user_stories/05_maintenance/STORIES.md`

**Depends on:** 7_1, 7_2 (state machine), 7_4, 7_6 (counselor submission side).

**Scope of this step:**

1. Backend: confirm `core.MaintenanceTicket` model exists with state machine integration (Step 7_2). Urgency field with enum Low/Normal/Urgent. Urgent_reason TextField nullable. Photos as ManyToMany to a TicketPhoto model with upload to S3-compatible storage (existing setup).
2. Backend: API endpoints under `/api/v1/maintenance/`:
   1. `GET /api/v1/maintenance/queue/?filter=<>` — Active queue per Story 30. Filters: Open / New / In Progress / Closed / All.
   2. `GET /api/v1/maintenance/tickets/<id>/` — ticket detail (Story 31).
   3. `POST /api/v1/maintenance/tickets/<id>/transition/` — via state machine.
   4. `POST /api/v1/maintenance/tickets/<id>/notes/` — add note (Story 33).
   5. `PATCH /api/v1/maintenance/tickets/<id>/notes/<note_id>/` — edit within 24h.
   6. `POST /api/v1/maintenance/tickets/<id>/correct-last-transition/` — 5-min correction window.
   7. `POST /api/v1/maintenance/tickets/<id>/reopen/` — reopen (Story 35).
3. Backend: implement note visibility per Story 33 — team-only (default) vs. submitter-and-team. Visibility enforced at note ViewSet.
4. Backend: bulk transition for Maintenance per state machine.
5. Backend: search across closed tickets per Story 35 criterion 2. PostgreSQL FTS on description + note bodies (team-only and submitter-visible).
6. Backend: Celery Beat task for daily digest email per Story 36. Send time configurable per org (Story 58). Default 06:00 org-local. Digest content per Story 36 criterion 4.
7. Backend: digest send failures logged to Datadog. 3+ consecutive failures alert Admin per Story 36 criterion 9.
8. Frontend: implement Maintenance queue at `frontend/src/pages/maintenance/Queue.jsx`. Virtualized list per Story 30 criterion 8. Default sort by urgency then age. NO self-reflection card.
9. Frontend: implement ticket detail at `frontend/src/pages/maintenance/TicketDetail.jsx`. Sections per Story 31 criterion 1.
10. Frontend: note form with team-only vs. submitter-and-team radio. AudienceDisclosure updates dynamically.
11. Frontend: bulk select + bulk fulfill in queue (Story 23 pattern adapted for tickets).
12. Frontend: closed view with search per Story 35.
13. Tests:
    1. Backend: state machine tests via existing 7_2 work; tickets-specific transition tests.
    2. Backend: urgency enum + Urgent reason required validation.
    3. Backend: digest generation test (mock email send; verify content includes all six sections).
    4. Backend: closed-ticket search.
    5. Frontend: queue rendering, virtualized scroll, filters.
14. Documentation: `docs/role_flows/maintenance.md`.

**Commit scope: `feat(7_10_maintenance_flow): ...`. PR title prefix: `7_10`.**

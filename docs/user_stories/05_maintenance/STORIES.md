# Maintenance Staff Flow — Stories 30-36

## Story 30: Sign in and see active queue

### Acceptance criteria

1. Sign-in per Story 1.
2. Post-login IS the Maintenance ticket queue. No separate dashboard, no reflection prompts, no widgets.
3. Queue defaults to **Open tickets** (New + In Progress), sorted: urgency first (Urgent → Normal → Low), then age (oldest first) within urgency.
4. Each row: urgency badge (when Urgent only), status badge (New/In Progress), location, category (Story 8 enum), one-line description, submitter name, submission time with age indicator past configured threshold, photo thumbnail when attached, acknowledger indicator when teammate moved to In Progress (name + relative time).
5. Status filter at top: Open (default) / New / In Progress / Closed / All.
6. Count summary in header: *"[n] new • [m] in progress • [k] urgent."*
7. Single team queue: all Maintenance staff see all tickets. No per-staff assignment.
8. List virtualized, responsive at 500+ tickets backlog on mid-tier Android 4G.
9. No self-reflection card. Maintenance has no reflection requirement.

## Story 31: Open ticket and read full request

### Acceptance criteria

1. Ticket detail sections: **Header** (location/category/urgency w/ reason if Urgent/status/submitter/time), **Description**, **Photos** (swipeable gallery, tap for fullscreen with pinch-to-zoom), **Activity** (chronological status changes + notes + counselor follow-up comments per Story 8 criterion 7), **Actions** (per current status).
2. Actions pinned to bottom on mobile; accessible without scrolling past Activity.
3. Multiple photos: original-submission photos in header gallery; team-added photos interleaved chronologically in Activity. In-progress photos appear with their notes.
4. Activity shows every event: actor, timestamp, event type (status change / note / photo added / urgency-adjusted), attached note if any.
5. Back affordance returns to queue with prior filter state and scroll position preserved.
6. Add follow-up note without status change inline within view — no modal, no separate page.

## Story 32: Acknowledge and mark In Progress

### Acceptance criteria

1. New ticket displays primary "Mark In Progress" action in detail view.
2. Tap transitions ticket to In Progress per state machine. No confirmation modal (5-min correction window applies).
3. Transition records: actor, timestamp, no required note (optional note input visible).
4. After transition, queue row updates: status badge In Progress, acknowledger indicator name + relative time.
5. Action transforms to "Add update" and "Mark Fulfilled" (Story 34) on detail.
6. Within 5-min correction window: "Undo acknowledgment" in overflow menu on detail. After 5 min, state stays; new transitions only.
7. Submitter's view shows updated status on next dashboard load.
8. Team queue row updates for all other Maintenance staff on next queue load.

## Story 33: Add notes about a ticket

### Acceptance criteria

1. "Add note" affordance available on detail for New or In Progress tickets. Closed tickets read-only (reopen path per Story 35).
2. Note form: **Body** (required, plain text), **Photo** (optional, Take/Choose per Story 8 criterion 1.iv), **Visibility** (required radio: *Team only* default / *Submitter and team*), timestamp/author auto-captured.
3. *Team only*: visible to Maintenance Staff (all), Admin.
4. *Submitter and team*: visible to *Team only* audience + submitting counselor + bunk's UH + Leadership Team.
5. AudienceDisclosure component on form, updating with visibility radio:
   - Team only: *"This note will be visible to: Maintenance team, Admin."*
   - Submitter and team: *"This note will be visible to: Submitting counselor, Unit Head, Maintenance team, Leadership Team, Admin."*
6. Notes appear in Activity per Story 31 criterion 4.
7. Edit own notes within 24 hours (matches Camper Care notes window from Story 21).
8. Cannot edit other Maintenance staff notes.
9. Cannot delete notes. Follow-up notes for corrections.
10. Network-tolerant submission and photo upload. Pending state on queued notes in Activity.

## Story 34: Update progress with status changes

### Acceptance criteria

1. In Progress ticket displays two terminal actions: **Mark Fulfilled** (primary, optional note), **Mark Unable to Fulfill** (secondary, required reason).
2. Mark Fulfilled transitions to Fulfilled per state machine. Closing note in Activity attached to status change.
3. Mark Unable to Fulfill requires reason (min 10 characters). Reason in Activity.
4. Both transitions record actor, timestamp, note.
5. Closing moves ticket out of Open queue. Accessible via Closed/All filter or search (Story 35).
6. Submitter's view shows new terminal status on next dashboard load.
7. Unable to Fulfill is terminal; no auto-routing. Escalation is separate action.
8. New → Unable to Fulfill direct transition supported (no In Progress required). Example: duplicate ticket closure.

### Decisions

- M1: No "blocked/awaiting parts" status; In Progress with notes documents the wait.

## Story 35: View closed tickets and reopen

### Acceptance criteria

1. Closed filter shows Fulfilled/Unable to Fulfill, sorted close-date descending.
2. Closed view supports date-range filter and search. Search matches location, category, description, note bodies.
3. Search results: same row shape as open queue + closed status badge + close date.
4. Closed ticket detail displays **Reopen** action.
5. Reopen transitions from Fulfilled/Unable to Fulfill → In Progress per state machine. Required reason note. Records actor, timestamp, reason.
6. Reopened tickets at top of open queue with **Reopened** badge.
7. Full history preserved across reopen events: original submission + all prior activity + prior closure + reopen with reason. Multiple cycles supported.
8. No time limit on reopening. Closure events older than current program de-emphasized visually in Activity.
9. Submitting counselor CANNOT reopen. Counselor submits fresh ticket if problem recurs. Maintenance can link tickets via note.
10. 24-hour note edit window does NOT reset on reopen. Note from original day stays locked when reopened months later.

## Story 36: Daily digest email

### Acceptance criteria

1. Daily digest sent to single org-configured Maintenance team email (Story 58). Individual per-staff delivery NOT in scope.
2. Send time configured per org. Default 06:00 in org timezone (per M2).
3. Window: 24 hours ending at prior day's rollover boundary.
4. Contents in order:
   1. **Summary line** — counts: "[n] new • [m] closed • [k] still open • [u] urgent open."
   2. **Urgent open** — all In Progress/New marked Urgent, oldest first. Each: location, category, description (truncated), age, deep link.
   3. **New in window** — tickets opened. Each: location, category, urgency if Urgent, description (truncated), submitter, deep link.
   4. **Closed in window** — tickets closed. Each: location, category, final status, closing note (truncated), deep link.
   5. **Reopened in window** — each: location, category, reopen reason, deep link.
   6. **Still open at window end** — all New/In Progress not closed, oldest first, compact format, deep link.
5. Deep links open ticket detail in app. Auth handled by existing session; unauthenticated redirects through sign-in then back.
6. Photos NOT embedded inline. "(photo attached)" marker links to ticket.
7. Plain text + HTML versions. HTML readable on iOS Mail, Gmail mobile without horizontal scroll.
8. Zero activity, zero open tickets: digest STILL sends with "all clear" body. No silent skip.
9. Send failures logged to Datadog. 3+ consecutive day failures alert Admin.
10. Delivery via existing email infra (SendGrid/Postmark). Celery Beat scheduled with per-org send time.

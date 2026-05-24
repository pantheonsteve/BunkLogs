# Story 66: Compose a Note with audience and optional camper reference

**As any role with an active Membership, I want to compose a Note with a clear audience picker and optional camper reference, so the right people see it and I can link it to context when relevant.**

## Acceptance criteria

1. The Note composer is reachable from:
   1. The Notes page Compose button (Story 67)
   2. The Story 69 cross-reference path (UH starts a Note from a Bunk concern)
   3. The Story 70 cross-reference path (Counselor or Specialist starts a Note from a Specialist camper note)
   4. Any future per-role entry point added as roles are wired into v1
2. The composer captures, in order:
   1. **Audience** — required, multi-select from the author's role-permitted options per `audience_matrices.md`
   2. **Subject** — required, single line, max 200 characters
   3. **Body** — required, multi-line free text, max 10,000 characters
   4. **Optional camper reference** — autocomplete from campers the author has visibility to (per visibility model); when set, the note appears on the camper's profile per visibility rules
   5. **Optional source reference** — set automatically when arriving via cross-reference (Stories 69, 70); not user-editable, but the user can remove it before submission with a clear affordance
3. Audience selections are explicit — the composer does not infer or pre-select audience based on subject or body text. The author always knows who will receive the note.
4. The composer renders the `AudienceDisclosure` component (per the cross-cutting visibility model) below the audience field with the resolved recipient list. The disclosure updates as audience selections change. Example: *"This note will be visible to: Brent (UH, your supervisor), Administration."*
5. The composer supports auto-save of drafts locally (per author + draft id key in localStorage) every 30 seconds and on field blur, so an interrupted compose can be resumed.
6. Submission is network-tolerant per the existing pattern from Counselor Story 7 criterion 6 (queue locally if connectivity drops, send when reconnected, visible "pending" state).
7. Audience must include at least one role-permitted recipient that is not the author. Note-to-Self is not supported (per decision N1).
8. After submission, the note appears in the author's Sent (Story 67) immediately and in each recipient's Inbox on next page load or refresh.
9. Audience resolution is captured at write-time as an audit artifact: the system records which specific Person records the role-based audience resolved to at submission. Subsequent changes to Membership do not change who can read this note.

## Design notes

- Criterion 3 (audience-first composition) is the central UX choice. The wrong design is "write the note, then decide who sees it" — that invites under- or over-sharing. The right design is "decide the audience, then write to that audience" — it shapes what the author writes.
- The `AudienceDisclosure` reuse keeps the visibility model legible across surfaces. A counselor reading "This will be visible to: your UH, Administration" knows exactly what they're doing.
- Optional camper reference (criterion 2.iv) is what lets a counselor write "heads up about Sarah tomorrow" without forcing every camper-related note through the Specialist camper-note shape. The note appears on Sarah's profile per visibility, but it's a Note (two-way, threaded) not a chart-style note.
- The captured-at-write-time audience resolution (criterion 9) matters for two reasons: (a) audit integrity — the historical record of who saw what stays stable even if roles change later, and (b) a counselor who moves to a different bunk doesn't lose access to notes they sent or received in their prior role.

## Decisions

- N1 (`../00_cross_cutting/decisions.md`): Note-to-self not supported.
- N3: Notes is a platform primitive; audience matrix lives in `audience_matrices.md`.
- N4: v1 author roles limited to Counselor and Unit Head.

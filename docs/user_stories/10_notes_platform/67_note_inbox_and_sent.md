# Story 67: Notes Inbox, Sent, and Archive

**As any role with an active Membership, I want a dedicated page where I can see notes I've sent and notes others have sent to me, with full threaded conversations — so I have a real communication channel that the existing one-way surfaces don't provide.**

## Acceptance criteria

1. The Notes page is reachable from the sidebar (added to the MY WORK section per `migration_prompts/7_19_notes_platform.md` — see "Sidebar integration" below) and from the my-tasks queue (per Counselor Story 10 revised criterion 4 — but note that no canonical "Story 10 revised" exists yet; this story documents the queue integration for both v1 roles).
2. The page is structured as three tabs or sections, in order:
   1. **Inbox** — notes where the user is in the resolved audience, sorted by most recent activity (new note or new reply) descending. Notes with unread replies have a visual unread indicator.
   2. **Sent** — notes the user authored, sorted by most recent activity descending.
   3. **Archive** — notes either side has archived, behind a "View archive" toggle; not loaded by default.
3. A **Compose** button at the top of the page opens the Note composer (Story 66).
4. Each note row in Inbox or Sent shows: subject, author (in Inbox) or audience summary (in Sent), most recent activity time relative to now ("2 hrs ago", "yesterday"), and an unread indicator when applicable.
5. Tapping a note opens the thread view (Story 68), where the original note and all replies are visible in chronological order.
6. The Inbox shows notes addressed to the user via:
   1. Direct addressing (the user's Person record was in the captured audience)
   2. Role-based addressing where the user held the role at the time of submission (e.g., a counselor on Bunk Maple sees notes sent to "counselors on Bunk Maple" while their Membership was active)
7. A note archived by the user disappears from their Inbox or Sent but remains visible to other audience members until they archive their own copy. Archived notes are never deleted; the audit trail is preserved (per decision N9).
8. The page respects the visibility model — a user cannot see notes they are not part of, regardless of subject, referenced camper, or referenced source.
9. The Notes page first contentful paint completes in under 2 seconds on a mid-tier Android phone over 4G, matching the perf bar set by other primary surfaces.
10. The unread count badge on the sidebar Notes link matches the count of Inbox notes with unread activity. The count updates on page navigation; v1 does not push live updates (per Tier 1 scope, consistent with LT12 for response feed).

## Sidebar integration

The Notes link lives in the MY WORK section of `Sidebar.jsx` (the shipped 3.32 IA), between "My reflections" and "Orders". Gated as: any authenticated user with at least one active Membership in a v1-enabled role (Counselor or Unit Head per N4). When the user has no active Membership in a v1-enabled role, the link is not rendered.

## Design notes

- "Most recent activity" sort (criterion 2) ensures that an old note with a new reply pops back to the top, which is how the page will actually be used in practice.
- Archive (not delete) preserves the supervisory record. A counselor cannot make a note disappear from their UH's record by archiving on their end (decision N9).
- The unread indicator is per-user, derived from the read receipts model (Story 68). When the user opens a thread, their unread state for that note clears.
- The role-based addressing path (criterion 6.ii) is what makes "notes to all counselors on Bunk Maple" work without manually addressing each counselor. The audit-captured resolved audience (Story 66 criterion 9) is what makes this stable as Memberships change.

## Decisions

- N4: v1 sidebar visibility limited to Counselor and Unit Head.
- N9: Archive is per-user; preserves audit trail.
- LT12 (`../00_cross_cutting/decisions.md`): No live response feed in Tier 1; manual refresh.

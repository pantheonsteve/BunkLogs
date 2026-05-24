# Story 68: Reply to a Note thread

**As any audience member of a Note, when I receive a Note that needs a response, I want to reply in the thread so the conversation stays in one place and everyone in the audience sees it.**

## Acceptance criteria

1. The Note thread view (reached by tapping a note in Inbox, Sent, or Archive per Story 67) shows the original note at top, followed by all replies in chronological order, with the most recent at the bottom.
2. Each entry shows: author name and role label (the role the author held when the note or reply was submitted), timestamp, body, and optional source reference indicator.
3. Audience is shown once at the top of the thread, not per-entry — every entry goes to the same audience as the original note. The audience display reuses the `AudienceDisclosure` component pattern.
4. A **Reply** affordance at the bottom of the thread opens an inline composer with body field only — audience, subject, and references are inherited from the original note and not editable in the reply path.
5. Submitting a reply adds it to the thread immediately for the author. Other audience members see it on next page load or refresh (per Tier 1 scope; no live updates).
6. Replies are not editable after submission (per decision N8). A correction requires a follow-up reply. The thread holds both the original and the correction; the audit value of the thread depends on knowing what was actually said.
7. The thread shows per-entry read indicators — a small avatar-or-initial list below each entry showing which audience members have opened the thread at or after that entry was posted. v1 displays this as "Read by N of M"; expansion to per-person identities is Tier 2.
8. The thread can be archived per Story 67 criterion 7. Archiving by the current user does not affect other audience members' views.
9. When a reply lands, the note's "most recent activity" timestamp updates and the note bubbles to the top of every audience member's Inbox.
10. Opening a thread that contains unread content (the original note or one or more replies the user has not yet seen) writes read receipts for all visible entries authored before the current user's last view. The thread's unread state for the user clears as a side effect of opening.
11. The thread view shows source reference indicators when present:
    1. **Source-of: Bunk concern** — links to the original concern in read-only view, scoped per the visibility model. Reader access to the source is NOT granted by thread participation (per decision N7) — the indicator shows but the link is disabled or returns 403 if the reader doesn't independently have access.
    2. **Source-of: Specialist note** — same pattern, links to the Specialist note read-only view, gated by independent access.

## Design notes

- The no-edit constraint on replies (criterion 6) is deliberate. Notes are communication; their audit value depends on knowing what was actually said. If a user wants to clarify, they reply again — the thread holds the correction.
- Read indicators (criterion 7) help recipients know when they've been heard. Without them, a counselor sending a note to their UH wonders for hours whether the UH has seen it.
- The "Read by N of M" form (criterion 7) is the Tier 1 compromise: useful signal without the privacy and engineering complexity of per-person tracking. Some users will want to know exactly who has read; that's fair feedback for Tier 2.
- Criterion 11's "indicator but no transitive access" is the practical implementation of decision N7. A UH starting a thread from a counselor's Bunk concern and adding admin to the audience does NOT thereby give admin access to the reflection that holds the concern — admin would need their own role-based access to that reflection, which they have. But for a hypothetical recipient who doesn't have admin's broad-read, the indicator shows without the link working.

## Decisions

- N7: Cross-reference access is not transitive.
- N8: Replies are not editable post-submission.
- LT12: No live updates; manual refresh.

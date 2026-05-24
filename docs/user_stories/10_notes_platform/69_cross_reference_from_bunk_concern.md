# Story 69: Cross-reference — start a Note from a Bunk concern

**As a Unit Head (or Admin, or other supervisor with visibility to the concern), when I read a Bunk concern raised by a counselor and I want to discuss it, I want to start a Note thread from that concern — so the conversation has context and we don't lose track of which concern we're talking about.**

## Acceptance criteria

1. When an authorized supervisor views a Bunk concern (per UH2 in decisions.md, the concern is an optional field on the counselor self-reflection), a **Start a Note from this concern** affordance is rendered on the concern.
2. The affordance is rendered for: UH (the concerned bunk's UH), Leadership Team, Admin. It is not rendered for the original concern's author (the counselor); see open question below.
3. Tapping the affordance opens the Note composer (Story 66) with:
   1. **Audience** pre-filled to: the original concern's author (the counselor) plus the supervisor starting the thread. The supervisor can add other recipients from their role-permitted options.
   2. **Subject** pre-filled with a prefix indicating source, e.g., *"Re: Bunk concern from Brent, June 5"*. Editable.
   3. **Source reference** set to the original Bunk concern (the parent reflection's concern field). Not user-editable, but removable with a clear affordance (Story 66 criterion 2.v).
   4. **Body** empty for the supervisor to fill in.
4. All pre-filled fields are editable by the supervisor before submission — the supervisor can change the audience, edit the subject, etc.
5. The resulting Note appears in the counselor's Inbox (Story 67) with a clear indicator that it references their original concern. Tapping the indicator opens the concern in read-only view per Story 68 criterion 11.
6. From the counselor's own view of the concern (in their self-reflection history), an indicator shows that Note threads have been started from it, with a count and a link to those threads. The counselor only sees indicators for threads where they are in the audience.
7. The original Bunk concern is not modified by the creation of a referencing Note. It remains as authored, and its edit-window rules (per Counselor Story 6) are unaffected.
8. Multiple Note threads can reference the same Bunk concern. Each thread is independent — archiving or replying in one does not affect others.

## Open question

- **Can the counselor start a Note from their own Bunk concern?** Currently criterion 2 says no. The argument for yes: a counselor who realizes after submitting that they want to add context or ask a question could do so via this path rather than composing a fresh note and manually wiring context. The argument for no: keep the workflow division clear — counselor raises, supervisor decides to escalate. Recommended for v1: no. Revisit if counselors ask for it.

## Design notes

- This is the heart of the May 23 decision to keep Bunk concerns and Notes distinct but cross-referenced (per N2). The low-friction concern surface (a field on the reflection) is preserved. The two-way conversation when supervisors decide one is warranted is a single tap away.
- The supervisor initiates this flow, not the counselor. The counselor's job was to raise the concern; the supervisor's job is to decide whether it warrants a conversation. This division of labor matches how the work actually flows.
- Pre-filled but editable (criterion 4) is the right pattern: the system makes the easy path obvious without locking the supervisor into it.
- The "indicator on the concern" (criterion 6) closes the loop for the counselor: they can see that their concern was acted upon, even if they're not the one who initiated the thread.

## Decisions

- N2: Keep Bunk concerns and Notes distinct primitives; this story is the cross-reference mechanism.
- N7: The Note thread does NOT grant access to the source concern; the counselor still has to be in the thread audience to see the thread, and the thread audience does not automatically gain access to the concern's surrounding reflection.
- UH2 (`../00_cross_cutting/decisions.md`): Bunk concerns are an optional field on counselor self-reflection, not a separate submission. This story builds on that shape.

# Story 70: Cross-reference — start a Note from a Specialist camper note

**As a Counselor (or Specialist) reading a Specialist's note about a camper, when I want to discuss it with the Specialist or escalate it to my supervisor, I want to start a Note thread from that camper note.**

## Acceptance criteria

1. When a Counselor views a non-sensitive Specialist camper note on the camper's profile (per Specialist Story 26 visibility rules), a **Reply with a Note** affordance is rendered on the note.
2. When a Specialist views one of their own camper notes (per Specialist Story 27), the same affordance is rendered, allowing them to start a thread about their own observation.
3. The affordance is NOT rendered to other supervisor roles (UH, Camper Care, Leadership Team, Admin) in v1. These roles read Specialist notes via the camper profile but do not start Note threads from them in v1; that wires in when their flows are revised. (See decision N4.)
4. Tapping the affordance opens the Note composer (Story 66) with:
   1. **Audience** pre-filled to: the Specialist who authored the note plus the user starting the thread. The user can add other recipients from their role-permitted options.
   2. **Subject** pre-filled with a prefix indicating source, e.g., *"Re: Specialist note about Sarah L. from June 5"*. Editable.
   3. **Camper reference** set to the camper named in the Specialist note. Editable to remove if the user wants the thread to not appear on the camper's profile.
   4. **Source reference** set to the Specialist's note. Not user-editable, but removable with a clear affordance.
   5. **Body** empty for the user to fill in.
5. All pre-filled fields are editable by the user before submission. The user can, for example, add the UH to the audience to escalate, or change the subject.
6. The resulting Note appears in the audience members' Inboxes per Story 67. The thread shows the source reference indicator per Story 68 criterion 11.
7. The original Specialist note is not modified by the creation of a referencing Note. It stays as authored, including its 24-hour edit window (per S4/S5 in decisions.md).
8. From the Specialist's view of their own note (in their notes history), an indicator shows that Note threads have been started from it, with a count and links. The Specialist only sees indicators for threads where they are in the audience.
9. Sensitive Specialist notes do NOT render the affordance. A Counselor cannot see a sensitive Specialist note (per Specialist Story 26 visibility), so the affordance is moot there. A Specialist viewing their own sensitive note also does not get the affordance in v1 — sensitive note communication is the responsibility of Camper Care (per visibility model); when Camper Care is wired into v1, this constraint can be revisited.

## Design notes

- This story applies the same cross-reference pattern as Story 69 (Bunk concern), but in the other direction. The reader of the source content (counselor, or the specialist themselves) initiates here, because the reader is the one who wants to discuss.
- Camper notes are part of the camper's longitudinal record (a Specialist's observation is data, not communication). The cross-referenced Note thread is communication *about* that record. Keeping them distinct preserves the record's integrity while allowing the communication to happen.
- The sensitive-note carve-out (criterion 9) is the right v1 boundary. Camper Care's wellness-scoped notes have their own communication patterns that should be designed when Camper Care is wired into Notes v2.
- The camper reference (criterion 4.iii) is editable so the user can choose whether this conversation should appear on the camper's profile. Sometimes "discuss the framing of this note" is meta-conversation that shouldn't show up as a camper-record entry; sometimes it should.

## Decisions

- N2: Notes and Specialist camper notes are distinct primitives; this story is the cross-reference mechanism.
- N4: Affordance available to Counselor and Specialist in v1; other roles wire in as their flows are revised.
- N7: Thread participation does not grant access to the source note; sensitive notes remain invisible to non-audience readers.
- S4, S5 (`../00_cross_cutting/decisions.md`): Specialist note deletion not permitted; edits within 24h; cross-referenced Note thread is independent of those rules.

# Story 3: See which campers in my bunk still need a reflection

**As a Counselor, I want to see my bunk roster with each camper's submission status for today, so I know who still needs one.**

## Acceptance criteria

1. The dashboard's camper reflections section opens to a roster list scoped to the user's active Bunk assignment(s) for today.
2. Each row shows: camper preferred-or-first name + last initial, age or grade if available, and a submission status: **submitted** or **not submitted**.
3. For a submitted reflection, the row shows the submitter's name when it's another counselor on the bunk; it shows nothing extra when it's the current user's own submission.
4. Submitted rows are visually distinct from not-submitted rows such that a viewer can identify all not-submitted campers without reading any text.
5. Tapping a not-submitted row opens the reflection form for that camper.
6. Tapping a submitted row opens the reflection in read-only view with an "Edit" affordance (Story 4).
7. A running count appears at the top: *"[n] of [m] reflections submitted."*
8. Campers marked **off-camp today** appear in a separate "Off camp" sub-section, do not count toward "expected," and cannot have a reflection submitted for them.
9. Roster order is by bunk-defined position if available, otherwise alphabetical by last name.

## Decisions

- C1 (`../00_cross_cutting/decisions.md`): UH or Camper Care marks a camper off-camp; Counselors see the result but don't set it.

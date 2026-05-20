# Story 4: Edit a camper reflection submitted today

**As a Counselor, I want to update a camper reflection submitted today — by me or a co-counselor — so I can add context I noticed later.**

## Acceptance criteria

1. Opening a submitted reflection from today shows it in read-only mode by default with a clearly labeled "Edit" affordance.
2. The Edit affordance is enabled for any Counselor active on the bunk on the reflection's date, regardless of who submitted the original.
3. The reflection record stores both **original submitter** and **last editor** (with timestamps). Both are visible in the read-only view.
4. Edits made after the rollover boundary (i.e., editing yesterday's reflection) are not permitted. The Edit affordance is not rendered for reflections older than today.
5. Editing creates an audit record per the audit trail spec, visible to UH, Camper Care, Leadership Team, and Admin showing the prior version and the edit's author + timestamp. The edit history is not visible to other Counselors.
6. Saving an edit returns the user to the camper list with the reflection still shown as "submitted" — the section's completion count does not change.

## Decisions

- C2: Edit history visible to supervisors only; co-counselors do not see prior versions.

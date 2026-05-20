# Story 9: See an unambiguous "all set" state when today's required work is complete

**As a Counselor, when I've completed today's required work I want the dashboard to clearly show I'm done.**

## Acceptance criteria

1. The dashboard enters an **All set** state when both of these conditions hold:
   1. The camper reflections section is complete (every roster camper has a submitted reflection, accounting for off-camp campers per Story 3 criterion 8).
   2. The self-reflection section is complete (today's reflection submitted, including day-off submissions).
2. The Requests section's state does *not* affect All set. Requests are reactive, not required.
3. The All set state is visually distinct from individual section completion — it's a dashboard-level treatment, not just three green checkmarks.
4. The All set state does not collapse or hide the sections. The user can still tap into any section to view or edit.
5. If a co-counselor submits the final missing camper reflection after the user has closed the app, the dashboard correctly shows All set on the user's next open.
6. The All set state persists for today until either (a) the rollover boundary passes, after which the dashboard resets for the new day, or (b) a previously-submitted reflection is *retracted*.

## Note

Retraction of a submitted reflection is not permitted; corrections are handled via edits within the rollover window. If a submission was truly in error, Admin can override-edit per Story 59.

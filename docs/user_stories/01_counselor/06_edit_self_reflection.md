# Story 6: Edit today's self-reflection; view past reflections read-only

**As a Counselor, I want to update today's self-reflection but have past reflections locked, so my record is honest over time.**

## Acceptance criteria

1. A submitted self-reflection for today displays an "Edit" affordance in its dashboard section and in its detail view.
2. Editing today's self-reflection follows the same edit-window rule as camper reflections: edits permitted until the rollover boundary.
3. A "My reflections" history view lists prior submissions in reverse-chronological order, showing date and a preview line.
4. Each prior submission opens in read-only mode. No "Edit" affordance is rendered for past dates.
5. Attempts to access an edit URL for a past date return a "This reflection is locked" state, not the form.
6. The history view includes days marked **day off** with that state clearly indicated, and days with **no submission** appear as a gap with a "no reflection submitted" indicator.

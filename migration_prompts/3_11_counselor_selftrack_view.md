Per Alyson's notes: "Counselors should be able to see if they have completed the reflections as well." Add a personal completion view.

Tasks:
1. Add route /my-reflections that shows:
   - Current period status (submitted? when?)
   - Last 14 days of reflections (or 4 weeks for weekly cadences)
   - Completion streak
   - Total count completed

2. API: GET /api/v1/reflections/my-summary/ returning the above data.

3. Tests for data correctness and access control.

Acceptance criteria:
- Personal view renders correctly for counselor
- Streak and counts accurate
- Tests pass
- Commit with message: "Add personal reflection tracking view"
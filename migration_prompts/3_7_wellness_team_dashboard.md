Build a separate dashboard for the Wellness team (Camper Care, Health Center, Special Diets). They have their own questions and need their own view.

Tasks:
1. Create route /wellness/dashboard.
2. Permission: Memberships with role in ('camper_care', 'health_center', 'special_diets', 'admin').

3. Sections:
   - Wellness team reflections by sub-role
   - Cross-team patterns (e.g., concerns flagged in counselor reflections that reference wellness)
   - Wellness completion tracking

4. API: /api/v1/dashboards/wellness/

5. Tests for permissions, data correctness, sub-role filtering.

Acceptance criteria:
- Dashboard renders correctly
- Wellness sub-roles get appropriate views
- Permissions enforced
- Tests pass
- Commit with message: "Add Wellness team dashboard"
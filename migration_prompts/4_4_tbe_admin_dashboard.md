TBE admin dashboard. Reuses the team dashboard infrastructure from Wave 3 with TBE-specific filters and views.

Tasks:
1. Route /admin/reflections renders (when org context is TBE):
   - Weekly completion view filtered to TBE Madrichim
   - Filter by grade level (8-12) instead of unit
   - Individual Madrich detail view with reflection history
   - CSV export for board reporting

2. Reuse team dashboard API where possible; add TBE-specific filters where needed.

3. Tests:
   - Renders correctly for TBE admin
   - Grade level filtering works
   - CSV export works
   - Crane Lake admin doesn't see TBE data (cross-org isolation)

Acceptance criteria:
- Dashboard works for TBE
- Tests pass
- Commit with message: "Add TBE admin dashboard with grade-level filtering"
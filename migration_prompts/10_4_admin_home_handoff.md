# 10_4 — Admin home handoff pass

**Step ID:** `10_4_admin_home_handoff`
**Estimated time:** 5–6 hours (split backend/frontend if the diff passes ~1,500 lines)
**Mode:** lean, except the identity payload change (auth-adjacent: test with both orgs)
**Reference:** `docs/dashboard-catalog.md`, pair 1
**Depends on:** 10_2b (so the school cards' copy uses the settled terminology)

```
Goal: the admin home, admin nav, sidebar and Reports hub decide what to
show from per-org feature settings, not from whether the org is a camp or a
religious school. A client admin should never see a setting they can't
understand. No visible change for clc or tbe.

Today:
- frontend/src/utils/auth/orgProfile.js: orgSurfaces(user) returns
  {campOps, campDashboards, observations, gradeReflections} from
  isReligiousSchoolOrg(user), which reads program_types from the per-org
  identity payload (core/identity.py).
- Consumers: AdminHome.jsx (school tabs via directorSections),
  DirectorHome.jsx, adminNavConfig.js (Reports + Setup links), Sidebar.jsx,
  ReportsHub.jsx, AdminReflectionsDashboard.jsx, AdminGrowthDashboard.jsx.
- Backend: api/admin_flow/director.py, nav.py and dashboard.py check
  program_type == "religious_school".

Pre-flight audit (report before writing code):
1. Every consumer of orgSurfaces/isReligiousSchoolOrg and every backend
   program_type check in api/ and core/ (excluding setup/seed commands and
   migrations). For each: which feature it gates, and whether that feature
   would make sense for the other customer type.
2. What the identity payload exposes per org today (program_types,
   terminology, branding) and where the frontend reads it.

Tasks:
1. core/features.py:
   - FEATURES: a dict of feature key -> {description, default_camp,
     default_school}. Start with exactly the keys orgSurfaces covers, named
     for what they are: requests (catalog, orders, maintenance),
     camp_dashboards (group performance, daily logs, coverage, concerns,
     authors), observations, availability, routed_questions,
     reflection_insights (themes + cohort moderation),
     completion_reports (weekly completion + growth by grade).
   - features_for(org) -> dict[str, bool]: Organization.settings["features"]
     overrides, falling back to defaults chosen from the org's active
     program types (all religious_school -> school defaults, otherwise camp
     defaults). This fallback is the ONLY place program_type maps to
     features.
2. Add "features" to the per-org identity payload next to program_types.
3. orgProfile.js: orgSurfaces(user) reads features from the payload. Keep
   the function name and return shape so consumers don't churn; add a
   hasFeature(user, key) helper for new code. Keep the program_types
   fallback only for a payload without features (old cached sessions).
4. Backend: replace program_type gates in admin_flow/director.py, nav.py
   and dashboard.py with features_for(org) checks. Director endpoints must
   still resolve the right program; resolve by "the selected program, else
   the active program" rather than by program_type.
5. Admin Settings page: a "Features" card listing each feature with its
   description and an on/off toggle (admin-only PATCH on org settings,
   audited through the existing audit trail). Plain-language labels, no
   keys shown. Put it next to the Roles and Groups cards from 10_2a.
6. Copy in DirectorHome.jsx and adminNavConfig.js through term():
   "Director", "Faculty responsiveness", "Madrichim", "(faculty)",
   "Madrich completion". Replace "Sunday"/"This Sunday" with wording based
   on program session dates ("Next session", "Upcoming sessions").
7. Sidebar: show Group Performance for any org with camp_dashboards OR
   completion_reports, since the admin home already shows Performance to
   both.

Out of scope (note in the PR, don't build): making routed questions or
insights produce data for camp orgs; merging Coverage with Madrich
completion.

Tests:
- features_for: defaults for a camp org, a school org, and overrides.
- Identity payload includes features for clc and tbe users (two-org test).
- Snapshot of admin nav + admin home tabs for clc and tbe: identical to
  before this step.
- Turning "availability" on for a camp-preset org shows the Staffing tab
  without errors (empty state is fine).
- Guard test: no program_type / isReligiousSchoolOrg reads in
  frontend/src or backend/bunk_logs/api outside an allowlist
  (core/features.py, orgProfile.js fallback, setup/seed commands,
  migrations).

Acceptance criteria:
- clc and tbe admins see exactly what they saw before.
- Any of these features can be switched on or off for any org from
  Settings, with no deploy.
```

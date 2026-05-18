# Prompt 3.25 — `is_staff` / `is_superuser` Super Admin consistency audit

**Wave:** 3 (Crane Lake Summer 2026 Build) — closes item #5 from the
original RBAC guideline.
**Estimated time:** 4-5 hours
**Prerequisites:** Prompts 3.21-3.24 merged (capability + visibility
fields already in place).

**Use the context prompt at the top of `0_0_context_prompt.md` before this session.**

---

```
The new RBAC code (everything under bunk_logs.api.* / bunk_logs.core.* )
checks ``user.is_superuser`` whenever it needs a bypass-all gate, but the
original product guideline (item #5) was: "is_staff is what will signify
Super Admin". The legacy single-tenant code under bunk_logs/api/views.py
already honours that -- it branches on ``is_staff or user.role == "Admin"``
-- and the React frontend already accepts ``is_staff || is_superuser`` in
every gate. The audit closes the gap on the new RBAC code so the three
layers agree on a single definition.

DEFINITION:

A "Super Admin" is any authenticated user where ``is_staff`` OR
``is_superuser`` is true. There is a single helper that returns this:

    bunk_logs.core.permissions.is_super_admin(user) -> bool

Both flags grant bypass-all access (org-scoped reflection visibility,
org-admin endpoints, cross-tenant template / FieldKey management, and
the legacy Crane Lake admin paths). If we ever need a stricter tier
("only Django superusers can edit the global registry"), introduce a
second helper THEN -- don't pre-emptively split the two flags now.

CONTEXT for non-obvious decisions:

- ``is_staff`` is the right primary signal because Crane Lake's existing
  admin staff already have it set (legacy code path); flipping the new
  RBAC code to also honour it lets the support team keep working without
  a flag migration.
- ``api/templates.py`` and ``api/field_keys.py`` cross tenant boundaries
  (list ALL orgs' templates / FieldKeys; edit global rows). They still
  unify on the same helper: anyone we trust as Super Admin can do this.
  Splitting tiers later is cheap if we need it.

Tasks:

1. Add the helper. Put it in ``backend/bunk_logs/core/permissions/super_admin.py``
   and re-export from ``bunk_logs.core.permissions.__init__``::

       def is_super_admin(user) -> bool:
           if user is None or not getattr(user, "is_authenticated", False):
               return False
           return bool(
               getattr(user, "is_staff", False)
               or getattr(user, "is_superuser", False),
           )

   Keep it dependency-free (no Django imports beyond what's in scope
   already). Anonymous / unauthenticated users return False.

2. Sweep the new RBAC code for direct ``is_superuser`` checks and
   replace them with ``is_super_admin(user)``. The full list:

   - ``backend/bunk_logs/core/permissions/visibility.py``
     - the bypass for superuser-without-Person (currently line 232)
     - the org-admin fast path (line 241)
     - ``is_org_admin`` helper (line 276)
     - ``has_supervisor_role`` helper (line 299)
   - ``backend/bunk_logs/core/permissions/drf.py``
     - ``IsOrgAdminOrSuperuser.has_permission`` (line 38). Update the
       ``message`` to mention staff: "Organization admin membership or
       Super Admin status required." Keep the class name unchanged so
       no downstream import breaks; the docstring should reference the
       helper.
   - ``backend/bunk_logs/api/memberships.py``
     - ``MembershipPermission.has_permission`` (line 49). Same docstring
       / message updates as above.
   - ``backend/bunk_logs/api/dashboards/coverage.py``
     - viewer-or-superuser bypass (line 77).
   - ``backend/bunk_logs/api/dashboards/template.py``
     - ``_viewer_can_access_template`` (line 54). Keep the
       ``user.role == User.ADMIN`` arm; that's a legacy role-based
       gate the new helper doesn't subsume.
   - ``backend/bunk_logs/api/wellness_dashboard.py`` (line 48).
   - ``backend/bunk_logs/api/team_dashboard.py`` (line 56).
   - ``backend/bunk_logs/api/reflections.py``
     - ``_privileged_reflection_actor`` (line 41). This is already a
       helper; rewrite its body to delegate to ``is_super_admin``.
   - ``backend/bunk_logs/api/templates.py``
     - get_queryset cross-org bypass (line 183)
     - include_global=false short-circuit (line 205)
     - get_object cross-org bypass (line 214)
     - ``_check_edit_permission`` global-template gate (line 243)
     - clone-template create gate (line 378)
   - ``backend/bunk_logs/api/field_keys.py``
     - all five sites (lines 77, 93, 106, 134, 154).

   Do NOT touch:
   - ``backend/bunk_logs/api/views.py`` -- legacy Crane Lake code,
     already uses ``is_staff`` exclusively.
   - ``backend/bunk_logs/api/permissions.py`` -- ditto.
   - The ``debug_*.py`` / ``scripts/*.py`` files that are private dev
     aids and not on the deploy path.

3. Backend tests. The point is to prove an ``is_staff=True, is_superuser=False``
   user gets the same access an ``is_superuser`` user gets today.

   - In ``backend/bunk_logs/core/permissions/test_visibility.py`` add
     ``TestSuperAdminConsistency``:
     * ``test_is_staff_user_sees_all_org_reflections`` -- create a
       reflection authored by a counselor, then assert an ``is_staff``
       user with NO Person profile gets it back from
       ``reflections_visible_to``.
     * ``test_is_staff_user_is_org_admin`` -- assert
       ``is_org_admin(staff_user) is True``.
     * ``test_is_staff_user_has_supervisor_role`` -- assert
       ``has_supervisor_role(staff_user) is True``.
   - In a new test file ``backend/bunk_logs/core/permissions/test_super_admin.py``
     pin the helper itself:
     * Returns False for ``None`` and anonymous users.
     * Returns False for an authenticated user with neither flag.
     * Returns True for ``is_staff=True, is_superuser=False``.
     * Returns True for ``is_staff=False, is_superuser=True``.
     * Returns True for both flags set.
   - In ``backend/bunk_logs/api/tests/test_template_api.py`` (or
     wherever the templates viewset is exercised) add one smoke
     assertion that an ``is_staff`` user can list templates from
     another org's perspective the same way a superuser can. If the
     existing fixtures don't cover that easily, add one targeted test
     rather than refactoring the suite.
   - In ``backend/bunk_logs/api/tests/test_membership_api.py`` add a
     parallel smoke that an ``is_staff`` user passes
     ``MembershipPermission``.

4. Frontend. The gates already accept either flag, but the check is
   duplicated four times. Extract a helper and migrate the call sites:

   - Create ``frontend/src/utils/auth/isSuperAdmin.js``::

       export function isSuperAdmin(user) {
         return Boolean(user?.is_staff || user?.is_superuser);
       }

   - Replace the inline expressions in:
     * ``frontend/src/Router.jsx`` (the AdminRoute gate)
     * ``frontend/src/partials/Sidebar.jsx`` (the admin-section show/hide)
     * ``frontend/src/api.js`` (the staff date-source branch)
     * ``frontend/src/components/ui/SingleDatePicker.jsx`` (the future-date allowance branch)
     * ``frontend/src/components/form/BunkLogForm.jsx``
     * ``frontend/src/components/form/CounselorLogForm.jsx``
     Keep any extra ``user.role`` checks in those files alongside the
     helper; the helper only covers the Super Admin half.
   - Update ``frontend/src/pages/admin/templates/__tests__/AdminRoute.test.jsx``
     to import the helper too (it currently re-implements the check
     inline; that drift was the original motivation for the audit).
   - Add ``frontend/src/utils/auth/isSuperAdmin.test.js`` covering the
     four input combinations.

5. Documentation. Add a "Super Admin (`is_staff` or `is_superuser`)"
   section to ``docs/membership-role-vs-capability.md`` directly above
   the existing "Per-reflection visibility" section. Three points to
   document:
   - The two-flag definition and the canonical helpers
     (``is_super_admin`` backend / ``isSuperAdmin`` frontend).
   - Which capabilities and code paths a Super Admin bypasses
     (visibility, org-admin endpoints, cross-org template management,
     FieldKey registry).
   - When NOT to add a third tier (we have ``is_superuser``-only checks
     today in templates / FieldKeys; the audit unifies them, and if
     anyone wants a stricter platform-only tier later it should be a
     separate helper named ``is_platform_superuser`` so the intent is
     loud in code review).

Acceptance criteria:
- Every direct ``user.is_superuser`` check in the new RBAC code
  (everything outside ``api/views.py`` and ``api/permissions.py``) now
  routes through ``is_super_admin`` or the frontend ``isSuperAdmin``.
- ``make test-backend`` adds the four new test cases (super-admin
  helper unit + visibility / templates / memberships smoke).
- ``make test-frontend`` adds the helper unit tests.
- ``make lint`` (``ruff check bunk_logs/ config/``) clean.
- Docs page lists the canonical helpers and the bypass scope.

Out of scope:
- Touching the legacy single-tenant code (``api/views.py``,
  ``api/permissions.py``). Those already honour ``is_staff``.
- Introducing a stricter "platform superuser" tier. The audit unifies
  the existing gates -- splitting tiers is a separate prompt if anyone
  asks for it.
- Anything user-management (adding admin UI to toggle ``is_staff``).
  That's a separate UX prompt.

Commit structure (single PR, ordered commits):
  1. feat(3_25_super_admin_audit): introduce is_super_admin helper + unit tests
  2. refactor(3_25_super_admin_audit): switch visibility/drf permissions to helper
  3. refactor(3_25_super_admin_audit): switch dashboards + reflections actor to helper
  4. refactor(3_25_super_admin_audit): switch cross-tenant templates + field_keys to helper
  5. test(3_25_super_admin_audit): pin is_staff bypass behaviour on visibility + permissions
  6. feat(3_25_super_admin_audit): frontend isSuperAdmin helper + call-site sweep
  7. docs(3_25_super_admin_audit): document Super Admin = is_staff || is_superuser
```

Add infrastructure to scope queries by Organization automatically.

Tasks:
1. Create `core/middleware.py` with OrganizationMiddleware:
   - Determine active organization based on:
     a) Subdomain (tbe.bunklogs.net → tbe org, clc.bunklogs.net → crane lake)
     b) Authenticated user's primary organization (fallback)
   - Store on request.organization
   - Use thread-local storage (asgiref.local.Local for async safety)
   - Handle missing org gracefully (None, no crash)

2. Create `core/managers.py` with OrgScopedManager:

class OrgScopedManager(models.Manager):
    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is None:
            return qs.none()  # Fail closed
        return qs.filter(organization=org)

3. Apply OrgScopedManager to Person, Program, Membership, ReflectionTemplate (when org is not null), Reflection. Keep Organization with default manager (we look up orgs without org context).

4. Add `all_objects` manager to each model bypassing scoping.

5. Add MIDDLEWARE entry in settings.

6. Tests:
   - No org context: querysets empty
   - With org context: only that org's data
   - all_objects bypasses scoping
   - Two orgs with separate data don't see each other
   - Subdomain routing resolves correctly

7. CRITICAL: existing Crane Lake endpoints (using old models) UNAFFECTED. Old models don't have OrgScopedManager.

Acceptance criteria:
- New models scoped automatically
- Old models unchanged
- Tests pass including isolation
- Manual smoke test: create two orgs, verify isolation
- Commit with message: "Add multi-tenant middleware and OrgScopedManager"
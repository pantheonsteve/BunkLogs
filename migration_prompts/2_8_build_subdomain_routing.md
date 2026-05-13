Configure subdomain-based organization routing in production. Local dev uses header override.

Tasks:
1. Update `OrganizationMiddleware`:
   - Extract subdomain from request.get_host() (e.g., "clc.bunklogs.net" → "clc")
   - Look up Organization by slug = subdomain
   - In dev: also accept `X-Organization-Slug` header
   - Also accept `?org=slug` query parameter in dev for browser testing

2. Update Django settings:
   - ALLOWED_HOSTS includes `*.bunklogs.net`
   - Decide on SESSION_COOKIE_DOMAIN approach (probably not shared across subdomains)

3. Document subdomain setup in `docs/multi-tenant-routing.md`:
   - How to add a new org (admin + DNS)
   - How to test locally
   - Session behavior across subdomains

4. Tests:
   - Request to clc.bunklogs.net resolves to Crane Lake (when migrated)
   - Request to tbe.bunklogs.net resolves to TBE (when created)
   - Header override works in dev
   - Query param override works in dev
   - Unknown subdomain returns no org (graceful)

Acceptance criteria:
- Subdomain routing works in dev
- Documentation written
- Tests pass
- Commit with message: "Add subdomain-based organization routing"
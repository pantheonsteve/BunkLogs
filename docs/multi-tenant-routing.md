# Multi-tenant routing (subdomains)

## How it works

`OrganizationMiddleware` resolves the current organization from the HTTP host:

- Hosts matching `*.bunklogs.net` use the first DNS label as the organization **slug** (e.g. `clc.bunklogs.net` → slug `clc`, `tbe.bunklogs.net` → slug `tbe`).
- Reserved labels (no tenant lookup): `www`, `admin`, `api`, `localhost`, and the empty label.

If no organization matches the subdomain, `request.organization` is `None`. Authenticated users may still get an organization from their linked `Person` record when the host does not imply a tenant (existing fallback).

The host is read via `request.get_host()` when Django accepts the host; otherwise the middleware falls back to `HTTP_HOST` so tests and edge cases still behave.

## Adding a new organization

1. **Django admin** (or a migration/data script): create an `Organization` with `slug` equal to the subdomain label you will use (e.g. `tbe` for `tbe.bunklogs.net`). Keep `is_active` true.
2. **DNS**: add a CNAME (or A/AAAA) for `{slug}.bunklogs.net` pointing at the same frontend/backend entrypoints you use today (e.g. Render static site + API on `admin.bunklogs.net` or tenant-specific origins as you roll them out).

If `DJANGO_ALLOWED_HOSTS` is overridden in the environment, include `.bunklogs.net` (leading dot) so Django accepts every tenant subdomain, or list each hostname explicitly.

## Local development

- **Header**: With `DEBUG=True` (local settings) or `ORGANIZATION_ROUTING_DEV_OVERRIDES=True` (set in `config.settings.test` so CI can exercise overrides without turning on `DEBUG`), send `X-Organization-Slug: <slug>` on API requests when using `localhost` or another host without a tenant subdomain.
- **Query string**: Same conditions: append `?org=<slug>` for quick browser testing.
- **Real subdomain locally**: Map e.g. `clc.bunklogs.net` to `127.0.0.1` in `/etc/hosts` and include `.bunklogs.net` in `ALLOWED_HOSTS` (already included in `config.settings.local`).

CORS allows the `x-organization-slug` header from browser clients (see `CORS_ALLOW_HEADERS` in base settings).

## Session and CSRF cookies across subdomains

Production (`config.settings.production` and `config.settings.render`) sets:

- `SESSION_COOKIE_DOMAIN = ".bunklogs.net"`
- `CSRF_COOKIE_DOMAIN = ".bunklogs.net"`

so one session can be shared across `admin.bunklogs.net`, `clc.bunklogs.net`, and other subdomains. That matches the current headless Allauth + browser flows where the API and apps live on different subdomains.

**Tighter isolation (optional):** If you want cookies scoped to a single host only, set `SESSION_COOKIE_DOMAIN` and `CSRF_COOKIE_DOMAIN` to `None` (host-only) and rely on JWT or per-subdomain login. That avoids accidental session sharing between tenants on different subdomains but requires coordinated frontend/API auth changes.

## Tests

See `bunk_logs/core/test_multitenancy.py` for subdomain resolution, dev header/query overrides, unknown subdomains, and thread-local cleanup.

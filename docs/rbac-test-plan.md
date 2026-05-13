# RBAC test plan (frontend)

Verification matrix and manual walkthrough for the
`Membership.capability` stack — reflections, templates, `/tasks`,
`/admin/*`, `/dashboards/*`, `/team`, and `/wellness` surfaces. See also
[`docs/membership-role-vs-capability.md`](membership-role-vs-capability.md)
for the underlying design.

## 1. Setup

```bash
make up                # postgres + redis + django + mailpit
make frontend-dev      # vite on :5173 (in another terminal)
make seed-rbac         # creates the test users below + templates + groups
```

Re-running `make seed-rbac` is idempotent: it wipes prior RBAC fixtures
under stable slugs and re-creates them. All users share the password
**`rbacpass123`**.

## 2. Test users

| Key             | Email                                  | Capability         | Membership.role     | User.role     | Notes                                                             |
| --------------- | -------------------------------------- | ------------------ | ------------------- | ------------- | ----------------------------------------------------------------- |
| `counselor`     | `rbac-counselor@example.test`          | `participant`      | `counselor`         | `Counselor`   | Self-reflection author + bunk-group author                        |
| `kitchen`       | `rbac-kitchen@example.test`            | `participant`      | `kitchen_staff`     | `Counselor`   | Bilingual — exercises `?language=es`                              |
| `unit_head`     | `rbac-unit-head@example.test`          | `supervisor`       | `unit_head`         | `Unit Head`   | Direct author of bunk + parent unit                               |
| `leadership`    | `rbac-leadership@example.test`         | `program_lead`     | `leadership_team`   | `Leadership`  | `/team/dashboard`, leadership reflection visibility               |
| `camper_care`   | `rbac-camper-care@example.test`        | `domain_specialist`| `camper_care`       | `Camper Care` | `/wellness/dashboard`; sees wellness reflections                  |
| `health_center` | `rbac-health-center@example.test`      | `domain_specialist`| `health_center`     | `Camper Care` | Second wellness role                                              |
| `admin`         | `rbac-admin@example.test`              | `admin`            | `admin`             | `Admin`       | **Admin via Membership only** (`is_staff=False`)                  |
| `superuser`     | `rbac-superuser@example.test`          | —                  | —                   | `Admin`       | Django superuser, **no Person**; multi-tenant dashboards 403      |
| `no_membership` | `rbac-no-membership@example.test`      | —                  | —                   | (none)        | Authenticated but no `Person` profile                             |
| `tbe_admin`     | `rbac-tbe-admin@example.test`          | `admin`            | `admin`             | `Admin`       | Admin in `tbe-test` org — cross-tenant isolation through `clc`    |

## 3. Automated: Playwright e2e suite

```bash
make test-e2e           # equivalent to: cd frontend && npm run test:e2e
```

Runs three spec files against the local dev stack (requires `make up`,
`make frontend-dev`, `make seed-rbac`):

- `frontend/e2e/rbac-sidebar.spec.ts` — sidebar link visibility per role
- `frontend/e2e/rbac-routes.spec.ts` — API + route gating, including
  cross-tenant isolation and admin-via-Membership writes
- `frontend/e2e/rbac-reflection-visibility.spec.ts` — reflection
  visibility paths (wellness, supervisor coverage), Spanish prompt
  delivery via `?language=es`

The first time, install the browser binary:

```bash
npm --prefix frontend run test:e2e:install   # downloads chromium
```

To override the URLs (e.g. test against a Render preview backend):

```bash
PLAYWRIGHT_BASE_URL=https://my-frontend.onrender.com \
PLAYWRIGHT_API_BASE_URL=https://my-backend.onrender.com \
PLAYWRIGHT_ORG_SLUG=clc \
  make test-e2e
```

## 4. Manual walkthrough (when UI flows change)

For each row, sign in at `http://localhost:5173/signin` and confirm the
expected behaviour. Tick the box once verified.

### Counselor (`participant`)

- [ ] Sidebar shows **My Reflections** + **Program reflection**, hides
      Memberships / Tests submenu / Unit health (LT) / Wellness team.
- [ ] `GET /api/v1/reflections/template-for-me/` returns the daily
      counselor template.
- [ ] `POST /api/v1/reflections/` with the seed payload returns 201
      (then 400 on retry due to `unique(period_start)` constraint).
- [ ] `/api/v1/memberships/` returns **403**.
- [ ] `/api/v1/templates/` POST returns **403** (write).

### Kitchen staff (`participant`, bilingual)

- [ ] `GET /api/v1/reflections/template-for-me/?language=es` returns
      Spanish prompts and `scale_labels.es`.
- [ ] Submitting a reflection with `language: "es"` succeeds and stores
      the locale on the row.

### Unit head (`supervisor`)

- [ ] Sidebar shows base links; admin tools hidden.
- [ ] `GET /api/v1/reflections/supervisor-coverage/` returns the seeded
      bunk group with its allowed templates.
- [ ] Reflections authored by counselors in the unit's bunks are
      visible (descendant traversal via parent unit).

### Leadership (`program_lead`)

- [ ] Sidebar shows **Unit health (LT)**.
- [ ] `GET /api/v1/dashboards/team/` returns 200 with scoped data.
- [ ] Cannot create templates (`POST /api/v1/templates/` → 403).

### Camper care / Health center (`domain_specialist`)

- [ ] Sidebar shows **Wellness team** for both.
- [ ] `GET /api/v1/dashboards/wellness/` returns 200.
- [ ] `GET /api/v1/reflections/?program=summer-2026` includes the
      seeded `clc-2026-camper-care-daily` reflection.
- [ ] The same query as `counselor` does NOT include that reflection.

### Admin via Membership (`admin`)

- [ ] Sidebar shows **Bunk Logs**, **Staff Reflections**,
      **Memberships**, and the **Tests** submenu (with Templates,
      Groups, Tasks, etc.).
- [ ] `GET /api/v1/memberships/` returns 200.
- [ ] `POST /api/v1/templates/` with a unique slug returns 201.
- [ ] `DELETE /api/v1/templates/<id>/` returns 204.

### Superuser (no Person)

- [ ] Sidebar still shows the **Tests** submenu via the
      `is_staff || is_superuser` fallback.
- [ ] `GET /api/v1/memberships/` returns 200.
- [ ] `GET /api/v1/dashboards/team/` returns **403** — multi-tenant
      dashboards require a `Person` row in the org. This is by design;
      assign the user a `Membership(role="admin")` in the org if you
      need dashboard access.

### No Person / Membership

- [ ] Sidebar shows only **Orders**.
- [ ] `GET /api/v1/reflections/template-for-me/` returns 404.
- [ ] `GET /api/v1/memberships/` returns 403.
- [ ] Navigating to `/reflect` does NOT redirect to `/signin` (the
      empty/error state renders client-side).

### TBE admin (cross-org)

- [ ] Sign in as `rbac-tbe-admin@example.test`.
- [ ] The frontend always sends `X-Organization-Slug=clc`, so:
  - `GET /api/v1/memberships/` returns **403** (no admin Membership in
    `clc`).
  - `POST /api/v1/templates/` returns **403**.
  - `GET /api/v1/templates/` returns 200 (read-only list within the
    request org context).

## 5. Cleaning up between runs

```bash
make seed-rbac          # safe to re-run; deletes & recreates fixture data
```

If you need a fully blank slate (e.g. the seed schema changed), run
`make reset-db` and then `make seed-rbac`.

## 6. Known caveats

- **Sidebar still gates on `User.role`.** The seed mirrors
  `Membership.role` to `User.role` so the legacy sidebar branches keep
  rendering. Once `Sidebar.jsx` migrates to capability-based gating,
  swap the user-role mirror in `seed_rbac_test_users.py` for capability
  checks.
- **Cross-org navigation in the SPA.** `VITE_DEV_ORGANIZATION_SLUG`
  hard-codes the org slug sent on every API call. Cross-tenant access
  is therefore validated at the API layer rather than via the SPA's
  routing — the `tbe_admin` user demonstrates the resulting 403s.
- **Render preview environments.** The seed command works on a
  preview's database too (one-off `python manage.py seed_rbac_test_users
  --reset` from the Render shell), but Google OAuth is unavailable on
  preview subdomains. Use the password sign-in only.

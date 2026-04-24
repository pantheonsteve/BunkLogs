# BunkLogs Development Guide

## Critical

**ALWAYS USE PODMAN COMMANDS** -- local dev runs in Podman containers. Never run `python manage.py` directly on the host.

Most common operations are wrapped in the `Makefile`. Run `make help` for the full list.

## Quick Start

```bash
make up                    # Start django + postgres + redis + mailpit
make frontend-dev          # In another terminal: start Vite on :5173
```

Verify:
- Backend health: http://localhost:8000/health/
- Django admin: http://localhost:8000/admin/
- Frontend: http://localhost:5173/
- Mailpit: http://localhost:8025/

## Architecture

- **Backend**: Django 5.0.13 + DRF, PostgreSQL 16, Redis 7, hosted on Render at `admin.bunklogs.net`
- **Frontend**: React 19 + Vite 6, hosted on Render (static site) at `clc.bunklogs.net`
- **Auth**: Django Allauth (headless) + JWT (SimpleJWT) + Google OAuth
- **Email**: Mailpit locally, Mailgun in production
- **Observability**: Datadog RUM (frontend) + APM (backend production)

Both Render services auto-deploy from `main` branch.

## Development Workflow

### Branching

- `main` is always deployable and matches production. Never push directly.
- Work on short-lived feature branches: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`.
- Open a PR for every change. Squash-merge into `main`.
- Delete feature branches after merge.

### CI and pre-commit

- `.github/workflows/ci.yml` runs pytest, ruff, and frontend tests/build on every PR.
- `.pre-commit-config.yaml` runs formatters and linters on staged files before each commit. Install once with:
  ```bash
  pip install pre-commit
  pre-commit install
  ```

### PR preview environments

`render.yaml` has `previews: generation: automatic` enabled. Opening a PR that touches backend code will spin up a preview backend on a Render subdomain (URL posted as a check on the PR). The preview gets its own Postgres on the free tier. Previews expire 7 days after the PR is closed/merged.

Limitation: Google OAuth won't work on preview URLs unless you add the preview subdomain pattern to the OAuth client's authorized redirect URIs (see "Google OAuth" below).

## Database Migration Safety

Render runs `migrate` on every deploy. Migrations that lock tables or fail mid-deploy can break production. Rules:

1. **Schema changes must be backwards-compatible with the previous code version.** The old code must keep running while the new migration is applied. This means:
   - New columns: nullable OR have a default
   - Renaming columns: do it in two PRs -- add new, backfill, point code at new, then drop old in a follow-up
   - Dropping columns: stop using in code first, ship that, then drop in a later PR
2. **Data migrations are separate from schema migrations.** Use `RunPython` with `reverse_code=migrations.RunPython.noop` and make them idempotent.
3. **Before merging a migration PR**, test it on the preview DB first. For larger changes, sync a recent prod snapshot locally with `make sync-prod-db` and run the migration against it.
4. **Long-running migrations** (>30s or involve large tables) should not run during deploy. Instead:
   - Ship the schema change as a no-op (e.g. add nullable column)
   - Backfill via a one-off Render job (`python manage.py <backfill_command>`)
   - Ship the final constraint/drop in a follow-up PR

## Rollback Procedure

**Code rollback (preferred for bad deploys):**
```bash
git revert <sha>
git push origin main
```
Render auto-deploys the revert within ~5 minutes.

**Emergency dashboard rollback (faster):**
1. Render dashboard -> `bunklogs-backend` -> Deploys
2. Click "Rollback" on the previous known-good deploy
3. Then still open a PR with `git revert` so `main` matches prod

**Database rollback:**
- Render Postgres has daily automated backups on paid plans. Restore via the Render dashboard.
- Before any migration with a non-trivial risk, run `make sync-prod-db` locally so you have a snapshot.

## Manual Setup Steps (one-time)

### Enable branch protection on `main`

In GitHub: repo Settings -> Branches -> "Add branch protection rule" for `main`:
- Require a pull request before merging
- Require status checks to pass before merging (select `Backend (pytest + ruff)` and `Frontend (vitest + build)` after CI has run at least once)
- Require branches to be up to date before merging
- Do not allow bypassing the above settings

### Google OAuth redirect URIs

In Google Cloud Console -> APIs & Services -> Credentials -> edit the OAuth 2.0 Client ID used by the app:

Authorized JavaScript origins should include:
- `http://localhost:5173`
- `https://clc.bunklogs.net`

Authorized redirect URIs should include:
- `http://localhost:8000/accounts/google/login/callback/`
- `https://admin.bunklogs.net/accounts/google/login/callback/`

Render preview subdomains are non-deterministic (e.g. `bunklogs-backend-pr-42.onrender.com`), and Google OAuth does not support wildcard subdomains on production-mode clients. Options:
- Test OAuth only locally or on production; use the preview env for everything else
- Create a separate OAuth client in "testing" mode that allows wildcard patterns, and wire it up conditionally via an env var on preview services

## Secrets and Environment

- `.envs/.local/.django`, `.envs/.local/.postgres`, `.envs/.production/.django`, and `frontend/.env` are gitignored. Copy from the matching `.example` files when setting up a new machine.
- **Production secrets** live only in the Render dashboard, never in the repo.
- **Rotation needed**: the git history prior to this cleanup contains old production secrets (Django `SECRET_KEY`, a Gmail app password, a Cloud SQL password). Those credentials look stale (GCP Cloud Run path no longer used) but should be rotated if they ever matched live services. The current Render-managed secrets are unaffected.

## Dependencies

- Backend deps are split across `backend/requirements/{base,local,production}.txt` and are fully pinned.
- Frontend deps are in `frontend/package.json`; versions are caret-ranged.

**Known audit issues** (run `npm audit` in `frontend/`):
- `vite` / `vitest` / `esbuild` / `@vitest/mocker`: moderate severity, dev-only. Fix requires upgrading to `vitest@4` which is a breaking change. Accept until we do a test infrastructure refresh.
- `quill` 2.0.3 -> 2.0.2: XSS via HTML export. Downgrade would be a regression on features; evaluate upstream fix or switch to a different rich text editor.

**Django 5.0.13 is end-of-life.** Plan a migration to Django 5.2 LTS.

**Cadence**: aim for one dependency PR per week during normal operations. Dependabot or Renovate can automate PR creation.

## Essential Commands

```bash
# Container lifecycle
make up                   # Start containers
make down                 # Stop containers
make restart              # Restart Django
make logs                 # Tail Django logs

# Django operations
make migrate              # Run pending migrations
make makemigrations       # Generate new migrations
make superuser            # Create superuser
make shell                # Django shell (shell_plus if available)

# Quality
make test                 # Backend + frontend tests
make lint                 # Backend lint
make test-backend         # Backend tests only
make test-frontend        # Frontend tests only

# Database
make sync-prod-db         # Sync local DB from production
make reset-db             # Drop volume, re-migrate
```

## Project Structure

```
BunkLogs/
├── backend/
│   ├── bunk_logs/          # Django apps (users, bunks, campers, bunklogs, orders, messaging, api, utils)
│   ├── config/             # Settings, urls, wsgi, auth
│   ├── compose/            # Dockerfiles (local, production, docs)
│   ├── requirements/       # base.txt, local.txt, production.txt
│   └── docker-compose.local.yml
├── frontend/
│   ├── src/
│   │   ├── auth/           # AuthContext (JWT)
│   │   ├── context/        # AllAuthContext (sessions)
│   │   ├── components/     # Reusable UI
│   │   ├── pages/          # Route targets
│   │   ├── lib/            # allauth client, integrations
│   │   └── api.js          # Axios client, JWT refresh, CSRF
│   └── vite.config.js
├── .github/workflows/
│   └── ci.yml              # PR tests + lint + build
├── .pre-commit-config.yaml
├── Makefile
├── render.yaml             # Backend + cron + redis + preview envs
└── sync-prod-db.sh         # Pull prod DB to local (keep out of git if it contains creds)
```

## Troubleshooting

**Port conflicts**: If `make up` fails with port-in-use errors, check for other projects using 5432/6379/8000:
```bash
lsof -i :5432 -i :6379 -i :8000
brew services list       # stop any system-level postgres
podman ps -a             # stop/remove old containers
```

**Django container restart loop**: Check `make logs`. Common causes are a broken migration, missing env var, or DB not accepting connections yet. Wait 10s after `make up` for postgres to be ready.

**ddtrace errors in local logs**: "failed to send traces to intake at localhost:8126" is harmless -- Datadog agent isn't running locally. Ignore.

**Cache not working in production health check**: Redis on Render may need re-provisioning. See `render.yaml` for the declared Redis service.

# Known Issues

Pre-existing issues documented here so they don't get re-flagged by automated tools or agents.
Last audited: 2026-04-28.

---

## Tests

### Backend (pytest)

**Status: all passing.** 109 tests across `bunk_logs/` pass cleanly.

Two deprecation warnings are present but do not fail any test:

- `dj_rest_auth` — `app_settings.USERNAME_REQUIRED` and `app_settings.EMAIL_REQUIRED` are deprecated in favor of `app_settings.SIGNUP_FIELDS[...]['required']`. Upstream issue in `dj-rest-auth`; fix by upgrading the package when a compatible version is released.
- `django.utils.html.format_html()` called without `args`/`kwargs` in `test_changelist` — `RemovedInDjango60Warning`. Will need to be addressed during the Django 5.x → 6.x upgrade.

### Frontend (Vitest)

**Status: all passing.** 4 tests in `src/App.test.jsx` pass cleanly.

Only one test file exists; test coverage is minimal. This is intentional at this stage of the project.

---

## Linters

### Backend (ruff)

**Status: `bunk_logs/` app code is clean.** All 242 ruff errors are in files outside the main application:

| File | Errors | Notes |
|------|--------|-------|
| `scripts/dev_admin.py` | 64 | Utility script moved from root; not part of app code |
| `scripts/example_test_data.py` | 58 | Seed data script; not part of app code |
| `scripts/fix_legacy_assignments.py` | 43 | One-off migration utility script |
| `scripts/update_api_views.py` | 39 | One-off transformation script |
| `scripts/update_views.py` | 32 | One-off transformation script |
| `config/migration_views.py` | 3 | New untracked view; S603/PLW1510/S607 subprocess warnings |
| `gunicorn.conf.py` | 3 | Q000 (single quotes) × 2, S108 (`/dev/shm` usage — intentional for performance) |

The `scripts/` files are utility/one-off scripts and are excluded from CI ruff checks. The `gunicorn.conf.py` `/dev/shm` warning (S108) is intentional — shared memory is used for gunicorn's worker heartbeat file.

### Frontend (ESLint)

**Status: not configured.** No `eslint.config.js` or `.eslintrc*` file exists in `frontend/`. `make lint-frontend` prints a stub message and exits cleanly.

This is a known gap. Adding ESLint was deferred because the frontend codebase is small and Vitest catches runtime errors. To add ESLint in the future:

```bash
cd frontend
npm init @eslint/config@latest
```

Then update `Makefile` target `lint-frontend` to run `npm run lint`.

---

## Dependencies

### npm audit (frontend)

Moderate-severity audit warnings accepted until further notice. See `CLAUDE.md → Dependencies` for the full list:

- `vite` / `vitest` / `esbuild` / `@vitest/mocker` — moderate, dev-only. Fix requires upgrading to `vitest@4` (breaking change).
- `quill` 2.0.3 — XSS via HTML export (production). Evaluate upstream fix or switch rich-text editor.

Run `npm audit` in `frontend/` for the current full list.

### Django version

Django 5.0.13 is end-of-life. Plan a migration to Django 5.2 LTS. Tracked in `CLAUDE.md → Dependencies`.

---

## Other

### `config/migration_views.py` (untracked)

A new file `backend/config/migration_views.py` is present but not yet committed. It contains a migration dashboard view. This is work-in-progress for the multi-tenant migration (see `migration_prompts/`).

### `frontend/src/pages/MigrationDashboard.jsx` (untracked)

Companion frontend page for the migration dashboard. Also work-in-progress, not yet committed.

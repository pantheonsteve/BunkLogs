# CLC Summer 2026 — Launch Runbook

Target launch: **Saturday, June 5, 2026** (staff orientation weekend).

---

## Pre-launch checklist (complete by June 3)

### Infrastructure
- [ ] Production Render service (`bunklogs-backend`) is on the latest `main` commit
- [ ] **Scale web to 2 instances** in Render dashboard before camp opens (handles end-of-day submission burst)
- [ ] Celery worker (`bunklogs-celery`) is running and connected to Redis
- [ ] `WEB_CONCURRENCY=3` on the backend web service (see `render.yaml`)
- [ ] All migrations applied cleanly — confirm via Render deploy logs, no migration errors
- [ ] `GET https://admin.bunklogs.net/health/` returns `{"status":"healthy"}`
- [ ] Redis and Postgres shown as `ok` in health check
- [ ] Mailgun production API key active; send a test email from Django admin

### Data
- [ ] `make onboard-clc` (templates only) has been run on staging and verified — see verification report
- [ ] Final Campminder CSV export received from Alyson with all summer 2026 staff
- [ ] CSV dry-run on staging passes with 0 warnings: `make onboard-clc CSV_PATH=<file> DRY_RUN=1`
- [ ] Campminder CSV imported on staging; spot-check 5 staff records in admin → Person list
- [ ] All 11 reflection templates visible and active in admin → Reflection templates (filter by org=clc)
- [ ] At least one test reflection submitted end-to-end on staging using a counselor account

### Auth
- [ ] Google OAuth redirect URIs include `https://admin.bunklogs.net/accounts/google/login/callback/`
- [ ] Test Google sign-in on staging with a `@urjcamps.org` account
- [ ] Password reset email arrives at a test address within 60 s

### Frontend
- [ ] `https://clc.bunklogs.net` loads the React app with no console errors
- [ ] `/reflect` redirects to sign-in for unauthenticated users
- [ ] After sign-in, counselors land on `/counselor-dashboard`
- [ ] **Submission reliability QA** (staging, before prod):
  - [ ] **Offline test:** submit a camper reflection with DevTools offline → row shows **Syncing…** on roster → go online → row confirms on server
  - [ ] **Draft test:** fill half a self-reflection → refresh → draft restores with same content
  - [ ] **Ambiguous failure:** throttle network to drop response after server saves → retry → single DB row (check admin)
  - [ ] **Burst smoke test:** run `python scripts/eod_submission_load_smoke.py` against staging with a counselor JWT — expect PASS, 0 HTTP 500

---

## Day-of steps (June 5)

Run these in order. Each step is idempotent — safe to repeat on failure.

### 1. Apply final migrations (if any pending)
Render auto-migrates on deploy. Confirm no pending migrations:
```bash
# In Render shell or via one-off job:
python manage.py showmigrations | grep "\[ \]"
# Expected: no output (all applied)
```

### 2. Run full onboarding with final CSV
```bash
# From the Render dashboard → one-off job, or via local container pointing at prod DB:
python manage.py onboard_clc_summer_2026 \
  --csv-path /path/to/clc_summer_2026_staff.csv

# Or using make (local, pointed at prod via DATABASE_URL):
make onboard-clc CSV_PATH=/path/to/clc_summer_2026_staff.csv
```

Expected output ends with:
```
✓  Organization              1 / 1 expected  (clc)
✓  Program                   1 / 1 expected  (summer-2026)
✓  Active templates          11 / 11 expected
✓  Persons                   <n>
✓  Active memberships        <n>

All checks passed. CLC Summer 2026 is ready.
```

### 3. Spot-check in Django admin
1. `https://admin.bunklogs.net/admin/core/person/` — confirm person count matches CSV
2. `https://admin.bunklogs.net/admin/core/membership/` — confirm all memberships active
3. `https://admin.bunklogs.net/admin/core/reflectiontemplate/` — confirm 11 active templates for `clc`

### 4. Send staff the sign-in link
Distribute `https://clc.bunklogs.net/signin` to staff.
First-time users without a Google account will use email + password reset.

### 5. Confirm first reflections are submitting
By end of Day 1 (June 5 evening), at least a handful of counselors should have submitted.
Check: `https://admin.bunklogs.net/admin/core/reflection/` — filter by program=summer-2026.

---

## Rollback plan

### Code rollback
```bash
git revert HEAD
git push origin main
```
Render auto-deploys in ~5 min. Migrations are not reversed by a code revert — see DB rollback below if needed.

### Data rollback (if onboarding imported bad data)
The import is additive and keyed by `campminder_id`. To undo a bad import:
```bash
# In Django shell (Render one-off job):
from bunk_logs.core.models import Organization, Person, Membership
org = Organization.objects.get(slug="clc")
# Inspect before deleting:
Person.all_objects.filter(organization=org).count()
# If confirmed bad, delete memberships first, then persons:
Membership.all_objects.filter(program__organization=org).delete()
Person.all_objects.filter(organization=org).delete()
```
Then re-run `onboard_clc_summer_2026` with the corrected CSV.

### Database rollback (nuclear option)
Render Postgres has daily automated backups (paid plan). In the Render dashboard:
Postgres service → Backups → restore to a snapshot taken before the problematic deploy.
**Warning:** this rolls back ALL data including any reflections submitted since the snapshot.

---

## Monitoring — first 48 hours (June 5–7)

### What to watch
| Signal | Where | Alert threshold |
|---|---|---|
| 5xx error rate | Render metrics → web service | > 1% of requests |
| P95 response time | Render metrics | > 2 s sustained |
| Failed reflection submissions | Django admin → Reflection list, filter `is_complete=False` | unexpected spike |
| Celery task failures | Render logs → worker service | any ERROR log |
| Email delivery | Mailgun dashboard | bounce rate > 5% |

### Useful queries (Django shell)
```python
from bunk_logs.core.models import Reflection, Organization
org = Organization.objects.get(slug="clc")
# Submissions today:
from django.utils import timezone
today = timezone.localdate()
Reflection.objects.filter(program__organization=org, period_end=today).count()

# Incomplete (saved draft but not submitted):
Reflection.objects.filter(program__organization=org, is_complete=False).count()
```

### Key contacts
- **Technical issues:** Steve Bresnick
- **Staff access / login help:** Alyson (program director)
- **Template content feedback:** Brent (director)

---

## Running the onboarding command

```bash
# Templates only (no CSV):
make onboard-clc

# With staff CSV:
make onboard-clc CSV_PATH=/path/to/staff.csv

# Dry-run validation (no DB writes):
make onboard-clc CSV_PATH=/path/to/staff.csv DRY_RUN=1

# Or directly in the container:
podman-compose -f backend/docker-compose.local.yml exec django \
  python manage.py onboard_clc_summer_2026 \
  --csv-path /path/to/staff.csv [--dry-run]
```

### CSV format expected by `import_campminder_staff`

| Column | Required | Notes |
|---|---|---|
| `campminder_id` | Yes | Stable Campminder person ID; used as dedup key |
| `first_name` | Yes | |
| `last_name` | Yes | |
| `email` | No | Used for account matching |
| `role` | Yes | Must match a valid Membership role code (e.g. `counselor`) |
| `language_preference` | No | `en` or `es`; stored in membership metadata |
| `tags` | No | Comma-separated; stored on membership |

Valid role codes: `counselor`, `junior_counselor`, `specialist`, `general_counselor`,
`leadership_team`, `kitchen_staff`, `maintenance`, `housekeeping`, `camper_care`,
`health_center`, `special_diets`, `admin`, `faculty`.

---

## Seeding TemplateAssignments (Step 7_22)

The per-role dashboards refactored in Step 7_21 read from
`TemplateAssignment` rows. Without those rows, every dashboard returns
empty. The `seed_summer_2026_assignments` management command writes the
12 rows Crane Lake needs.

**Prerequisites:** `onboard_clc_summer_2026` must have run first so the
org, program, and all 12 templates exist.

### Command

```bash
python manage.py seed_summer_2026_assignments \
    --org-slug clc \
    --program-slug summer-2026 \
    [--actor-username <admin-or-LT-email>] \
    [--dry-run]
```

- `--dry-run` reports the plan and writes nothing.
- `--actor-username` is optional; when supplied, it must be the email of
  a user with an active `admin` or `leadership_team` Membership in the
  target org. Their Membership is stamped onto `created_by`.

### What it creates

12 `TemplateAssignment` rows — one per CLC 2026 template, all
`target_type='role'`, `is_required=True`, `status='scheduled'`,
`cadence_override=None` (so each template's own cadence applies —
biweekly for Leadership Team, daily for the rest). Dates flow from the
Program record.

| Role | Template slug | Title |
|---|---|---|
| counselor | `clc-2026-counselor-daily` | Counselor daily bunk log |
| junior_counselor | `clc-2026-junior-counselor-daily` | Junior counselor daily reflection |
| general_counselor | `clc-2026-general-counselor-daily` | General counselor daily reflection |
| specialist | `clc-2026-specialist-daily` | Specialist daily reflection |
| unit_head | `clc-2026-unit-head-daily` | Unit head daily reflection |
| leadership_team | `clc-2026-leadership-biweekly` | Leadership team check-in (biweekly) |
| kitchen_staff | `clc-2026-kitchen-daily` | Kitchen staff daily reflection |
| maintenance | `clc-2026-maintenance-daily` | Maintenance daily reflection |
| housekeeping | `clc-2026-housekeeping-daily` | Housekeeping daily reflection |
| camper_care | `clc-2026-camper-care-daily` | Camper care daily reflection |
| health_center | `clc-2026-health-center-daily` | Health center daily reflection |
| special_diets | `clc-2026-special-diets-daily` | Special diets daily reflection |

There is no `admin` row — admin's surface is template oversight, not a
templated reflection.

### Idempotency contract

Keyed on `(program, template, target_type='role', target_payload['role'])`
restricted to `status IN ('scheduled', 'active')`.

- Re-running with the same args reconciles `title` / `is_required` on the
  matched row and never creates duplicates.
- If only `ended` / `cancelled` rows exist for the key, the command logs
  a warning and creates a fresh `scheduled` row alongside (does NOT
  resurrect the old row).
- The command refuses to run (`CommandError`) if any of the 12 templates
  is missing — fix that by re-running `onboard_clc_summer_2026` first.

### Verification on staging

1. `python manage.py seed_summer_2026_assignments --org-slug clc --program-slug summer-2026`
2. Confirm count:
   ```bash
   python manage.py shell -c "from bunk_logs.core.models import TemplateAssignment, Program; \
     p = Program.all_objects.get(slug='summer-2026'); \
     print(TemplateAssignment.all_objects.filter(program=p).count())"
   ```
   Expected: `12`.
3. Log in as Alyson (or any LT user) and load each per-role dashboard:
   counselor, junior counselor, general counselor, specialist, unit head,
   leadership team, kitchen staff, maintenance, housekeeping, camper
   care, health center, special diets. Each should show its resolved
   template (no empty-state).

### Final Wave 1 production deploy sequence

Per `docs/wave_1_progress.md`, the cutover is:

1. Deploy `7_20` + `7_21` + `7_22` together in one maintenance window
   (suggested: evening of June 1 or 2).
2. After deploy completes, run the seeding command on the production
   backend (via Render shell):
   ```bash
   python manage.py seed_summer_2026_assignments \
     --org-slug clc --program-slug summer-2026 \
     --actor-username <alyson@clc.email>
   ```
3. Smoke-test as Alyson immediately.
4. Watch Datadog APM for 24h for unexpected dashboard errors.

### Rollback

Forward fixes are preferred. If the seeded rows are wrong:

- Mark the bad rows `status='cancelled'`, then re-run the seeder (it
  creates fresh `scheduled` rows alongside).
- Or revert `7_21` + `7_22` as a pair — the old hard-coded dashboards
  return as a backstop.

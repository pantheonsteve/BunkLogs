# Local Development Data

How to get realistic data into your local BunkLogs database without leaking
production PII onto a developer laptop.

## TL;DR

- **Everyday work**: `./backend/dev.sh seed-dev` -- synthetic Faker data, no
  prod credentials needed. (Phase 2: a richer `seed_dev_data` command;
  currently falls back to `create_sample_test_data`.)
- **Occasional realism check**: `./backend/dev.sh sync-prod` -- pulls
  production, restores locally, then **immediately** scrubs PII via
  `python manage.py scrub_pii --confirm`.

## Why we anonymize before data hits your laptop

BunkLogs holds PII for minors (camper names, DOB, parent contact info).
Under **COPPA** in the US -- and **GDPR** if any EU campers ever appear --
the test we want to be able to pass is:

> Production PII never leaves the production boundary in unscrubbed form.

The hybrid workflow makes that the default:

```text
Prod Postgres ─pg_dump─> local Postgres ─scrub_pii─> usable dev DB
                          (raw, ~seconds)
```

The raw dump exists on disk for the duration of the restore + scrub
(typically under a minute) and is then deleted. For solo dev with an
encrypted laptop this is acceptable; when you grow the team, see
[Phase 3 below](#phase-3--server-side-scrub-when-the-team-grows).

## One-time setup

### 1. Create a read-only Postgres role on production

Run this **once**, against your Render Postgres, as a user that owns the
schema (e.g. via the Render web shell or `psql` from your laptop):

```sql
-- Replace CHANGEME with a strong, unique password.
CREATE ROLE bunklogs_readonly WITH LOGIN PASSWORD 'CHANGEME';

GRANT CONNECT ON DATABASE bunk_logs TO bunklogs_readonly;
GRANT USAGE   ON SCHEMA public TO bunklogs_readonly;
GRANT SELECT  ON ALL TABLES IN SCHEMA public TO bunklogs_readonly;

-- Make sure future tables are also readable.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO bunklogs_readonly;
```

Why a dedicated role:

- The principle of least privilege -- this credential lives on dev
  laptops and in `.env` files, so it must not be able to write or drop.
- Rotation: revoking just this role won't break the app.
- Auditability: `pg_stat_activity` lets you see exactly when a dev pulled
  a dump.

### 2. Install the local PostgreSQL client tools

The sync script runs `pg_dump` on your **host** (not in podman), and the
production server is **PostgreSQL 16**, so your client must be version 16+:

```bash
# macOS
brew install postgresql@16
# NOTE: Do NOT just `brew install postgresql` -- it may give you pg14/pg15
# which will fail with "server version mismatch". The sync script
# automatically puts the pg16 bin dir first in PATH.

# Debian/Ubuntu
sudo apt-get install postgresql-client-16
```

### 3. Configure the local credential file

```bash
cp backend/.envs/.local/.prod-readonly.example \
   backend/.envs/.local/.prod-readonly
```

Edit the new file and fill in `PROD_READONLY_DATABASE_URL` with the
Render external connection string for the `bunklogs_readonly` role.
The file is gitignored.

## Daily workflow

### Pull + scrub a fresh prod copy

```bash
./backend/dev.sh sync-prod
```

What happens, in order:

1. `pg_dump` (read-only role) -> `/tmp/bunk_logs_prod_<ts>.sql`
2. drop + recreate the local `bunk_logs` DB inside the podman postgres
   container
3. `psql -f` the dump into the local DB
4. `python manage.py migrate` (in the django container) -- in case your
   branch has migrations production hasn't seen yet
5. `python manage.py scrub_pii --confirm` -- replaces PII with Faker
   values; resets every non-superuser password to `devpass123`
6. raw dump removed from host and from the container's `/tmp`

Useful flags (forward via `ARGS=` or `./scripts/sync-prod-db.sh`):

```bash
make sync-prod-db ARGS="--keep-superuser-emails"   # scrub, but keep superuser emails
./scripts/sync-prod-db.sh --keep-dump              # keep the .dump for debugging
./scripts/sync-prod-db.sh --no-scrub              # raw prod copy (real emails/passwords; type 'unscrubbed' to confirm)
```

### Raw prod copy (troubleshooting only)

By default every sync runs `scrub_pii`, which replaces user emails with
`user{id}@example.test` and resets passwords to `devpass123`. To debug
issues that depend on real identities (email delivery, specific user
accounts, OAuth linkage), pull an **unscrubbed** copy:

```bash
make sync-prod-db ARGS="--no-scrub"
# or: ./backend/dev.sh sync-prod --no-scrub
```

You will be prompted to type `unscrubbed`. Sign in with each user's
**production password** (hashes are copied verbatim). When finished,
either re-sync without `--no-scrub` or run `./backend/dev.sh scrub-pii`
to anonymize the current local DB.

### Re-scrub the current local DB

If you skipped the scrub, or want to re-scrub after manually loading more
data:

```bash
./backend/dev.sh scrub-pii
```

### Generate synthetic data instead (no prod access)

```bash
./backend/dev.sh seed-dev
```

Phase 1 ships this as a thin wrapper that falls back to the existing
`create_sample_test_data` command. Phase 2 will replace it with a much
richer `seed_dev_data` command (2 sessions, 4 units, ~120 campers, 30
days of logs, sample orders).

## What `scrub_pii` actually does

Field-by-field. See
[`backend/bunk_logs/utils/management/commands/scrub_pii.py`](../backend/bunk_logs/utils/management/commands/scrub_pii.py)
for the source.

| Model / table                     | Action                                                                 |
| --------------------------------- | ---------------------------------------------------------------------- |
| `users.User`                      | `email` → `user{pk}@example.test`, names → Faker, password → `devpass123`, `last_login` → null |
| `core.Person`                     | names → Faker, DOB → same year/month + random day, `email` → `user{user_id}@example.test` or `person{pk}@example.test`, `notes` → `[scrubbed]` |
| `campers.Camper`                  | names → Faker, DOB → same year/month, random day; emergency contact → Faker; all `*_notes` / `status_note` → `[scrubbed]` |
| `bunks.Cabin`                     | `location`, `notes` → blank / `[scrubbed]` (capacity preserved)         |
| `bunklogs.BunkLog`                | `description` → `[scrubbed]` (scores preserved so the UI looks real)   |
| `bunklogs.StaffLog`               | `elaboration`, `values_reflection` → `[scrubbed]` (scores preserved for all staff roles) |
| `orders.Order` (legacy)           | `additional_notes`, `narrative_description` → `[scrubbed]`             |
| `notes.Observation`               | `body` → `[scrubbed]`                                                  |
| `notes.ObservationReply`          | `body` → `[scrubbed]`                                                  |
| `core.Reflection`                 | string values inside `answers` JSON → `[scrubbed]` (structure preserved) |
| `core.Order` (camper care)        | `item_note`, `description` → `[scrubbed]`                              |
| `core.MaintenanceTicket`          | `description`, `urgent_reason` → `[scrubbed]`                          |
| `core.CamperDayState`             | `reason` → `[scrubbed]`                                                |
| `core.OrderActivityEvent`         | `note`, `reason` → `[scrubbed]`                                        |
| `core.AuditEvent`                 | `reason_note` → `[scrubbed]`; `before_state` / `after_state` / `metadata` cleared via raw SQL (append-only model) |
| `core.TranslationRecord`          | `translated_text`, `last_error` → `[scrubbed]`                         |
| `messaging.EmailRecipient`        | `email`, `name` → Faker                                                 |
| `messaging.EmailLog`              | TRUNCATE                                                                |
| `django_session`                  | TRUNCATE                                                                |
| `authtoken_token`                 | TRUNCATE                                                                |
| `token_blacklist_outstandingtoken` | TRUNCATE CASCADE                                                       |
| `token_blacklist_blacklistedtoken` | TRUNCATE                                                                |
| `socialaccount_socialtoken`       | TRUNCATE                                                                |
| `socialaccount_socialaccount`     | TRUNCATE                                                                |
| `account_emailaddress`            | UPDATE to mirror scrubbed user emails                                   |

Hard guardrails inside the command:

- Refuses to run if `settings.DEBUG` is False.
- Refuses to run if the active DB host is not in
  `{localhost, 127.0.0.1, ::1, postgres, ""}`.
- Without `--confirm` it's a no-op (only runs the safety checks).

## Compliance notes (so future-you doesn't have to reverse-engineer this)

- **No prod credential ever has DROP/INSERT/UPDATE rights** -- the
  `bunklogs_readonly` role is `SELECT` only.
- **Default-deny on dump retention** -- `sync-prod-db.sh` deletes the
  raw dump unless you pass `--keep-dump`. The container copy is also
  removed.
- **Single, well-known dev password** post-scrub. Don't reuse it
  anywhere else; it exists to make local sign-in trivial after a sync.
- **`is_test_data` flag** on every relevant model lets you bulk-purge
  records you created locally without touching scrubbed prod records --
  see `cleanup_test_data` and `delete_all_test_data` in
  [`backend/bunk_logs/utils/models.py`](../backend/bunk_logs/utils/models.py).

## Phase 3 -- Server-side scrub (when the team grows)

The remaining risk in the current design is the brief window where the
raw `pg_dump` lives on the developer's host before scrubbing. Once a
second engineer joins, eliminate that window by moving the scrub
upstream:

1. Render one-off job (or scheduled job) does:
   ```text
   pg_dump prod
     -> restore into a throwaway DB
     -> python manage.py scrub_pii --confirm
     -> pg_dump that scrubbed DB
     -> upload to gs://bunklogs-dev-snapshots/YYYY-MM-DD.sql.gz
   ```
2. Devs run a shorter `pull-dev-snapshot.sh` that only ever sees the
   pre-scrubbed artifact.
3. The raw dump never leaves Render.

## Troubleshooting

- **`pg_dump: error: connection failed`** -- verify the read-only role
  was created and that Render's external connections are allowed for
  your IP. The Render dashboard shows the external host in the DB
  page.
- **`SSL connection has been closed unexpectedly` during COPY** -- the
  sync script uses compressed custom-format dumps, TCP keepalives, and
  automatic retries. If it still fails, wait a minute and rerun; check
  your network/VPN isn't dropping long-lived connections.
- **`scrub_pii` aborts with "DB host not in local allowlist"** -- you
  ran the command outside the podman django container, or `DATABASE_URL`
  in your `.django` env points somewhere unexpected. Always invoke via
  `make sync-prod-db` or `./scripts/sync-prod-db.sh`.
- **Observations / reflections missing after sync** -- the dump is full-database;
  if counts are zero, production likely has no rows yet. After a successful
  sync, the script prints post-scrub counts for `persons`, `observations`,
  and `reflections`. Re-grant `SELECT` on new tables to `bunklogs_readonly` if
  `pg_dump` fails after a schema migration (see [One-time setup](#one-time-setup)).
- **Local sign-in fails after scrub** -- scrubbed syncs reset all passwords
  to `devpass123` and replace non-superuser emails with
  `user{id}@example.test`. For real emails/passwords, re-sync with
  `--no-scrub` (troubleshooting only). Superusers keep their email when
  you pass `--keep-superuser-emails` during a scrubbed sync.
- **OAuth (Google) sign-in fails after scrub** -- expected:
  `socialaccount_socialaccount` is truncated. Either re-link via the
  signup flow, or sign in with email + `devpass123`.

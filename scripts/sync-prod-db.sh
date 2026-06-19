#!/usr/bin/env bash
#
# sync-prod-db.sh -- Pull a production Postgres dump, restore it into the
# local podman Postgres, then immediately scrub PII via the Django command.
#
# Pipeline:
#   1. pg_dump (read-only role)  ->  /tmp/<dump>.dump on host (custom format)
#   2. drop + recreate the local DB inside the podman postgres container
#   3. pg_restore <dump>         ->  local DB
#   4. python manage.py migrate  (in the django container)
#   5. python manage.py scrub_pii --confirm  (skipped with --no-scrub)
#
# Safety rails:
#   - Refuses to run unless PROD_READONLY_DATABASE_URL is set (sourced from
#     backend/.envs/.local/.prod-readonly, which is gitignored).
#   - Refuses if the prod URL host doesn't look like a remote host
#     (prevents pointing both ends at the same DB by accident).
#   - The local restore target is hard-coded; you cannot point this script
#     at a remote DB.
#   - Scrub step runs by default. Pass --no-scrub for a raw prod copy (PII
#     intact); requires typing 'unscrubbed' to confirm.
#
# Usage:
#   ./scripts/sync-prod-db.sh
#   ./scripts/sync-prod-db.sh --keep-dump
#   ./scripts/sync-prod-db.sh --keep-superuser-emails
#   ./scripts/sync-prod-db.sh --no-scrub   # full prod PII for troubleshooting
#

set -euo pipefail

# --- locations -------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
ENV_FILE="${BACKEND_DIR}/.envs/.local/.prod-readonly"
COMPOSE_FILE="${BACKEND_DIR}/docker-compose.local.yml"
LOCAL_DB_NAME="${LOCAL_DB_NAME:-bunk_logs}"
LOCAL_PG_USER="${LOCAL_PG_USER:-postgres}"
PG_CONTAINER="${PG_CONTAINER:-bunk_logs_local_postgres}"
DJANGO_CONTAINER="${DJANGO_CONTAINER:-bunk_logs_local_django}"

# --- args ------------------------------------------------------------------

KEEP_DUMP=0
NO_SCRUB=0
SCRUB_EXTRA_ARGS=()
for arg in "$@"; do
    case "$arg" in
        --keep-dump)
            KEEP_DUMP=1
            ;;
        --keep-superuser-emails)
            SCRUB_EXTRA_ARGS+=("--keep-superuser-emails")
            ;;
        --no-scrub)
            NO_SCRUB=1
            ;;
        -h|--help)
            sed -n '2,35p' "$0"
            exit 0
            ;;
        *)
            echo "unknown arg: $arg" >&2
            exit 2
            ;;
    esac
done

# --- helpers ---------------------------------------------------------------

red()    { printf "\033[0;31m%s\033[0m\n" "$*"; }
green()  { printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[1;33m%s\033[0m\n" "$*"; }
blue()   { printf "\033[0;34m%s\033[0m\n" "$*"; }

die() { red "[fatal] $*" >&2; exit 1; }
info() { blue "[sync-prod-db] $*"; }
ok() { green "[sync-prod-db] $*"; }
warn() { yellow "[sync-prod-db] $*"; }

compose_cmd() {
    if command -v podman-compose >/dev/null 2>&1; then
        echo "podman-compose"
    elif command -v podman >/dev/null 2>&1; then
        echo "podman compose"
    else
        die "podman / podman-compose not found"
    fi
}

# Render (and other remote hosts) may drop idle SSL sessions during long COPY
# streams. libpq keepalive params help; custom-format dumps compress payload.
prod_url_with_keepalives() {
    local url="$1"
    case "$url" in
        *keepalives=*)
            printf '%s' "$url"
            ;;
        *\?*)
            printf '%s&keepalives=1&keepalives_idle=30&keepalives_interval=10&keepalives_count=5' "$url"
            ;;
        *)
            printf '%s?keepalives=1&keepalives_idle=30&keepalives_interval=10&keepalives_count=5' "$url"
            ;;
    esac
}

# --- preflight -------------------------------------------------------------

[[ -f "$ENV_FILE" ]] || die "missing ${ENV_FILE}. Copy .prod-readonly.example and fill it in."
# shellcheck source=/dev/null
set -a; source "$ENV_FILE"; set +a

[[ -n "${PROD_READONLY_DATABASE_URL:-}" ]] \
    || die "PROD_READONLY_DATABASE_URL not set in ${ENV_FILE}"

# Sanity check: the prod URL must NOT point at localhost / podman service.
prod_host=$(printf '%s' "$PROD_READONLY_DATABASE_URL" \
    | sed -E 's|^[^@]+@([^:/]+).*|\1|')
case "$prod_host" in
    localhost|127.0.0.1|::1|postgres|"$PG_CONTAINER")
        die "PROD_READONLY_DATABASE_URL points at a local host ('$prod_host'). Aborting."
        ;;
esac
info "prod host: $prod_host"
info "local target: container=$PG_CONTAINER db=$LOCAL_DB_NAME user=$LOCAL_PG_USER"

if [[ "$NO_SCRUB" -eq 1 ]]; then
    warn "RAW SYNC: scrub_pii will be SKIPPED. Real emails, names, and prod passwords will remain."
    warn "Only use on an encrypted machine. Re-run without --no-scrub when done troubleshooting."
    printf "Type 'unscrubbed' to continue: "
    read -r no_scrub_confirm
    [[ "$no_scrub_confirm" == "unscrubbed" ]] \
        || die "cancelled (--no-scrub requires typing 'unscrubbed')"
fi

# Prefer the pg16 client (production server is pg16; pg_dump must be >= server).
for pg_dir in \
    /opt/homebrew/opt/postgresql@16/bin \
    /usr/lib/postgresql/16/bin \
    /usr/local/opt/postgresql@16/bin; do
    if [[ -x "${pg_dir}/pg_dump" ]]; then
        export PATH="${pg_dir}:${PATH}"
        break
    fi
done
command -v pg_dump >/dev/null 2>&1 \
    || die "pg_dump not found on host. Install PostgreSQL client (e.g. 'brew install postgresql@16')."
pg_dump_ver=$(pg_dump --version | awk '{print $3}' | cut -d. -f1)
[[ "$pg_dump_ver" -ge 16 ]] \
    || die "pg_dump version ${pg_dump_ver} is too old (need >=16 for a pg16 server). Run: brew install postgresql@16"
command -v podman >/dev/null 2>&1 || die "podman not found"

CMP="$(compose_cmd)"

# --- ensure containers up --------------------------------------------------

info "ensuring postgres and django containers are running..."
pg_running=$(podman inspect -f '{{.State.Running}}' "$PG_CONTAINER" 2>/dev/null || echo "false")
dj_running=$(podman inspect -f '{{.State.Running}}' "$DJANGO_CONTAINER" 2>/dev/null || echo "false")
if [[ "$pg_running" != "true" || "$dj_running" != "true" ]]; then
    ( cd "$BACKEND_DIR" && $CMP -f docker-compose.local.yml up -d postgres django >/dev/null )
else
    info "containers already running, skipping 'up'"
fi

# wait for postgres
attempts=0
until $CMP -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "$LOCAL_PG_USER" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    [[ $attempts -gt 30 ]] && die "timeout waiting for local postgres"
    sleep 1
done
ok "local postgres ready"

# --- dump prod -------------------------------------------------------------

ts="$(date +%Y%m%d_%H%M%S)"
dump_file="/tmp/bunk_logs_prod_${ts}.dump"
prod_url="$(prod_url_with_keepalives "$PROD_READONLY_DATABASE_URL")"
max_dump_attempts=3
dump_attempt=1

while true; do
    info "dumping prod -> ${dump_file} (attempt ${dump_attempt}/${max_dump_attempts})"
    # Custom format + compression is smaller over the wire and more reliable
    # than plain SQL for large JSON-heavy tables (e.g. core_reflection).
    if pg_dump \
        --no-owner --no-privileges \
        --format=custom --compress=6 \
        --file="$dump_file" \
        "$prod_url"; then
        break
    fi
    rm -f "$dump_file"
    if [[ "$dump_attempt" -ge "$max_dump_attempts" ]]; then
        die "pg_dump failed after ${max_dump_attempts} attempts (SSL timeout on large tables is common -- retry, or check Render IP allowlist)"
    fi
    warn "pg_dump failed; retrying in 15s..."
    dump_attempt=$((dump_attempt + 1))
    sleep 15
done

size=$(du -h "$dump_file" | awk '{print $1}')
ok "dump complete (${size})"

# --- recreate local DB -----------------------------------------------------

info "terminating active connections to ${LOCAL_DB_NAME}..."
$CMP -f "$COMPOSE_FILE" exec -T postgres psql -U "$LOCAL_PG_USER" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${LOCAL_DB_NAME}' AND pid <> pg_backend_pid();" \
    >/dev/null

info "dropping and recreating ${LOCAL_DB_NAME}..."
$CMP -f "$COMPOSE_FILE" exec -T postgres dropdb -U "$LOCAL_PG_USER" --if-exists "$LOCAL_DB_NAME"
$CMP -f "$COMPOSE_FILE" exec -T postgres createdb -U "$LOCAL_PG_USER" "$LOCAL_DB_NAME"

info "copying dump into postgres container..."
podman cp "$dump_file" "${PG_CONTAINER}:/tmp/restore.dump"

info "restoring into local DB..."
$CMP -f "$COMPOSE_FILE" exec -T postgres pg_restore \
    --no-owner --no-privileges \
    --dbname="$LOCAL_DB_NAME" \
    --username="$LOCAL_PG_USER" \
    /tmp/restore.dump

ok "restore complete"

# --- migrate + scrub -------------------------------------------------------

info "running 'manage.py migrate' (handles any branch-vs-prod schema drift)..."
$CMP -f "$COMPOSE_FILE" exec -T django python manage.py migrate --noinput

if [[ "$NO_SCRUB" -eq 1 ]]; then
    warn "Skipping scrub_pii: local DB contains UNSCRUBBED production PII."
    warn "Use production passwords to sign in. Delete the dump/DB when done troubleshooting."
else
    info "running 'manage.py scrub_pii --confirm'..."
    # Guard the array expansion: under `set -u`, an empty array triggers an
    # "unbound variable" error on bash 3.2 (macOS default). The `+` form
    # expands to nothing when the array is empty.
    $CMP -f "$COMPOSE_FILE" exec -T django \
        python manage.py scrub_pii --confirm "${SCRUB_EXTRA_ARGS[@]+"${SCRUB_EXTRA_ARGS[@]}"}"
fi

info "post-sync row counts:"
$CMP -f "$COMPOSE_FILE" exec -T django python manage.py shell -c "
from bunk_logs.core.models import Person, Reflection
from bunk_logs.notes.models import Observation
from bunk_logs.users.models import User
print(f'  users={User.objects.count()}')
print(f'  persons={Person.all_objects.count()}')
print(f'  observations={Observation.all_objects.count()}')
print(f'  reflections={Reflection.all_objects.count()}')
"

# --- cleanup ---------------------------------------------------------------

if [[ "$KEEP_DUMP" -eq 1 ]]; then
    warn "leaving raw dump on disk: ${dump_file}"
    warn "this file contains UNSCRUBBED production PII -- delete it when done."
else
    rm -f "$dump_file"
    $CMP -f "$COMPOSE_FILE" exec -T postgres rm -f /tmp/restore.dump
    ok "raw dump removed from host and container"
fi

if [[ "$NO_SCRUB" -eq 1 ]]; then
    ok "done. Local DB '${LOCAL_DB_NAME}' contains UNSCRUBBED production data."
else
    ok "done. Local DB '${LOCAL_DB_NAME}' contains scrubbed production data."
fi

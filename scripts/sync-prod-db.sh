#!/usr/bin/env bash
#
# sync-prod-db.sh -- Pull a production Postgres dump, restore it into the
# local podman Postgres, then immediately scrub PII via the Django command.
#
# Pipeline:
#   1. pg_dump (read-only role)  ->  /tmp/<dump>.sql on host
#   2. drop + recreate the local DB inside the podman postgres container
#   3. psql -f <dump>            ->  local DB
#   4. python manage.py migrate  (in the django container)
#   5. python manage.py scrub_pii --confirm  (in the django container)
#
# Safety rails:
#   - Refuses to run unless PROD_READONLY_DATABASE_URL is set (sourced from
#     backend/.envs/.local/.prod-readonly, which is gitignored).
#   - Refuses if the prod URL host doesn't look like a remote host
#     (prevents pointing both ends at the same DB by accident).
#   - The local restore target is hard-coded; you cannot point this script
#     at a remote DB.
#   - Scrub step is mandatory. If it fails, the script exits non-zero and
#     leaves you in a known-bad state (loud, not silent).
#
# Usage:
#   ./scripts/sync-prod-db.sh
#   ./scripts/sync-prod-db.sh --keep-dump      # don't delete the .sql file
#   ./scripts/sync-prod-db.sh --keep-superuser-emails
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
SCRUB_EXTRA_ARGS=()
for arg in "$@"; do
    case "$arg" in
        --keep-dump)
            KEEP_DUMP=1
            ;;
        --keep-superuser-emails)
            SCRUB_EXTRA_ARGS+=("--keep-superuser-emails")
            ;;
        -h|--help)
            sed -n '2,30p' "$0"
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
dump_file="/tmp/bunk_logs_prod_${ts}.sql"
info "dumping prod -> ${dump_file}"
# --no-owner / --no-privileges keep the dump portable across roles.
# --clean / --if-exists make the restore idempotent.
pg_dump \
    --no-owner --no-privileges \
    --clean --if-exists \
    --format=plain \
    "$PROD_READONLY_DATABASE_URL" \
    > "$dump_file"
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
podman cp "$dump_file" "${PG_CONTAINER}:/tmp/restore.sql"

info "restoring into local DB..."
$CMP -f "$COMPOSE_FILE" exec -T postgres psql -U "$LOCAL_PG_USER" -d "$LOCAL_DB_NAME" \
    -v ON_ERROR_STOP=1 -q -f /tmp/restore.sql >/dev/null

ok "restore complete"

# --- migrate + scrub -------------------------------------------------------

info "running 'manage.py migrate' (handles any branch-vs-prod schema drift)..."
$CMP -f "$COMPOSE_FILE" exec -T django python manage.py migrate --noinput

info "running 'manage.py scrub_pii --confirm'..."
$CMP -f "$COMPOSE_FILE" exec -T django \
    python manage.py scrub_pii --confirm "${SCRUB_EXTRA_ARGS[@]}"

# --- cleanup ---------------------------------------------------------------

if [[ "$KEEP_DUMP" -eq 1 ]]; then
    warn "leaving raw dump on disk: ${dump_file}"
    warn "this file contains UNSCRUBBED production PII -- delete it when done."
else
    rm -f "$dump_file"
    $CMP -f "$COMPOSE_FILE" exec -T postgres rm -f /tmp/restore.sql
    ok "raw dump removed from host and container"
fi

ok "done. Local DB '${LOCAL_DB_NAME}' contains scrubbed production data."

#!/bin/bash

# Production Database Backup and Sync Script
# This script backs up production, downloads it locally, and syncs to local database

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Database configuration from render_specs.txt
PROD_DB_HOST="dpg-d16o5v95pdvs73fifljg-a.virginia-postgres.render.com"
PROD_DB_NAME="bunk_logs"
PROD_DB_USER="stevebresnick"
PROD_DB_PASSWORD="bpiFWVkn3Ku89g7A67WjpRsWitc6K0Hw"

# Local database configuration
LOCAL_DB_HOST="localhost"
LOCAL_DB_PORT="5432"
LOCAL_DB_NAME="bunk_logs_local"
LOCAL_DB_USER="postgres"
LOCAL_DB_PASSWORD="postgres"

# Backup directory and filename
BACKUP_DIR="./database_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="production_backup_${TIMESTAMP}.sql"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
print_step "Checking prerequisites..."

if ! command_exists pg_dump; then
    print_error "pg_dump not found. Please install PostgreSQL client tools."
    exit 1
fi

if ! command_exists psql; then
    print_error "psql not found. Please install PostgreSQL client tools."
    exit 1
fi

print_success "Prerequisites check passed"

# Create backup directory
print_step "Creating backup directory..."
mkdir -p "${BACKUP_DIR}"
print_success "Backup directory ready: ${BACKUP_DIR}"

# Step 1: Create production backup
print_step "Creating production database backup..."
echo "This may take a few minutes depending on database size..."

# Use Docker/Podman with PostgreSQL 16 to match production version
podman run --rm \
    -e PGPASSWORD="${PROD_DB_PASSWORD}" \
    postgres:16 \
    pg_dump \
    -h "${PROD_DB_HOST}" \
    -U "${PROD_DB_USER}" \
    -d "${PROD_DB_NAME}" \
    --verbose \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    > "${BACKUP_PATH}"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(ls -lh "${BACKUP_PATH}" | awk '{print $5}')
    print_success "Production backup created: ${BACKUP_PATH} (${BACKUP_SIZE})"
else
    print_error "Failed to create production backup"
    exit 1
fi

# Step 2: Test local database connection
print_step "Testing local database connection..."

podman exec bunk_logs_local_postgres psql \
    -U "${LOCAL_DB_USER}" \
    -d "postgres" \
    -c "SELECT version();" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    print_success "Local database connection successful"
else
    print_error "Cannot connect to local database. Is PostgreSQL running?"
    print_warning "Make sure your local containers are running: podman-compose up -d"
    exit 1
fi

# Step 3: Create local backup (if database exists)
print_step "Creating backup of current local database (if exists)..."

LOCAL_BACKUP_FILE="local_backup_before_sync_${TIMESTAMP}.sql"
LOCAL_BACKUP_PATH="${BACKUP_DIR}/${LOCAL_BACKUP_FILE}"

podman exec bunk_logs_local_postgres pg_dump \
    -U "${LOCAL_DB_USER}" \
    -d "${LOCAL_DB_NAME}" \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    > "${LOCAL_BACKUP_PATH}" 2>/dev/null

if [ $? -eq 0 ]; then
    LOCAL_BACKUP_SIZE=$(ls -lh "${LOCAL_BACKUP_PATH}" | awk '{print $5}')
    print_success "Local database backup created: ${LOCAL_BACKUP_PATH} (${LOCAL_BACKUP_SIZE})"
else
    print_warning "Local database doesn't exist or couldn't be backed up (this is OK for first-time setup)"
    rm -f "${LOCAL_BACKUP_PATH}" 2>/dev/null
fi

# Step 4: Restore production backup to local database
print_step "Restoring production backup to local database..."
echo "This will overwrite your local database with production data..."

podman exec bunk_logs_local_postgres psql \
    -U "${LOCAL_DB_USER}" \
    -d "postgres" \
    -c "DROP DATABASE IF EXISTS ${LOCAL_DB_NAME};" > /dev/null 2>&1

podman exec bunk_logs_local_postgres psql \
    -U "${LOCAL_DB_USER}" \
    -d "postgres" \
    -c "CREATE DATABASE ${LOCAL_DB_NAME};" > /dev/null 2>&1

# Copy backup file into container and restore
podman cp "${BACKUP_PATH}" bunk_logs_local_postgres:/tmp/backup.sql

podman exec bunk_logs_local_postgres psql \
    -U "${LOCAL_DB_USER}" \
    -d "${LOCAL_DB_NAME}" \
    -f "/tmp/backup.sql" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    print_success "Production data successfully restored to local database"
else
    print_error "Failed to restore production backup to local database"
    exit 1
fi

# Step 5: Verify the sync
print_step "Verifying database sync..."

# Check record counts
PROD_COUNT=$(podman run --rm \
    -e PGPASSWORD="${PROD_DB_PASSWORD}" \
    postgres:16 \
    psql \
    -h "${PROD_DB_HOST}" \
    -U "${PROD_DB_USER}" \
    -d "${PROD_DB_NAME}" \
    -t -c "SELECT COUNT(*) FROM bunklogs_bunklog;" 2>/dev/null | tr -d ' ')

LOCAL_COUNT=$(podman exec bunk_logs_local_postgres psql \
    -U "${LOCAL_DB_USER}" \
    -d "${LOCAL_DB_NAME}" \
    -t -c "SELECT COUNT(*) FROM bunklogs_bunklog;" 2>/dev/null | tr -d ' ')

if [ "${PROD_COUNT}" = "${LOCAL_COUNT}" ]; then
    print_success "Sync verified: ${LOCAL_COUNT} BunkLog records in both databases"
else
    print_warning "Record count mismatch: Production=${PROD_COUNT}, Local=${LOCAL_COUNT}"
fi

# Step 6: Run date sync check on local database
print_step "Running date sync check on local database..."
echo "This will show you what records need fixing..."

cd "$(dirname "$0")/backend"

if [ -f "manage.py" ]; then
    podman exec -it bunk_logs_local_django python manage.py check_date_sync
    print_success "Date sync check completed on local database"
else
    print_warning "manage.py not found. Run this from the project root directory."
fi

# Summary
echo ""
echo "========================================="
echo -e "${GREEN}BACKUP AND SYNC COMPLETED SUCCESSFULLY${NC}"
echo "========================================="
echo ""
echo "📁 Files created:"
echo "   Production backup: ${BACKUP_PATH}"
if [ -f "${LOCAL_BACKUP_PATH}" ]; then
    echo "   Local backup:      ${LOCAL_BACKUP_PATH}"
fi
echo ""
echo "✅ Next steps:"
echo "   1. Test the fix_date_sync command on local database first"
echo "   2. If satisfied, run the same command on production"
echo "   3. Keep the backup files safe for rollback if needed"
echo ""
echo "🔧 Test command (run this first):"
echo "   cd backend && podman exec -it bunk_logs_local_django python manage.py fix_date_sync --dry-run"
echo ""
echo "🚀 Production command (run after testing):"
echo "   cd backend && podman exec -it bunk_logs_local_django python manage.py fix_date_sync"
echo ""
echo "⚠️  Rollback command (if needed):"
echo "   ./restore-production-backup.sh ${BACKUP_FILE}"

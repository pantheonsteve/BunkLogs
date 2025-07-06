#!/bin/bash

# Production Database Restore Script
# This script restores a production database backup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Database configuration
PROD_DB_HOST="dpg-d16o5v95pdvs73fifljg-a.virginia-postgres.render.com"
PROD_DB_NAME="bunk_logs"
PROD_DB_USER="stevebresnick"
PROD_DB_PASSWORD="bpiFWVkn3Ku89g7A67WjpRsWitc6K0Hw"

BACKUP_DIR="./database_backups"

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

# Check if backup file is provided
if [ $# -eq 0 ]; then
    print_error "Usage: $0 <backup_filename>"
    echo ""
    echo "Available backups:"
    ls -la "${BACKUP_DIR}"/production_backup_*.sql 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Check if backup file exists
if [ ! -f "${BACKUP_PATH}" ]; then
    print_error "Backup file not found: ${BACKUP_PATH}"
    echo ""
    echo "Available backups:"
    ls -la "${BACKUP_DIR}"/production_backup_*.sql 2>/dev/null || echo "No backups found"
    exit 1
fi

# Confirmation prompt
BACKUP_SIZE=$(ls -lh "${BACKUP_PATH}" | awk '{print $5}')
echo ""
echo "========================================="
echo -e "${RED}⚠️  PRODUCTION DATABASE RESTORE${NC}"
echo "========================================="
echo ""
echo "This will RESTORE the production database with:"
echo "   File: ${BACKUP_PATH}"
echo "   Size: ${BACKUP_SIZE}"
echo ""
echo -e "${YELLOW}WARNING: This will OVERWRITE all current production data!${NC}"
echo ""
read -p "Are you absolutely sure you want to proceed? (type 'YES' to continue): " confirm

if [ "${confirm}" != "YES" ]; then
    print_warning "Restore cancelled by user"
    exit 0
fi

# Additional confirmation
echo ""
read -p "This action cannot be undone. Type 'RESTORE' to confirm: " final_confirm

if [ "${final_confirm}" != "RESTORE" ]; then
    print_warning "Restore cancelled by user"
    exit 0
fi

# Check prerequisites
print_step "Checking prerequisites..."

if ! command -v psql >/dev/null 2>&1; then
    print_error "psql not found. Please install PostgreSQL client tools."
    exit 1
fi

print_success "Prerequisites check passed"

# Test connection
print_step "Testing production database connection..."

PGPASSWORD="${PROD_DB_PASSWORD}" psql \
    -h "${PROD_DB_HOST}" \
    -U "${PROD_DB_USER}" \
    -d "${PROD_DB_NAME}" \
    -c "SELECT version();" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    print_success "Production database connection successful"
else
    print_error "Cannot connect to production database"
    exit 1
fi

# Create a backup before restore (safety measure)
print_step "Creating safety backup before restore..."
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SAFETY_BACKUP="safety_backup_before_restore_${TIMESTAMP}.sql"
SAFETY_BACKUP_PATH="${BACKUP_DIR}/${SAFETY_BACKUP}"

PGPASSWORD="${PROD_DB_PASSWORD}" pg_dump \
    -h "${PROD_DB_HOST}" \
    -U "${PROD_DB_USER}" \
    -d "${PROD_DB_NAME}" \
    --verbose \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    > "${SAFETY_BACKUP_PATH}"

if [ $? -eq 0 ]; then
    SAFETY_SIZE=$(ls -lh "${SAFETY_BACKUP_PATH}" | awk '{print $5}')
    print_success "Safety backup created: ${SAFETY_BACKUP_PATH} (${SAFETY_SIZE})"
else
    print_error "Failed to create safety backup"
    exit 1
fi

# Restore the backup
print_step "Restoring backup to production database..."
echo "This may take several minutes..."

PGPASSWORD="${PROD_DB_PASSWORD}" psql \
    -h "${PROD_DB_HOST}" \
    -U "${PROD_DB_USER}" \
    -d "${PROD_DB_NAME}" \
    < "${BACKUP_PATH}"

if [ $? -eq 0 ]; then
    print_success "Backup successfully restored to production database"
else
    print_error "Failed to restore backup to production database"
    print_warning "Production database may be in an inconsistent state"
    print_warning "Safety backup available at: ${SAFETY_BACKUP_PATH}"
    exit 1
fi

# Verify the restore
print_step "Verifying restore..."

RECORD_COUNT=$(PGPASSWORD="${PROD_DB_PASSWORD}" psql \
    -h "${PROD_DB_HOST}" \
    -U "${PROD_DB_USER}" \
    -d "${PROD_DB_NAME}" \
    -t -c "SELECT COUNT(*) FROM bunklogs_bunklog;" 2>/dev/null | tr -d ' ')

if [ ! -z "${RECORD_COUNT}" ] && [ "${RECORD_COUNT}" -gt 0 ]; then
    print_success "Restore verified: ${RECORD_COUNT} BunkLog records found"
else
    print_warning "Could not verify restore or no records found"
fi

# Summary
echo ""
echo "========================================="
echo -e "${GREEN}PRODUCTION RESTORE COMPLETED${NC}"
echo "========================================="
echo ""
echo "📁 Files:"
echo "   Restored from:  ${BACKUP_PATH}"
echo "   Safety backup:  ${SAFETY_BACKUP_PATH}"
echo ""
echo "✅ Production database has been restored"
echo "🔧 You may want to run health checks on your application"

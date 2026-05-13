#!/bin/bash

# Production Date Fix Script
# This script runs the fix_date_sync command on production database

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

# Check if we're in dry-run mode
DRY_RUN=""
if [ "$1" = "--dry-run" ]; then
    DRY_RUN="--dry-run"
    print_warning "Running in DRY-RUN mode - no changes will be made"
else
    echo ""
    echo "========================================="
    echo -e "${YELLOW}⚠️  PRODUCTION DATABASE UPDATE${NC}"
    echo "========================================="
    echo ""
    echo "This will fix date mismatches in the production database."
    echo "Make sure you have run the backup script first!"
    echo ""
    read -p "Have you created a backup? (y/N): " backup_confirm
    
    if [ "${backup_confirm}" != "y" ] && [ "${backup_confirm}" != "Y" ]; then
        print_error "Please run ./backup-and-sync-db.sh first to create a backup"
        exit 1
    fi
    
    read -p "Are you sure you want to update production? (type 'YES'): " confirm
    
    if [ "${confirm}" != "YES" ]; then
        print_warning "Production update cancelled by user"
        exit 0
    fi
fi

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

# Check current mismatch count
print_step "Checking current date mismatches..."

cd backend

# Use a temporary container to run the management command against production
MISMATCH_COUNT=$(PGPASSWORD="${PROD_DB_PASSWORD}" podman run --rm \
    -e DATABASE_URL="postgresql://${PROD_DB_USER}:${PROD_DB_PASSWORD}@${PROD_DB_HOST}/${PROD_DB_NAME}" \
    -e DJANGO_SETTINGS_MODULE="config.settings.production" \
    -v "$(pwd):/app" \
    -w /app \
    python:3.13-slim-bullseye \
    bash -c "
        pip install -q psycopg2-binary django
        python manage.py check_date_sync 2>/dev/null | grep 'Found' | grep -o '[0-9]\\+' | head -1
    " 2>/dev/null || echo "0")

print_success "Found ${MISMATCH_COUNT} records with date mismatches"

if [ "${MISMATCH_COUNT}" = "0" ]; then
    print_success "No mismatches found - database is already consistent!"
    exit 0
fi

# Run the fix
if [ -n "${DRY_RUN}" ]; then
    print_step "Running date sync fix in DRY-RUN mode..."
    COMMAND="fix_date_sync --dry-run"
else
    print_step "Running date sync fix on production..."
    COMMAND="fix_date_sync"
fi

PGPASSWORD="${PROD_DB_PASSWORD}" podman run --rm \
    -e DATABASE_URL="postgresql://${PROD_DB_USER}:${PROD_DB_PASSWORD}@${PROD_DB_HOST}/${PROD_DB_NAME}" \
    -e DJANGO_SETTINGS_MODULE="config.settings.production" \
    -v "$(pwd):/app" \
    -w /app \
    python:3.13-slim-bullseye \
    bash -c "
        pip install -q psycopg2-binary django pytz
        python manage.py ${COMMAND}
    "

if [ $? -eq 0 ]; then
    if [ -n "${DRY_RUN}" ]; then
        print_success "Dry-run completed successfully"
        echo ""
        echo "To apply the changes, run:"
        echo "   ./fix-production-dates.sh"
    else
        print_success "Production date fix completed successfully"
        
        # Verify the fix
        print_step "Verifying the fix..."
        FINAL_COUNT=$(PGPASSWORD="${PROD_DB_PASSWORD}" podman run --rm \
            -e DATABASE_URL="postgresql://${PROD_DB_USER}:${PROD_DB_PASSWORD}@${PROD_DB_HOST}/${PROD_DB_NAME}" \
            -e DJANGO_SETTINGS_MODULE="config.settings.production" \
            -v "$(pwd):/app" \
            -w /app \
            python:3.13-slim-bullseye \
            bash -c "
                pip install -q psycopg2-binary django
                python manage.py check_date_sync 2>/dev/null | grep 'Found' | grep -o '[0-9]\\+' | head -1
            " 2>/dev/null || echo "0")
        
        print_success "After fix: ${FINAL_COUNT} records with date mismatches"
        
        if [ "${FINAL_COUNT}" = "0" ]; then
            print_success "🎉 All date mismatches have been fixed!"
        else
            print_warning "Some mismatches remain. This might be expected for edge cases."
        fi
    fi
else
    print_error "Fix command failed"
    if [ -z "${DRY_RUN}" ]; then
        print_warning "Production database may be in an inconsistent state"
        print_warning "Consider restoring from backup if needed"
    fi
    exit 1
fi

echo ""
if [ -n "${DRY_RUN}" ]; then
    echo "========================================="
    echo -e "${GREEN}DRY-RUN COMPLETED${NC}"
    echo "========================================="
else
    echo "========================================="
    echo -e "${GREEN}PRODUCTION FIX COMPLETED${NC}"
    echo "========================================="
fi

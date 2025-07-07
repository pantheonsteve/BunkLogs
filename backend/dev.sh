#!/bin/bash

# Development Commands Helper
# Usage: ./dev.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
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

# Check if virtual environment is activated
check_venv() {
    if [[ -z "${VIRTUAL_ENV}" ]]; then
        print_warning "Virtual environment not activated. Activating..."
        source venv/bin/activate
    fi
}

# Setup Podman environment
setup_podman_env() {
    if command -v podman &> /dev/null; then
        # Check if Podman machine is running
        if ! podman machine list | grep -q "Currently running"; then
            print_status "Starting Podman machine..."
            podman machine start
        fi
        
        # The machine start should set up the environment automatically
        # but let's verify podman is accessible
        if ! podman info &> /dev/null; then
            print_error "Podman is not accessible. Please check your Podman installation."
            exit 1
        fi
    fi
}

# Detect available compose command - prefer Podman
get_compose_command() {
    if command -v podman-compose &> /dev/null; then
        echo "podman-compose"
    elif command -v podman &> /dev/null; then
        echo "podman compose"
    else
        print_error "Podman not found. Please install Podman Desktop or Podman CLI."
        print_error "Install from: https://podman-desktop.io/"
        exit 1
    fi
}

# Function to show help
show_help() {
    echo "BunkLogs Backend Development Helper"
    echo "=================================="
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup           - Set up local development environment"
    echo "  start           - Start local development server"
    echo "  test            - Run tests"
    echo "  test-coverage   - Run tests with coverage"
    echo "  migrate         - Run database migrations"
    echo "  makemigrations  - Create new migrations"
    echo "  shell           - Open Django shell"
    echo "  superuser       - Create superuser"
    echo "  collectstatic   - Collect static files"
    echo "  docker-up       - Start Docker services"
    echo "  docker-down     - Stop Docker services"
    echo "  docker-reset    - Reset Docker services and volumes"
    echo "  lint            - Run code linting"
    echo "  format          - Format code with black"
    echo "  requirements    - Update requirements.txt files"
    echo "  clean           - Clean cache and temp files"
    echo "  logs            - Show application logs"
    echo "  backup-db       - Backup local database"
    echo "  restore-db      - Restore local database"
    echo "  sync-prod-db    - Sync production database to local (DESTRUCTIVE)"
    echo "  import-prod-db  - Import production database using backup script (RECOMMENDED)"
    echo "  analyze-date-conflicts - Analyze unique constraint conflicts preventing date fixes"
    echo "  smart-date-fix  - Intelligently fix date conflicts by handling duplicates"
    echo "  fix-july-6-7-dates - Fix BunkLog date fields to match created_at timezone"
    echo "  help            - Show this help message"
}

case "$1" in
    setup)
        print_status "Setting up local development environment..."
        ./setup-local-dev.sh
        print_success "Setup complete!"
        ;;
    
    start)
        check_venv
        setup_podman_env
        print_status "Starting Django development server..."
        export DJANGO_READ_DOT_ENV_FILE=True
        python manage.py runserver
        ;;
    
    test)
        check_venv
        setup_podman_env
        print_status "Running tests..."
        export DJANGO_READ_DOT_ENV_FILE=True
        python manage.py test
        ;;
    
    test-coverage)
        check_venv
        setup_podman_env
        print_status "Running tests with coverage..."
        export DJANGO_READ_DOT_ENV_FILE=True
        if command -v coverage &> /dev/null; then
            coverage run --source='.' manage.py test
            coverage report
            coverage html
            print_success "Coverage report generated in htmlcov/index.html"
        else
            print_warning "Coverage not installed. Install with: pip install coverage"
            python manage.py test
        fi
        ;;
    
    migrate)
        check_venv
        print_status "Running database migrations..."
        export DJANGO_READ_DOT_ENV_FILE=True
        python manage.py migrate
        print_success "Migrations complete!"
        ;;
    
    makemigrations)
        check_venv
        print_status "Creating new migrations..."
        export DJANGO_READ_DOT_ENV_FILE=True
        python manage.py makemigrations
        print_success "Migrations created!"
        ;;
    
    shell)
        check_venv
        print_status "Opening Django shell..."
        export DJANGO_READ_DOT_ENV_FILE=True
        python manage.py shell
        ;;
    
    superuser)
        check_venv
        print_status "Creating superuser..."
        export DJANGO_READ_DOT_ENV_FILE=True
        python manage.py createsuperuser
        ;;
    
    collectstatic)
        check_venv
        print_status "Collecting static files..."
        export DJANGO_READ_DOT_ENV_FILE=True
        python manage.py collectstatic --noinput
        print_success "Static files collected!"
        ;;
    
    docker-up)
        setup_podman_env
        print_status "Starting Podman services..."
        COMPOSE_CMD=$(get_compose_command)
        $COMPOSE_CMD -f docker-compose.local.yml up -d
        print_success "Podman services started!"
        ;;
    
    docker-down)
        setup_podman_env
        print_status "Stopping Podman services..."
        COMPOSE_CMD=$(get_compose_command)
        $COMPOSE_CMD -f docker-compose.local.yml down
        print_success "Podman services stopped!"
        ;;
    
    docker-reset)
        setup_podman_env
        print_status "Resetting Podman services and volumes..."
        COMPOSE_CMD=$(get_compose_command)
        $COMPOSE_CMD -f docker-compose.local.yml down -v
        $COMPOSE_CMD -f docker-compose.local.yml up -d
        sleep 5
        check_venv
        python manage.py migrate
        print_success "Podman services reset!"
        ;;
    
    lint)
        check_venv
        print_status "Running code linting..."
        if command -v flake8 &> /dev/null; then
            flake8 --max-line-length=120 --exclude=migrations,venv,env .
            print_success "Linting complete!"
        else
            print_warning "Flake8 not installed. Install with: pip install flake8"
        fi
        ;;
    
    format)
        check_venv
        print_status "Formatting code with black..."
        if command -v black &> /dev/null; then
            black --line-length=120 --exclude=migrations .
            print_success "Code formatting complete!"
        else
            print_warning "Black not installed. Install with: pip install black"
        fi
        ;;
    
    requirements)
        check_venv
        print_status "Updating requirements files..."
        pip freeze > requirements/local.txt.new
        print_warning "Review requirements/local.txt.new and update manually"
        ;;
    
    clean)
        print_status "Cleaning cache and temp files..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        find . -type f -name "*.pyo" -delete 2>/dev/null || true
        find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
        rm -rf .coverage htmlcov/ .pytest_cache/ .tox/ 2>/dev/null || true
        print_success "Cache cleaned!"
        ;;
    
    logs)
        print_status "Showing Django application logs..."
        COMPOSE_CMD=$(get_compose_command)
        $COMPOSE_CMD -f docker-compose.local.yml logs -f django
        ;;
    
    backup-db)
        print_status "Backing up local database..."
        COMPOSE_CMD=$(get_compose_command)
        $COMPOSE_CMD -f docker-compose.local.yml exec postgres pg_dump -U postgres bunk_logs_local > backup_$(date +%Y%m%d_%H%M%S).sql
        print_success "Database backed up!"
        ;;
    
    restore-db)
        if [ -z "$2" ]; then
            print_error "Please provide backup file: ./dev.sh restore-db backup_file.sql"
            exit 1
        fi
        print_status "Restoring database from $2..."
        COMPOSE_CMD=$(get_compose_command)
        $COMPOSE_CMD -f docker-compose.local.yml exec -T postgres psql -U postgres bunk_logs_local < "$2"
        print_success "Database restored!"
        ;;
    
    sync-prod-db)
        print_warning "⚠️  This will COMPLETELY REPLACE your local database with production data!"
        print_warning "⚠️  All local data will be lost!"
        echo ""
        read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm
        
        if [ "$confirm" != "yes" ]; then
            print_status "Operation cancelled."
            exit 0
        fi
        
        print_status "Syncing production database to local..."
        
        # Check if pg_dump is available
        if ! command -v pg_dump &> /dev/null; then
            print_error "pg_dump is not installed. Please install PostgreSQL client tools:"
            print_error "  macOS: brew install postgresql"
            print_error "  Ubuntu: sudo apt-get install postgresql-client"
            exit 1
        fi
        
        # Check if production DATABASE_URL is set
        check_venv
        export DJANGO_READ_DOT_ENV_FILE=True
        
        # Try to get DATABASE_URL from environment or .env
        if [ -f .env ]; then
            source .env
        fi
        
        if [ -z "${PROD_DATABASE_URL:-}" ]; then
            print_error "PROD_DATABASE_URL environment variable not set."
            print_error "Please add your production database URL to .env file:"
            print_error "  PROD_DATABASE_URL=postgresql://user:pass@host:port/database"
            print_error ""
            print_error "You can find this in your Render.com dashboard under:"
            print_error "  Your Service > Environment > DATABASE_URL"
            exit 1
        fi
        
        # Ensure local containers are running
        setup_podman_env
        COMPOSE_CMD=$(get_compose_command)
        print_status "Starting local database services..."
        $COMPOSE_CMD -f docker-compose.local.yml up -d postgres
        sleep 5
        
        # Create timestamp for backup file
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="/tmp/prod_sync_${TIMESTAMP}.sql"
        
        print_status "Creating backup of production database..."
        if ! pg_dump --no-owner --no-privileges "$PROD_DATABASE_URL" > "$BACKUP_FILE"; then
            print_error "Failed to create production backup"
            print_error "Please check your PROD_DATABASE_URL and network connectivity"
            rm -f "$BACKUP_FILE"
            exit 1
        fi
        
        print_status "Dropping local database..."
        $COMPOSE_CMD -f docker-compose.local.yml exec postgres dropdb -U postgres bunk_logs_local --if-exists || true
        
        print_status "Creating fresh local database..."
        $COMPOSE_CMD -f docker-compose.local.yml exec postgres createdb -U postgres bunk_logs_local
        
        print_status "Restoring production data to local database..."
        if ! $COMPOSE_CMD -f docker-compose.local.yml exec -T postgres psql -U postgres bunk_logs_local < "$BACKUP_FILE"; then
            print_error "Failed to restore database"
            # rm -f "$BACKUP_FILE"   # Commented out to keep the backup file for debugging
            exit 1
        fi
        
        # Clean up
        # rm -f "$BACKUP_FILE"   # Commented out to keep the backup file for debugging
        
        print_success "Production database successfully synced to local!"
        print_success "Your local database now contains production data."
        
        # Run migrations in case there are local schema differences
        print_status "Running any pending migrations..."
        export DJANGO_READ_DOT_ENV_FILE=True
        python manage.py migrate
        
        print_success "Database sync complete!"
        ;;
    
    import-prod-db)
        print_warning "⚠️  This will COMPLETELY REPLACE your local database with production data!"
        print_warning "⚠️  All local data will be lost!"
        echo ""
        read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm
        
        if [ "$confirm" != "yes" ]; then
            print_status "Operation cancelled."
            exit 0
        fi
        
        print_status "Importing production database using backup script..."
        
        # Change to project root where backup script is located
        cd "$(dirname "$0")/.."
        
        # Check if backup script exists
        if [ ! -f "backup-and-sync-db.sh" ]; then
            print_error "backup-and-sync-db.sh not found in project root"
            exit 1
        fi
        
        # Make sure script is executable
        chmod +x backup-and-sync-db.sh
        
        # Run the backup and sync script
        ./backup-and-sync-db.sh
        
        if [ $? -eq 0 ]; then
            print_success "Production database successfully imported!"
            print_success "You can now log in with production user accounts."
        else
            print_error "Database import failed. Check the output above for details."
            exit 1
        fi
        ;;
    
    analyze-date-conflicts)
        check_venv
        print_status "Analyzing date fix conflicts..."
        export DJANGO_READ_DOT_ENV_FILE=True
        python manage.py shell -c "
from bunk_logs.bunklogs.models import BunkLog
from django.utils import timezone
from django.db.models import Q
from datetime import date

# Find records that need date fixes (check each record individually)
all_records = BunkLog.objects.all().order_by('bunk_assignment_id', 'date')
needs_fix = []

for record in all_records:
    correct_date = timezone.localtime(record.created_at).date()
    if record.date != correct_date:
        needs_fix.append(record)

print(f'Found {len(needs_fix)} records that need date fixes')
print()

# Check for potential conflicts
conflicts = []
for record in needs_fix[:20]:  # Check first 20
    correct_date = timezone.localtime(record.created_at).date()
    
    # Check if there's already a record for this bunk_assignment on the correct date
    existing = BunkLog.objects.filter(
        bunk_assignment_id=record.bunk_assignment_id,
        date=correct_date
    ).exclude(id=record.id).first()
    
    if existing:
        conflicts.append({
            'record_id': record.id,
            'bunk_assignment': record.bunk_assignment_id,
            'wrong_date': record.date,
            'correct_date': correct_date,
            'existing_id': existing.id,
            'existing_created': existing.created_at
        })

print(f'Found {len(conflicts)} potential conflicts:')
for conflict in conflicts[:10]:
    print(f'  Record {conflict[\"record_id\"]} (bunk {conflict[\"bunk_assignment\"]}) wants to move from {conflict[\"wrong_date\"]} to {conflict[\"correct_date\"]}')
    print(f'    But record {conflict[\"existing_id\"]} already exists for {conflict[\"correct_date\"]} (created: {conflict[\"existing_created\"]})')
    print()
"
        ;;
    
    smart-date-fix)
        check_venv
        print_status "Running smart date fix (dry run first)..."
        export DJANGO_READ_DOT_ENV_FILE=True
        
        # Show what would happen
        python manage.py smart_date_fix --dry-run --strategy=keep-latest
        
        echo ""
        print_warning "⚠️  This will modify and delete records to resolve date conflicts!"
        read -p "Do you want to proceed with the actual fix? (type 'yes' to confirm): " confirm
        
        if [ "$confirm" == "yes" ]; then
            print_status "Applying smart date fix..."
            python manage.py smart_date_fix --strategy=keep-latest
            print_success "Smart date fix complete!"
        else
            print_status "Operation cancelled."
        fi
        ;;
    
    fix-july-6-7-dates)
        check_venv
        print_status "Fixing ALL BunkLog dates to match America/New_York timezone..."
        export DJANGO_READ_DOT_ENV_FILE=True
        
        # First, run analysis to show what will happen
        python manage.py shell -c "
from bunk_logs.bunklogs.models import BunkLog
from django.utils import timezone
from datetime import date, datetime
from django.db import transaction

print('🔍 Analyzing BunkLog date mismatches (America/New_York timezone)...')
print('=' * 70)

# Find ALL logs where date field doesn't match the local timezone date
mismatched_logs = []
total_logs = BunkLog.objects.count()

print(f'Checking {total_logs} BunkLogs for date field mismatches...')
print('(This may take a moment for large datasets)')
print()

# Check each log to see if date matches local timezone
for log in BunkLog.objects.all():
    local_date = timezone.localtime(log.created_at).date()
    if log.date != local_date:
        mismatched_logs.append({
            'log': log,
            'current_date': log.date,
            'correct_date': local_date,
            'created_at': log.created_at
        })

print(f'Found {len(mismatched_logs)} logs with incorrect date fields')
print()

if len(mismatched_logs) == 0:
    print('✅ All BunkLog dates already match America/New_York timezone!')
    exit()

# Analyze the mismatches
date_changes = {}
for item in mismatched_logs:
    change_key = f'{item[\"current_date\"]} → {item[\"correct_date\"]}'
    if change_key not in date_changes:
        date_changes[change_key] = []
    date_changes[change_key].append(item)

print('📊 Date changes needed:')
for change, logs in date_changes.items():
    print(f'  {change}: {len(logs)} logs')

print()

# Check for potential duplicates after fixing
print('🔍 Checking for potential duplicate conflicts...')
duplicates_to_delete = []
logs_to_fix = []

for item in mismatched_logs:
    log = item['log']
    correct_date = item['correct_date']
    
    # Check if there's already a log for this bunk on the correct date
    existing = BunkLog.objects.filter(
        bunk_assignment_id=log.bunk_assignment_id,
        date=correct_date
    ).exclude(id=log.id).first()
    
    if existing:
        duplicates_to_delete.append({
            'log': log,
            'existing': existing,
            'reason': f'Duplicate - log for {correct_date} already exists'
        })
    else:
        logs_to_fix.append(item)

print(f'� Summary:')
print(f'  - Logs to FIX (update date): {len(logs_to_fix)}')
print(f'  - Logs to DELETE (duplicates): {len(duplicates_to_delete)}')
print()

if duplicates_to_delete:
    print('🗑️  Logs to DELETE (duplicates):')
    for item in duplicates_to_delete[:10]:
        log = item['log']
        existing = item['existing']
        print(f'  - ID {log.id} (bunk {log.bunk_assignment_id}) - duplicate of ID {existing.id}')
    if len(duplicates_to_delete) > 10:
        print(f'  ... and {len(duplicates_to_delete) - 10} more')
    print()

if logs_to_fix:
    print('🔧 Logs to FIX (update date field):')
    for item in logs_to_fix[:10]:
        log = item['log']
        print(f'  - ID {log.id} (bunk {log.bunk_assignment_id}): {item[\"current_date\"]} → {item[\"correct_date\"]}')
    if len(logs_to_fix) > 10:
        print(f'  ... and {len(logs_to_fix) - 10} more')
    print()

print(f'🎯 Total fixes needed: {len(logs_to_fix) + len(duplicates_to_delete)}')
"
        
        echo ""
        print_warning "⚠️  This was a DRY RUN - no changes were made!"
        read -p "Do you want to EXECUTE the fixes? (type 'yes' to confirm): " confirm
        
        if [ "$confirm" == "yes" ]; then
            print_status "Executing BunkLog date fixes for America/New_York timezone..."
            python manage.py shell -c "
from bunk_logs.bunklogs.models import BunkLog
from django.utils import timezone
from datetime import date
from django.db import transaction

print('🚀 EXECUTING BunkLog date fixes...')
print('=' * 50)

# Find all mismatched logs again
mismatched_logs = []
for log in BunkLog.objects.all():
    local_date = timezone.localtime(log.created_at).date()
    if log.date != local_date:
        mismatched_logs.append({
            'log': log,
            'current_date': log.date,
            'correct_date': local_date
        })

deleted_count = 0
fixed_count = 0

# Use transaction for safety
with transaction.atomic():
    for item in mismatched_logs:
        log = item['log']
        correct_date = item['correct_date']
        
        # Check for existing log on correct date
        existing = BunkLog.objects.filter(
            bunk_assignment_id=log.bunk_assignment_id,
            date=correct_date
        ).exclude(id=log.id).first()
        
        if existing:
            # Delete duplicate
            print(f'🗑️  DELETING duplicate ID {log.id} (bunk {log.bunk_assignment_id}) - {correct_date} log already exists (ID {existing.id})')
            log.delete()
            deleted_count += 1
        else:
            # Fix date to match local timezone
            print(f'🔧 FIXING ID {log.id} (bunk {log.bunk_assignment_id}): {item[\"current_date\"]} → {correct_date}')
            log.date = correct_date
            log.save()
            fixed_count += 1

print()
print(f'✅ COMPLETED:')
print(f'  - Deleted {deleted_count} duplicate records')
print(f'  - Fixed {fixed_count} date fields to match America/New_York timezone')
print(f'  - Total processed: {deleted_count + fixed_count}')
print()
print('🎯 All BunkLog dates now consistently use America/New_York timezone!')
"
            print_success "BunkLog timezone fixes completed!"
        else
            print_status "Operation cancelled."
        fi
        ;;

    help|"")
        show_help
        ;;
    
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac

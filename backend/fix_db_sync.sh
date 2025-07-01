#!/bin/bash

# Fix database sync by truncating all data and restoring from production backup
set -e

# Activate virtual environment
source venv/bin/activate

echo "=== FIXING DATABASE SYNC ==="
echo "This script will:"
echo "1. Truncate all data from local database (keeping schema)"
echo "2. Restore data from production backup"
echo ""

BACKUP_FILE="/tmp/prod_sync_20250630_232931.sql"
LOCAL_DB="postgres://postgres:postgres@localhost:5432/bunk_logs_local"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file $BACKUP_FILE not found!"
    exit 1
fi

echo "Step 1: Creating data-only backup file..."
# Extract only COPY statements and their data
awk '
    /^COPY / { copying=1; print }
    copying && /^\\.$/ { print; copying=0 }
    copying && !/^COPY / && !/^\\.$/ { print }
' "$BACKUP_FILE" > /tmp/prod_data_only.sql

echo "Step 2: Getting list of all tables to truncate..."
# Get list of all tables from Django
python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT LIKE 'django_%' AND tablename NOT LIKE 'auth_%' AND tablename != 'account_emailaddress' AND tablename != 'account_emailconfirmation' AND tablename != 'authtoken_token' AND tablename != 'socialaccount_socialaccount' AND tablename != 'socialaccount_socialapp' AND tablename != 'socialaccount_socialapp_sites' AND tablename != 'socialaccount_socialtoken'\")
tables = [row[0] for row in cursor.fetchall()]
print('Tables to truncate:', tables)
# Generate truncate statements
truncate_sql = []
for table in tables:
    truncate_sql.append(f'TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;')
with open('/tmp/truncate_tables.sql', 'w') as f:
    f.write('\n'.join(truncate_sql))
print('Truncate SQL written to /tmp/truncate_tables.sql')
"

echo "Step 3: Truncating all application tables..."
psql "$LOCAL_DB" -f /tmp/truncate_tables.sql

echo "Step 4: Restoring data from production backup..."
psql "$LOCAL_DB" -f /tmp/prod_data_only.sql

echo "Step 5: Verifying the restore..."
python3 manage.py shell -c "
from django.contrib.auth import get_user_model
from bunk_logs.bunks.models import Bunk
from bunk_logs.bunklogs.models import CounselorLog

User = get_user_model()
print('=== POST-RESTORE VERIFICATION ===')
print(f'Users: {User.objects.count()}')
print(f'Bunks: {Bunk.objects.count()}')
print(f'Counselor Logs: {CounselorLog.objects.count()}')
print()
print('Sample users:')
for user in User.objects.all()[:3]:
    print(f'  - {user.email} ({user.first_name} {user.last_name}) - Role: {user.role}')
print()
print('Sample bunks:')
for bunk in Bunk.objects.all()[:3]:
    print(f'  - {bunk.name} in {bunk.unit.name if bunk.unit else \"No Unit\"}')
"

echo ""
echo "=== DATABASE SYNC COMPLETE ==="
echo "Your local database should now contain production data!"

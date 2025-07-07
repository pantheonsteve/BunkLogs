#!/bin/bash

# Production BunkLog Date Fix Script
# This script fixes the production database issue where BunkLogs were created on July 6th 
# but incorrectly dated July 7th due to the old date-shifting logic.

set -e  # Exit on any error

echo "🔧 BunkLog Production Date Fix Script"
echo "======================================"
echo

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Please run this script from the Django project root."
    exit 1
fi

# Step 1: Create backup
echo "📦 Step 1: Creating backup..."
python manage.py backup_bunklogs --output="bunklogs_backup_$(date +%Y%m%d_%H%M%S).json"
echo

# Step 2: Analyze the problem (dry run)
echo "🔍 Step 2: Analyzing problematic logs..."
python manage.py fix_production_dates --dry-run
echo

# Step 3: Ask for confirmation
echo "⚠️  WARNING: This will modify your production database!"
echo "   - Duplicate logs will be DELETED"
echo "   - Incorrectly dated logs will have their dates UPDATED"
echo
read -p "Do you want to proceed with the fix? (type 'YES' to confirm): " confirmation

if [ "$confirmation" != "YES" ]; then
    echo "❌ Fix cancelled. No changes made."
    exit 0
fi

# Step 4: Apply the fix
echo
echo "🚀 Step 3: Applying fixes..."
python manage.py fix_production_dates --force
echo

# Step 5: Verify the fix
echo "✅ Step 4: Verifying fixes..."
python manage.py fix_production_dates --dry-run
echo

echo "🎉 Production date fix completed!"
echo "   - Backup files are saved for recovery if needed"
echo "   - Check the output above to confirm all issues were resolved"

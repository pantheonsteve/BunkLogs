#!/bin/bash

# Production BunkLog Fix Script
# This script fixes the July 7th BunkLog date issue in production

echo "=========================================="
echo "Production BunkLog Fix Script"
echo "Date: $(date)"
echo "=========================================="

# Set production environment variables
export DJANGO_SETTINGS_MODULE=config.settings.production

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Create backup of current BunkLog data${NC}"
echo "Creating backup..."

# Create backup directory with timestamp
BACKUP_DIR="bunklogs_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup all BunkLogs from July 5-8, 2025
echo "Backing up BunkLogs from July 5-8, 2025..."
python manage.py dumpdata bunklogs.BunkLog \
    --indent 2 \
    --natural-foreign \
    --natural-primary \
    > $BACKUP_DIR/bunklogs_july_5_8_backup.json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup created successfully in $BACKUP_DIR${NC}"
else
    echo -e "${RED}✗ Backup failed! Aborting.${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 2: Analyze current state${NC}"
echo "Running analysis..."
python manage.py analyze_bunklog_dates

echo -e "\n${YELLOW}Step 3: Run dry-run to see what would be fixed${NC}"
echo "Dry run of fix command..."
python manage.py fix_july_7_bunklogs --dry-run

echo -e "\n${YELLOW}Step 4: Waiting for confirmation...${NC}"
echo -e "${RED}IMPORTANT: Review the dry-run output above carefully.${NC}"
echo -e "Press ${GREEN}ENTER${NC} to proceed with the fix, or ${RED}Ctrl+C${NC} to abort:"
read -r

echo -e "\n${YELLOW}Step 5: Executing the fix${NC}"
echo "Running fix command..."
python manage.py fix_july_7_bunklogs --force

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Fix completed successfully${NC}"
else
    echo -e "${RED}✗ Fix failed!${NC}"
    echo -e "${YELLOW}Backup is available in $BACKUP_DIR${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 6: Verify the fix${NC}"
echo "Running post-fix analysis..."
python manage.py analyze_bunklog_dates

echo -e "\n${GREEN}=========================================="
echo "Production fix completed successfully!"
echo "Backup location: $BACKUP_DIR"
echo "Date: $(date)"
echo -e "==========================================${NC}"

# Optional: Clean up old backups (keep last 5)
echo -e "\n${YELLOW}Cleaning up old backups (keeping last 5)...${NC}"
ls -t bunklogs_backup_* | tail -n +6 | xargs -r rm -rf
echo -e "${GREEN}✓ Cleanup completed${NC}"

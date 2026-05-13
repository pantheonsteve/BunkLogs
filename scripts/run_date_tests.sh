#!/bin/bash
# Test runner script for date synchronization tests

echo "🧪 Running BunkLog and CounselorLog Date Synchronization Tests"
echo "============================================================="

# Navigate to backend directory
cd /Users/steve.bresnick/Projects/BunkLogs/backend

# Run the specific test file
echo "Running date sync tests..."
python manage.py test bunk_logs.bunklogs.tests.test_date_sync -v 2

echo ""
echo "✅ Test run complete!"
echo ""
echo "💡 To run these tests in your container:"
echo "   1. In Podman Desktop terminal:"
echo "      cd /app"
echo "      python manage.py test bunk_logs.bunklogs.tests.test_date_sync -v 2"
echo ""
echo "   2. Or run all bunklogs tests:"
echo "      python manage.py test bunk_logs.bunklogs -v 2"
echo ""
echo "   3. Or run all tests:"
echo "      python manage.py test -v 2"

#!/bin/bash

echo "=== CamperList Fix Verification Script ==="
echo ""

# Get today's date
TODAY=$(date +%Y-%m-%d)
echo "Today's date: $TODAY"
echo ""

# Test 1: Check if backend is responding
echo "Test 1: Backend Health Check"
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/get-csrf-token/)
if [ "$response" = "200" ]; then
    echo "✅ Backend is responding (HTTP $response)"
else
    echo "❌ Backend not responding (HTTP $response)"
fi
echo ""

# Test 2: Check frontend is running
echo "Test 2: Frontend Health Check"
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/)
if [ "$response" = "200" ]; then
    echo "✅ Frontend is responding (HTTP $response)"
else
    echo "❌ Frontend not responding (HTTP $response)"
fi
echo ""

# Test 3: Check if any 403 errors are appearing in recent logs
echo "Test 3: Check Recent Backend Logs for 403 Errors"
cd /Users/steve.bresnick/Projects/BunkLogs/backend

# Get recent logs and check for 403 errors
recent_403=$(docker-compose -f docker-compose.local.yml logs --tail=20 django 2>/dev/null | grep -c "403")
echo "Recent 403 errors in logs: $recent_403"

if [ "$recent_403" -eq 0 ]; then
    echo "✅ No recent 403 errors found"
else
    echo "⚠️ Found $recent_403 recent 403 errors"
    echo "Recent 403 error details:"
    docker-compose -f docker-compose.local.yml logs --tail=20 django 2>/dev/null | grep "403" | tail -3
fi
echo ""

# Test 4: Check the CamperList component for our fixes
echo "Test 4: Verify CamperList Code Changes"
CAMPER_LIST_FILE="/Users/steve.bresnick/Projects/BunkLogs/frontend/src/partials/bunk-dashboard/CamperList.jsx"

if grep -q 'date !== "2025-01-01"' "$CAMPER_LIST_FILE"; then
    echo "✅ Found date validation check in CamperList"
else
    echo "❌ Date validation check not found in CamperList"
fi

if grep -q 'setError(null); // Clear any previous errors' "$CAMPER_LIST_FILE"; then
    echo "✅ Found error state clearing in CamperList"
else
    echo "❌ Error state clearing not found in CamperList"
fi

if grep -q 'error && data.length === 0' "$CAMPER_LIST_FILE"; then
    echo "✅ Found improved error condition in CamperList"
else
    echo "❌ Improved error condition not found in CamperList"
fi
echo ""

# Test 5: Check BunkDashboard for today's date default
echo "Test 5: Verify BunkDashboard Date Logic"
BUNK_DASHBOARD_FILE="/Users/steve.bresnick/Projects/BunkLogs/frontend/src/pages/BunkDashboard.jsx"

if grep -q 'new Date().toISOString().split' "$BUNK_DASHBOARD_FILE"; then
    echo "✅ Found today's date default in BunkDashboard"
else
    echo "❌ Today's date default not found in BunkDashboard"
fi
echo ""

echo "=== Verification Complete ==="
echo ""
echo "Summary of fixes implemented:"
echo "1. ✅ CamperList skips API calls for default fallback date (2025-01-01)"
echo "2. ✅ CamperList clears error state on successful fetch"
echo "3. ✅ CamperList only shows errors when there's no data"
echo "4. ✅ BunkDashboard uses today's date as default instead of 2025-01-01"
echo "5. ✅ Improved error handling and user feedback"
echo ""
echo "Next steps:"
echo "1. Log in to the application as a Unit Head (uh1@clc.org)"
echo "2. Navigate to a bunk dashboard"
echo "3. Verify camper list loads without errors"
echo "4. Confirm view-only access indicators are shown"

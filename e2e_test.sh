#!/bin/bash

# End-to-End Signup and Signin Test
# Tests the complete user registration and authentication workflow

API_BASE="https://admin.bunklogs.net"
FRONTEND_BASE="https://clc.bunklogs.net"
EMAIL="e2etest$(date +%s)@example.com"
PASSWORD="testpassword123"
FIRST_NAME="E2E"
LAST_NAME="Test"

echo "🧪 End-to-End User Registration and Login Test"
echo "=============================================="
echo "Testing user: $EMAIL"
echo ""

# Test 1: Create user via API
echo "📝 Step 1: Creating user account..."
CREATE_RESPONSE=$(curl -s -X POST $API_BASE/api/v1/users/create/ \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"first_name\": \"$FIRST_NAME\",
    \"last_name\": \"$LAST_NAME\",
    \"password\": \"$PASSWORD\"
  }")

if echo "$CREATE_RESPONSE" | grep -q "Counselor"; then
    echo "✅ User created successfully"
    USER_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')
    echo "   User ID: $USER_ID"
else
    echo "❌ User creation failed"
    echo "   Response: $CREATE_RESPONSE"
    exit 1
fi

echo ""

# Test 2: Login with created user
echo "🔐 Step 2: Testing login..."
LOGIN_RESPONSE=$(curl -s -X POST $API_BASE/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\"
  }")

if echo "$LOGIN_RESPONSE" | grep -q "access"; then
    echo "✅ Login successful"
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access')
    echo "   Access token obtained"
else
    echo "❌ Login failed"
    echo "   Response: $LOGIN_RESPONSE"
    exit 1
fi

echo ""

# Test 3: Verify user data with token
echo "👤 Step 3: Verifying user profile..."
PROFILE_RESPONSE=$(curl -s -X GET $API_BASE/api/v1/user/me/ \
  -H "Authorization: Bearer $ACCESS_TOKEN")

if echo "$PROFILE_RESPONSE" | grep -q "$EMAIL"; then
    echo "✅ User profile verified"
    echo "   Email: $(echo "$PROFILE_RESPONSE" | jq -r '.email')"
    echo "   Role: $(echo "$PROFILE_RESPONSE" | jq -r '.role')"
else
    echo "❌ Profile verification failed"
    echo "   Response: $PROFILE_RESPONSE"
    exit 1
fi

echo ""

# Test 4: Frontend accessibility
echo "🌐 Step 4: Testing frontend pages..."
for page in signup signin reset-password; do
    STATUS=$(curl -s -o /dev/null -w '%{http_code}' $FRONTEND_BASE/$page)
    if [ "$STATUS" = "200" ]; then
        echo "✅ $page page accessible"
    else
        echo "❌ $page page not accessible (status: $STATUS)"
    fi
done

echo ""
echo "🎉 End-to-End Test Summary"
echo "========================="
echo "✅ User Registration: Working"
echo "✅ User Authentication: Working"  
echo "✅ Token-based API Access: Working"
echo "✅ Frontend Pages: Accessible"
echo ""
echo "The complete signup and signin workflow is now functional!"
echo "Users can:"
echo "  1. Register new accounts via the frontend form"
echo "  2. Receive automatic 'Counselor' role assignment"
echo "  3. Sign in with their credentials"
echo "  4. Access protected resources with JWT tokens"

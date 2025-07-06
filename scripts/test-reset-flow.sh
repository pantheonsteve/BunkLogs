#!/bin/bash

# Comprehensive password reset test script
set -e

echo "🔄 Starting comprehensive password reset test..."

# Cleanup
rm -f /tmp/session_cookies.txt

echo "🔒 Step 1: Get CSRF token first"
CSRF_TOKEN=$(curl -s -X GET "http://localhost:8000/api/get-csrf-token/" \
  -H "Accept: application/json" \
  -c /tmp/session_cookies.txt | jq -r '.csrfToken')
echo "CSRF token: ${CSRF_TOKEN:0:10}..."

echo "📧 Step 2: Request password reset"
RESET_RESPONSE=$(curl -X POST "http://localhost:8000/_allauth/browser/v1/auth/password/request" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d '{"email": "admin@example.com"}' \
  -b /tmp/session_cookies.txt \
  -c /tmp/session_cookies.txt \
  -s)
echo "Reset response: $RESET_RESPONSE"

echo "⏳ Waiting for email..."
sleep 3

echo "📬 Step 3: Get latest email"
LATEST_EMAIL_ID=$(curl -s -X GET "http://localhost:8025/api/v1/messages" -H "Accept: application/json" | jq -r '.messages[0].ID')
echo "Latest email ID: $LATEST_EMAIL_ID"

echo "🔑 Step 4: Extract reset key"
RESET_KEY=$(curl -s -X GET "http://localhost:8025/api/v1/message/$LATEST_EMAIL_ID" -H "Accept: application/json" | jq -r '.Text' | grep -o 'key/[^[:space:]]*' | sed 's/key\///')
echo "Reset key: $RESET_KEY"

echo "✅ Step 5: Validate reset key"
curl -X GET "http://localhost:8000/_allauth/browser/v1/auth/password/reset" \
  -H "Accept: application/json" \
  -H "X-Password-Reset-Key: $RESET_KEY" \
  -b /tmp/session_cookies.txt \
  -c /tmp/session_cookies.txt \
  -s | jq .

echo "🔄 Step 6: Get fresh CSRF token for reset"
CSRF_TOKEN=$(curl -s -X GET "http://localhost:8000/api/get-csrf-token/" \
  -H "Accept: application/json" \
  -b /tmp/session_cookies.txt \
  -c /tmp/session_cookies.txt | jq -r '.csrfToken')
echo "Fresh CSRF token: ${CSRF_TOKEN:0:10}..."

echo "🔄 Step 7: Reset password"
RESET_FINAL_RESPONSE=$(curl -X POST "http://localhost:8000/_allauth/browser/v1/auth/password/reset" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d "{
    \"key\": \"$RESET_KEY\",
    \"password\": \"newpassword123\",
    \"password_confirm\": \"newpassword123\"
  }" \
  -b /tmp/session_cookies.txt \
  -c /tmp/session_cookies.txt \
  -s)
echo "Final reset response: $RESET_FINAL_RESPONSE"

echo "🎉 Test completed!"

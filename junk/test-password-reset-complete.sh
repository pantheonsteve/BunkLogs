#!/bin/bash

# Complete password reset test with proper session management
set -e

echo "🧪 Starting complete password reset test..."

# Clean up
rm -f /tmp/test_session.txt

echo "🔒 Step 1: Initialize session and get CSRF token"
CSRF_TOKEN=$(curl -s -X GET "http://localhost:8000/api/get-csrf-token/" \
  -H "Accept: application/json" \
  -c /tmp/test_session.txt | jq -r '.csrfToken')
echo "CSRF token: ${CSRF_TOKEN:0:10}..."

echo "📧 Step 2: Request password reset"
RESET_RESPONSE=$(curl -w "%{http_code}" -o /tmp/reset_response.json \
  -X POST "http://localhost:8000/_allauth/browser/v1/auth/password/request" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d '{"email": "admin@example.com"}' \
  -b /tmp/test_session.txt \
  -c /tmp/test_session.txt \
  -s)

echo "Reset request HTTP code: $RESET_RESPONSE"
cat /tmp/reset_response.json
echo ""

if [ "$RESET_RESPONSE" = "200" ]; then
    echo "✅ Password reset request successful"
    
    echo "⏳ Waiting for email..."
    sleep 3
    
    echo "📬 Step 3: Get latest email"
    LATEST_EMAIL_ID=$(curl -s -X GET "http://localhost:8025/api/v1/messages" -H "Accept: application/json" | jq -r '.messages[0].ID')
    echo "Latest email ID: $LATEST_EMAIL_ID"
    
    echo "🔑 Step 4: Extract reset key"
    EMAIL_TEXT=$(curl -s -X GET "http://localhost:8025/api/v1/message/$LATEST_EMAIL_ID" -H "Accept: application/json" | jq -r '.Text')
    echo "Email content preview:"
    echo "$EMAIL_TEXT" | head -5
    
    RESET_KEY=$(echo "$EMAIL_TEXT" | grep -o 'key/[^[:space:]]*' | sed 's/key\///')
    echo "Reset key: $RESET_KEY"
    
    if [ -n "$RESET_KEY" ]; then
        echo "✅ Step 5: Validate reset key"
        VALIDATE_RESPONSE=$(curl -w "%{http_code}" -o /tmp/validate_response.json \
          -X GET "http://localhost:8000/_allauth/browser/v1/auth/password/reset" \
          -H "Accept: application/json" \
          -H "X-Password-Reset-Key: $RESET_KEY" \
          -b /tmp/test_session.txt \
          -c /tmp/test_session.txt \
          -s)
        
        echo "Validate HTTP code: $VALIDATE_RESPONSE"
        cat /tmp/validate_response.json
        echo ""
        
        if [ "$VALIDATE_RESPONSE" = "200" ]; then
            echo "✅ Reset key validation successful"
            
            echo "🔄 Step 6: Get fresh CSRF token for password reset"
            CSRF_TOKEN=$(curl -s -X GET "http://localhost:8000/api/get-csrf-token/" \
              -H "Accept: application/json" \
              -b /tmp/test_session.txt \
              -c /tmp/test_session.txt | jq -r '.csrfToken')
            echo "Fresh CSRF token: ${CSRF_TOKEN:0:10}..."
            
            echo "🔄 Step 7: Reset password"
            FINAL_RESPONSE=$(curl -w "%{http_code}" -o /tmp/final_response.json \
              -X POST "http://localhost:8000/_allauth/browser/v1/auth/password/reset" \
              -H "Accept: application/json" \
              -H "Content-Type: application/json" \
              -H "X-CSRFToken: $CSRF_TOKEN" \
              -d "{
                \"key\": \"$RESET_KEY\",
                \"password\": \"newpassword123\",
                \"password_confirm\": \"newpassword123\"
              }" \
              -b /tmp/test_session.txt \
              -c /tmp/test_session.txt \
              -s)
            
            echo "Final reset HTTP code: $FINAL_RESPONSE"
            cat /tmp/final_response.json
            echo ""
            
            if [ "$FINAL_RESPONSE" = "200" ]; then
                echo "🎉 Password reset completed successfully!"
                
                echo "🧪 Step 8: Test login with new password"
                LOGIN_RESPONSE=$(curl -w "%{http_code}" -o /tmp/login_response.json \
                  -X POST "http://localhost:8000/_allauth/browser/v1/auth/login" \
                  -H "Accept: application/json" \
                  -H "Content-Type: application/json" \
                  -H "X-CSRFToken: $CSRF_TOKEN" \
                  -d '{"email": "admin@example.com", "password": "newpassword123"}' \
                  -b /tmp/test_session.txt \
                  -c /tmp/test_session.txt \
                  -s)
                
                echo "Login test HTTP code: $LOGIN_RESPONSE"
                cat /tmp/login_response.json
                echo ""
                
                if [ "$LOGIN_RESPONSE" = "200" ]; then
                    echo "🎉 Login with new password successful!"
                else
                    echo "❌ Login with new password failed"
                fi
            else
                echo "❌ Password reset failed"
            fi
        else
            echo "❌ Reset key validation failed"
        fi
    else
        echo "❌ Could not extract reset key from email"
    fi
else
    echo "❌ Password reset request failed"
fi

echo "🧽 Cleaning up temp files..."
rm -f /tmp/test_session.txt /tmp/reset_response.json /tmp/validate_response.json /tmp/final_response.json /tmp/login_response.json

echo "🎯 Test completed!"

#!/bin/bash

echo "🚀 Cross-Domain Authentication Fix Deployment Monitor"
echo "===================================================="

echo "✅ Changes pushed to main branch successfully!"
echo ""
echo "📋 Summary of fixes deployed:"
echo "  ✅ Backend: Session cookies now shared across .bunklogs.net subdomains"
echo "  ✅ Backend: CSRF tokens now shared across .bunklogs.net subdomains"
echo "  ✅ Frontend: Cookie handling updated for production domain"
echo "  ✅ Frontend: CSRF token detection for __Secure-csrftoken"
echo ""

echo "🕐 Waiting for GitHub Actions deployment to complete..."
echo "   You can monitor the deployment at:"
echo "   https://github.com/pantheonsteve/BunkLogs/actions"
echo ""

# Wait a bit for deployment to start
sleep 10

echo "🧪 Testing deployment status..."

# Test if the new frontend is deployed
echo "1. Testing if frontend deployment is live..."
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "https://clc.bunklogs.net")
if [ "$FRONTEND_RESPONSE" = "200" ]; then
    echo "   ✅ Frontend is accessible"
else
    echo "   ⚠️  Frontend returned status: $FRONTEND_RESPONSE"
fi

# Test backend endpoints
echo ""
echo "2. Testing backend endpoints..."
CSRF_RESPONSE=$(curl -s -w "%{http_code}" "https://admin.bunklogs.net/api/get-csrf-token/" -o /dev/null)
if [ "$CSRF_RESPONSE" = "200" ]; then
    echo "   ✅ CSRF endpoint is working"
else
    echo "   ❌ CSRF endpoint returned: $CSRF_RESPONSE"
fi

ALLAUTH_RESPONSE=$(curl -s -w "%{http_code}" "https://admin.bunklogs.net/_allauth/browser/v1/config" -o /dev/null)
if [ "$ALLAUTH_RESPONSE" = "200" ]; then
    echo "   ✅ AllAuth config endpoint is working"
else
    echo "   ❌ AllAuth config returned: $ALLAUTH_RESPONSE"
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Wait 2-3 minutes for GitHub Actions to complete frontend deployment"
echo "2. Open https://clc.bunklogs.net/signin in an incognito window"
echo "3. Open browser dev tools (F12) → Network tab"
echo "4. Click 'Sign In With Google' and watch for:"
echo "   - CSRF token requests to admin.bunklogs.net"
echo "   - Cookies being set with .bunklogs.net domain"
echo "   - Successful OAuth redirect flow"
echo ""
echo "🔍 If the fix worked, you should see:"
echo "   ✅ No more 'An unknown error occurred' message"
echo "   ✅ Successful Google sign-in"
echo "   ✅ Redirect to dashboard after authentication"

echo ""
echo "📺 Monitor deployment progress:"
echo "   GitHub Actions: https://github.com/pantheonsteve/BunkLogs/actions"
echo "   Frontend: https://clc.bunklogs.net"
echo "   Backend: https://admin.bunklogs.net"

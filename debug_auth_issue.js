// Debug authentication issue utility
// Run this in the browser console to diagnose the 401 error

function debugAuthIssue() {
  console.log('🔍 === DEBUGGING AUTHENTICATION ISSUE ===');
  
  // Check localStorage tokens
  const accessToken = localStorage.getItem('access_token');
  const refreshToken = localStorage.getItem('refresh_token');
  const userProfile = localStorage.getItem('user_profile');
  
  console.log('📦 LocalStorage Status:', {
    hasAccessToken: !!accessToken,
    hasRefreshToken: !!refreshToken,
    hasUserProfile: !!userProfile,
    accessTokenPreview: accessToken ? accessToken.substring(0, 30) + '...' : 'none',
    refreshTokenPreview: refreshToken ? refreshToken.substring(0, 30) + '...' : 'none'
  });
  
  // Check if access token is expired
  if (accessToken) {
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const isExpired = Date.now() >= payload.exp * 1000;
      console.log('🕒 Token Expiration Check:', {
        exp: new Date(payload.exp * 1000).toISOString(),
        now: new Date().toISOString(),
        isExpired,
        timeUntilExpiry: isExpired ? 'EXPIRED' : `${Math.round((payload.exp * 1000 - Date.now()) / 1000 / 60)} minutes`,
        payload: payload
      });
      
      if (isExpired) {
        console.error('❌ ACCESS TOKEN IS EXPIRED!');
        
        // Check if refresh token is available
        if (refreshToken) {
          console.log('🔄 Refresh token is available, attempting refresh...');
          refreshAccessToken();
        } else {
          console.error('❌ No refresh token available - user needs to log in again');
        }
      }
    } catch (e) {
      console.error('❌ Error parsing access token:', e);
      console.log('Token value:', accessToken);
    }
  } else {
    console.error('❌ NO ACCESS TOKEN FOUND');
  }
  
  // Parse user profile
  if (userProfile) {
    try {
      const profile = JSON.parse(userProfile);
      console.log('👤 User Profile:', profile);
    } catch (e) {
      console.error('❌ Error parsing user profile:', e);
    }
  }
  
  // Test API call to counselor logs endpoint
  testCounselorLogsAPI();
}

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  
  if (!refreshToken) {
    console.error('❌ No refresh token available');
    return false;
  }
  
  try {
    console.log('🔄 Attempting to refresh access token...');
    
    const apiUrl = window.location.origin; // Use current domain
    const response = await fetch(`${apiUrl}/api/auth/token/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh: refreshToken
      })
    });
    
    console.log('🔄 Refresh response status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ Token refresh successful');
      
      // Update access token
      localStorage.setItem('access_token', data.access);
      console.log('💾 New access token stored');
      
      // Test API call again
      testCounselorLogsAPI();
      
      return true;
    } else {
      const errorData = await response.text();
      console.error('❌ Token refresh failed:', response.status, errorData);
      console.log('🚪 User needs to log in again');
      return false;
    }
  } catch (error) {
    console.error('❌ Error during token refresh:', error);
    return false;
  }
}

async function testCounselorLogsAPI() {
  const accessToken = localStorage.getItem('access_token');
  
  if (!accessToken) {
    console.error('❌ Cannot test API - no access token');
    return;
  }
  
  try {
    console.log('🧪 Testing counselor logs API call...');
    
    const apiUrl = window.location.origin; // Use current domain
    const response = await fetch(`${apiUrl}/api/v1/counselorlogs/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    console.log('🧪 API test response status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ API call successful:', data);
    } else {
      const errorData = await response.text();
      console.error('❌ API call failed:', response.status, errorData);
      
      if (response.status === 401) {
        console.error('🚨 401 Unauthorized - Token is invalid or expired');
        console.log('🔄 Try running refreshAccessToken() or user needs to log in again');
      }
    }
  } catch (error) {
    console.error('❌ Error during API test:', error);
  }
}

// Check CSRF token availability
function checkCSRFToken() {
  console.log('🛡️ Checking CSRF token...');
  
  // Check cookies
  const cookies = document.cookie.split(';').reduce((acc, cookie) => {
    const [key, value] = cookie.trim().split('=');
    acc[key] = value;
    return acc;
  }, {});
  
  const csrfFromCookie = cookies['__Secure-csrftoken'] || cookies['csrftoken'];
  
  console.log('🍪 CSRF Token Status:', {
    fromCookie: csrfFromCookie ? 'YES (' + csrfFromCookie.substring(0, 8) + '...)' : 'NO',
    allCookies: Object.keys(cookies)
  });
}

// Run full debug
console.log('🚀 Starting authentication debug...');
debugAuthIssue();
checkCSRFToken();

console.log('📋 Run these functions manually:');
console.log('- debugAuthIssue() - Full auth debug');
console.log('- refreshAccessToken() - Try to refresh token');
console.log('- testCounselorLogsAPI() - Test the API endpoint');
console.log('- checkCSRFToken() - Check CSRF token status');

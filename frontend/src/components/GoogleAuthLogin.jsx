import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const GoogleAuthLogin = ({ onLoginSuccess, buttonText = "Sign in with Google" }) => {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Extract auth code from URL if present (for OAuth callback)
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    const code = urlParams.get('code');
    
    if (code) {
      // We have a code from Google, exchange it for a token
      exchangeCodeForToken(code);
      
      // Clean up the URL to remove the code
      navigate(location.pathname, { replace: true });
    }
  }, [location]);
  
  // Exchange the code for a token with our backend
  const exchangeCodeForToken = async (code) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/auth-token/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies if needed
        body: JSON.stringify({ 
          code,
          redirect_uri: window.location.origin + '/callback'
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      const data = await response.json();
      
      // Store the token in localStorage
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token || '');
      
      // Call the success handler
      if (onLoginSuccess) {
        onLoginSuccess(data);
      }
      
    } catch (error) {
      console.error('Error exchanging code for token:', error);
      // Implement error handling here
    }
  };
  
  // Start the OAuth flow
  const handleLogin = () => {
    // Google OAuth configuration
    const googleAuthUrl = 'https://accounts.google.com/o/oauth2/v2/auth';
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID; // Get from environment variables
    
    // Prepare the OAuth parameters
    const params = new URLSearchParams({
      client_id: clientId,
      redirect_uri: window.location.origin + '/callback', // Must match your Google OAuth settings
      response_type: 'code',
      scope: 'email profile', // Adjust scopes as needed
      access_type: 'offline', // For refresh token
      prompt: 'consent',
    });
    
    // Redirect to Google Auth
    window.location.href = `${googleAuthUrl}?${params.toString()}`;
  };
  
  return (
    <button
      onClick={handleLogin}
      className="flex items-center justify-center gap-2 bg-white text-gray-700 border border-gray-300 rounded-md px-4 py-2 w-full hover:bg-gray-50 transition-colors"
    >
      <svg 
        width="20" 
        height="20" 
        viewBox="0 0 24 24" 
        className="text-gray-900"
      >
        <path
          fill="currentColor"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        />
      </svg>
      {buttonText}
    </button>
  );
};

export default GoogleAuthLogin;
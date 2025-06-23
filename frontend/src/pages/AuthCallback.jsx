// Create: frontend/src/pages/AuthCallback.jsx
import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

function AuthCallback() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [status, setStatus] = useState('processing');
  const hasProcessed = useRef(false); // Prevent multiple executions

  useEffect(() => {
    // Prevent multiple executions
    if (hasProcessed.current) {
      console.log('AuthCallback already processed, skipping...');
      return;
    }

    const handleAuthCallback = async () => {
      try {
        // Mark as processed immediately
        hasProcessed.current = true;

        // Debug: Log the full URL
        console.log('=== AUTH CALLBACK DEBUG ===');
        console.log('Full URL:', window.location.href);
        console.log('Pathname:', window.location.pathname);
        console.log('Search:', window.location.search);
        console.log('Hash:', window.location.hash);
        
        // Get tokens from URL fragment (after #)
        const fragment = window.location.hash.substring(1); // Remove the #
        console.log('Fragment after removing #:', fragment);
        
        // Try both URLSearchParams and manual parsing
        const params = new URLSearchParams(fragment);
        console.log('URLSearchParams entries:');
        for (let [key, value] of params.entries()) {
          console.log(`  ${key}: ${value ? value.substring(0, 20) + '...' : 'empty'}`);
        }
        
        // Manual parsing as backup
        const manualParams = {};
        if (fragment) {
          fragment.split('&').forEach(pair => {
            const [key, value] = pair.split('=');
            if (key && value) {
              manualParams[decodeURIComponent(key)] = decodeURIComponent(value);
            }
          });
        }
        console.log('Manual parsing result:', Object.keys(manualParams));
        
        const accessToken = params.get('access_token') || manualParams['access_token'];
        const refreshToken = params.get('refresh_token') || manualParams['refresh_token'];
        
        console.log('Final tokens found:', { 
          accessToken: accessToken ? 'YES (' + accessToken.substring(0, 20) + '...)' : 'NO',
          refreshToken: refreshToken ? 'YES (' + refreshToken.substring(0, 20) + '...)' : 'NO'
        });

        if (accessToken && refreshToken) {
          console.log('✅ Tokens found, logging in...');
          
          // Clear the URL fragment BEFORE login to prevent issues
          window.history.replaceState({}, document.title, window.location.pathname);
          
          // Login with tokens and wait for completion
          try {
            console.log('Starting login process...');
            const loginResult = await login({
              access_token: accessToken,
              refresh_token: refreshToken,
            });
            
            console.log('Login completed:', loginResult);
            
            // Wait for user profile to be fully loaded
            console.log('Waiting for user profile to load...');
            let attempts = 0;
            const maxAttempts = 50; // 5 seconds max wait
            
            const waitForUserProfile = () => {
              return new Promise((resolve, reject) => {
                const checkUser = () => {
                  attempts++;
                  
                  // Get current auth state
                  const token = localStorage.getItem('access_token');
                  const userProfile = localStorage.getItem('user_profile');
                  
                  console.log(`Profile check attempt ${attempts}:`, {
                    hasToken: !!token,
                    hasProfile: !!userProfile,
                    token: token ? token.substring(0, 20) + '...' : 'none'
                  });
                  
                  if (token && userProfile) {
                    try {
                      const profile = JSON.parse(userProfile);
                      if (profile && profile.id) {
                        console.log('✅ User profile loaded:', profile);
                        resolve(profile);
                        return;
                      }
                    } catch (e) {
                      console.warn('Failed to parse user profile:', e);
                    }
                  }
                  
                  if (attempts >= maxAttempts) {
                    console.warn('⚠️ Timeout waiting for user profile, proceeding anyway');
                    resolve(null);
                    return;
                  }
                  
                  // Try again in 100ms
                  setTimeout(checkUser, 100);
                };
                
                checkUser();
              });
            };
            
            await waitForUserProfile();
            
            setStatus('success');
            
            // Additional delay to ensure all auth state is propagated to React components
            setTimeout(() => {
              console.log('🎯 Redirecting to dashboard with fully loaded profile...');
              navigate('/dashboard', { replace: true });
            }, 1000); // Reduced delay since we already waited for profile
            
          } catch (loginError) {
            console.error('Login failed:', loginError);
            setStatus('error');
            setTimeout(() => {
              navigate('/signin?error=login_failed', { replace: true });
            }, 3000);
          }
        } else {
          console.log('❌ No tokens found, checking for errors...');
          
          // Check for error in query parameters (as fallback)
          const urlParams = new URLSearchParams(window.location.search);
          const error = urlParams.get('auth_error') || urlParams.get('error');
          
          if (error) {
            console.error('Auth error found:', error);
            setStatus('error');
            setTimeout(() => {
              navigate('/signin?error=' + encodeURIComponent(error), { replace: true });
            }, 3000);
          } else {
            console.error('No tokens and no error found');
            setStatus('error');
            setTimeout(() => {
              navigate('/signin?error=no_tokens', { replace: true });
            }, 3000);
          }
        }
      } catch (error) {
        console.error('Auth callback error:', error);
        setStatus('error');
        setTimeout(() => {
          navigate('/signin?error=callback_failed', { replace: true });
        }, 3000);
      }
    };

    // Small delay to ensure URL is fully loaded, but only process once
    const timeoutId = setTimeout(() => {
      handleAuthCallback().catch(error => {
        console.error('Async callback error:', error);
        setStatus('error');
        navigate('/signin?error=callback_failed', { replace: true });
      });
    }, 100);
    
    // Cleanup timeout if component unmounts
    return () => clearTimeout(timeoutId);
  }, []); // Empty dependency array - only run once

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          {status === 'processing' && (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-500 mx-auto"></div>
              <h2 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
                Processing authentication...
              </h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Completing your Google sign in and loading your profile...
              </p>
              <div className="mt-4 text-xs text-gray-500 dark:text-gray-500">
                This may take a few seconds while we set up your dashboard.
              </div>
            </>
          )}
          
          {status === 'success' && (
            <>
              <div className="rounded-full h-12 w-12 bg-green-100 mx-auto flex items-center justify-center">
                <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
                Sign in successful!
              </h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Redirecting to your dashboard...
              </p>
            </>
          )}
          
          {status === 'error' && (
            <>
              <div className="rounded-full h-12 w-12 bg-red-100 mx-auto flex items-center justify-center">
                <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h2 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
                Authentication failed
              </h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Redirecting back to sign in...
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default AuthCallback;
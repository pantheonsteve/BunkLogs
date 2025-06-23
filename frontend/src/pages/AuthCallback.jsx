// Create: frontend/src/pages/AuthCallback.jsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

function AuthCallback() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [status, setStatus] = useState('processing');

  useEffect(() => {
    const handleAuthCallback = () => {
      try {
        // Get tokens from URL fragment (after #)
        const fragment = window.location.hash.substring(1); // Remove the #
        const params = new URLSearchParams(fragment);
        
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        
        console.log('Auth callback params:', { accessToken: !!accessToken, refreshToken: !!refreshToken });

        if (accessToken && refreshToken) {
          // Login with tokens
          login({
            access_token: accessToken,
            refresh_token: refreshToken,
          });

          setStatus('success');
          
          // Clear the URL fragment
          window.history.replaceState({}, document.title, window.location.pathname);
          
          setTimeout(() => {
            navigate('/dashboard');
          }, 1000);
        } else {
          // Check for error in query parameters (as fallback)
          const urlParams = new URLSearchParams(window.location.search);
          const error = urlParams.get('auth_error') || urlParams.get('error');
          
          if (error) {
            console.error('Auth error:', error);
            setStatus('error');
            setTimeout(() => {
              navigate('/signin?error=' + encodeURIComponent(error));
            }, 3000);
          } else {
            console.error('No tokens found in callback');
            setStatus('error');
            setTimeout(() => {
              navigate('/signin?error=no_tokens');
            }, 3000);
          }
        }
      } catch (error) {
        console.error('Auth callback error:', error);
        setStatus('error');
        setTimeout(() => {
          navigate('/signin?error=callback_failed');
        }, 3000);
      }
    };

    handleAuthCallback();
  }, [navigate, login]);

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
                Please wait while we complete your Google sign in.
              </p>
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
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

function CallbackPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [status, setStatus] = useState('processing');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        const state = urlParams.get('state');
        const error = urlParams.get('error');
        const authError = urlParams.get('auth_error');
        const authCancelled = urlParams.get('auth_cancelled');

        // Handle errors first
        if (error || authError) {
          console.error('OAuth error:', error || authError);
          setStatus('error');
          setTimeout(() => {
            navigate('/signin?error=' + encodeURIComponent(error || authError));
          }, 2000);
          return;
        }

        if (authCancelled) {
          console.log('Authentication cancelled by user');
          setStatus('error');
          setTimeout(() => {
            navigate('/signin?cancelled=true');
          }, 2000);
          return;
        }

        // Check if we have an authorization code (main OAuth flow)
        if (code) {
          console.log('Processing OAuth authorization code...');
          
          try {
            // Exchange code for tokens via your backend
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'https://admin.bunklogs.net'}/api/auth/google/callback/`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              credentials: 'include',
              body: JSON.stringify({
                code,
                state,
                redirect_uri: `${window.location.origin}/callback/`
              })
            });

            if (!response.ok) {
              throw new Error(`Backend responded with ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Token exchange successful:', data);
            
            if (data.access_token || data.access) {
              // Store tokens and user data
              const tokens = {
                access_token: data.access_token || data.access,
                refresh_token: data.refresh_token || data.refresh,
                user: data.user
              };
              
              login(tokens);
              setStatus('success');
              
              setTimeout(() => {
                navigate('/dashboard');
              }, 1000);
              return;
            } else {
              throw new Error('No access token received from backend');
            }
          } catch (fetchError) {
            console.error('Token exchange failed:', fetchError);
            setStatus('error');
            setTimeout(() => {
              navigate('/signin?error=token_exchange_failed');
            }, 2000);
            return;
          }
        }

        // Legacy token handling (if tokens are passed directly in URL)
        const token = urlParams.get('token');
        if (token) {
          console.log('Processing direct token from URL...');
          try {
            login({ access_token: token });
            setStatus('success');
            setTimeout(() => {
              navigate('/dashboard');
            }, 1000);
            return;
          } catch (err) {
            console.error('Error processing token:', err);
            setStatus('error');
            setTimeout(() => {
              navigate('/signin?error=token_error');
            }, 2000);
            return;
          }
        }

        // Fallback: Check if allauth handled the authentication automatically
        console.log('Checking for existing authentication...');
        
        // Give allauth some time to process
        setTimeout(async () => {
          try {
            // Check if we're now authenticated by making a test API call
            const testResponse = await fetch(`${import.meta.env.VITE_API_URL || 'https://admin.bunklogs.net'}/api/auth/me/`, {
              credentials: 'include'
            });

            if (testResponse.ok) {
              const userData = await testResponse.json();
              console.log('User authenticated via allauth:', userData);
              
              // Create token object from the authenticated session
              login({ user: userData });
              setStatus('success');
              setTimeout(() => {
                navigate('/dashboard');
              }, 1000);
            } else {
              throw new Error('Authentication check failed');
            }
          } catch (checkError) {
            console.error('Authentication check failed:', checkError);
            setStatus('error');
            setTimeout(() => {
              navigate('/signin?error=callback_failed');
            }, 2000);
          }
        }, 2000);

      } catch (error) {
        console.error('Callback processing error:', error);
        setStatus('error');
        setTimeout(() => {
          navigate('/signin?error=callback_processing_failed');
        }, 2000);
      }
    };

    handleCallback();
  }, [navigate, login]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          {status === 'processing' && (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-500 mx-auto"></div>
              <h2 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
                Processing login...
              </h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Please wait while we complete your authentication.
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
                Login successful!
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

export default CallbackPage;
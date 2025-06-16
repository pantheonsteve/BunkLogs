import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

function CallbackPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  useEffect(() => {
    // Check for tokens in URL params (in case they're passed via URL)
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const error = urlParams.get('error');
    const authError = urlParams.get('auth_error');
    const authCancelled = urlParams.get('auth_cancelled');

    if (error || authError) {
      console.error('Authentication error:', error || authError);
      navigate('/signin?error=' + encodeURIComponent(error || authError));
      return;
    }

    if (authCancelled) {
      console.log('Authentication cancelled by user');
      navigate('/signin?cancelled=true');
      return;
    }

    if (token) {
      // If we have a token in the URL, use it to log in
      try {
        login({ access_token: token });
        navigate('/dashboard');
        return;
      } catch (err) {
        console.error('Error processing token:', err);
        navigate('/signin?error=token_error');
        return;
      }
    }

    // If no specific handling needed, redirect to dashboard after a short delay
    // This gives the allauth library time to process the callback
    const timer = setTimeout(() => {
      // Check if user is now authenticated
      const accessToken = localStorage.getItem('access_token');
      if (accessToken) {
        navigate('/dashboard');
      } else {
        // If still not authenticated, redirect back to signin
        navigate('/signin?error=callback_failed');
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [navigate, login]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-500 mx-auto"></div>
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
            Processing login...
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Please wait while we complete your authentication.
          </p>
        </div>
      </div>
    </div>
  );
}

export default CallbackPage;

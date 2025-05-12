import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const AuthCallback = () => {
  const [status, setStatus] = useState('Processing authentication...');
  const navigate = useNavigate();

  useEffect(() => {
    // Get tokens from URL hash (fragment)
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    
    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');
    
    if (accessToken) {
      // Store tokens in localStorage
      localStorage.setItem('access_token', accessToken);
      if (refreshToken) {
        localStorage.setItem('refresh_token', refreshToken);
      }
      
      setStatus('Authentication successful! Redirecting...');
      
      // Redirect to dashboard
      setTimeout(() => {
        navigate('/');
      }, 1000);
    } else {
      setStatus('Authentication failed. No token received.');
      
      // Redirect to login page after a delay
      setTimeout(() => {
        navigate('/signin');
      }, 2000);
    }
  }, [navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="w-full max-w-md p-8 space-y-8 bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
            Authentication Callback
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            {status}
          </p>
        </div>
      </div>
    </div>
  );
};

export default AuthCallback;
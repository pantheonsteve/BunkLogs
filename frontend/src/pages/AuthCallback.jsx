import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';

const AuthCallback = () => {
  const [status, setStatus] = useState('Processing authentication...');
  const navigate = useNavigate();
  const { login } = useAuth();

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
        navigate('/dashboard');
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
      <div className="p-6 max-w-sm w-full bg-white dark:bg-gray-800 shadow-md rounded-md">
        <div className="flex flex-col items-center">
          <h1 className="text-2xl font-bold text-gray-800 dark:text-white mb-3">Authentication</h1>
          <p className="text-gray-600 dark:text-gray-300">{status}</p>
        </div>
      </div>
    </div>
  );
};

export default AuthCallback;
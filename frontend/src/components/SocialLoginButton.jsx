import React from 'react';

async function testCors() {
    try {
      const response = await fetch('http://localhost:8000/api/test-cors/', {
        method: 'GET',
        credentials: 'include',  // For cookies
      });
      const data = await response.json();
      console.log('CORS test successful:', data);
    } catch (error) {
      console.error('CORS test failed:', error);
    }
  }

const SocialLoginButton = ({ provider = 'google' }) => {
  const handleLogin = () => {
    const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    // Direct to the Google login view
    window.location.href = `${backendUrl}/api/auth/google/`;
    testCors();
    console.log('Login button clicked');
  };

  return (
    <button
      onClick={handleLogin}
      className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 dark:bg-gray-800 dark:border-gray-700/60 dark:text-gray-400 dark:hover:bg-gray-700/20"
    >
      {provider === 'google' && (
        <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032 s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2 C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
        </svg>
      )}
      Sign in with {provider.charAt(0).toUpperCase() + provider.slice(1)}
    </button>
  );
};

export default SocialLoginButton;
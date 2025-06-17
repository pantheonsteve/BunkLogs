import React from 'react';

const DirectGoogleLogin = () => {
  const handleClick = () => {
    // Log what we're doing
    console.log('Initiating direct Google login');
    
    // Directly redirect to Django's social login URL
    const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const callbackUrl = `${window.location.origin}/account/provider/callback`;
    
    console.log('Redirecting to:', `${backendUrl}/accounts/google/login/`);
    console.log('Callback URL:', callbackUrl);
    
    // Perform the redirect
    window.location.href = `${backendUrl}/accounts/google/login/?process=login&next=${encodeURIComponent(callbackUrl)}`;
  };

  return (
    <button 
      onClick={handleClick}
      className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
    >
      Direct Google Login
    </button>
  );
};

export default DirectGoogleLogin;
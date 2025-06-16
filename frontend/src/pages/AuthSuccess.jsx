import React, { useEffect } from 'react';

const AuthSuccess = () => {
  useEffect(() => {
    // User is now authenticated, redirect to dashboard
    window.location.href = '/dashboard';
  }, []);
  
  return <div>Authentication successful, redirecting...</div>;
};

export default AuthSuccess;

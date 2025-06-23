import React from 'react';
import { useAuth } from '../auth/AuthContext';

/**
 * Debug component to help troubleshoot authentication issues
 * Add this temporarily to any dashboard to see auth state
 */
function AuthDebug() {
  const { user, loading, isAuthenticating, isAuthenticated } = useAuth();
  
  if (process.env.NODE_ENV === 'production') {
    return null; // Don't show in production
  }
  
  return (
    <div className="fixed bottom-4 right-4 bg-gray-900 text-white p-4 rounded-lg text-xs max-w-sm z-50">
      <div className="font-bold mb-2">Auth Debug</div>
      <div>Loading: {loading ? 'Yes' : 'No'}</div>
      <div>Authenticating: {isAuthenticating ? 'Yes' : 'No'}</div>
      <div>Authenticated: {isAuthenticated ? 'Yes' : 'No'}</div>
      <div>User ID: {user?.id || 'None'}</div>
      <div>User Role: {user?.role || 'None'}</div>
      <div>User Email: {user?.email || 'None'}</div>
      <div>Token: {localStorage.getItem('access_token') ? 'Present' : 'Missing'}</div>
    </div>
  );
}

export default AuthDebug;

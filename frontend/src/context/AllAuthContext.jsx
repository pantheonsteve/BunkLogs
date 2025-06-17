import React, { createContext, useState, useEffect, useContext } from 'react';
import { getAuth, getConfig } from '../lib/allauth';

const AllAuthContext = createContext(null);

export function AllAuthProvider({ children }) {
  const [auth, setAuth] = useState(null);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Listen for allauth authentication changes
    const handleAuthChange = (event) => {
      console.log('AllAuth auth change event:', event.detail);
      setAuth(event.detail);
    };

    document.addEventListener('allauth.auth.change', handleAuthChange);

    // Initialize auth and config
    const initializeAllAuth = async () => {
      try {
        console.log('AllAuth: Initializing authentication state...');
        console.log('AllAuth: Base URL:', `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/_allauth/browser/v1`);
        
        // Fetch initial auth state and config
        const [authResponse, configResponse] = await Promise.all([
          getAuth().catch(err => {
            console.log('AllAuth: No existing auth session:', err);
            return { status: 401, meta: { is_authenticated: false } };
          }),
          getConfig().catch(err => {
            console.log('AllAuth: Could not fetch config:', err);
            return { data: { socialaccount: { providers: [] } } };
          })
        ]);

        console.log('AllAuth: Auth response:', authResponse);
        console.log('AllAuth: Config response:', configResponse);
        console.log('AllAuth: Providers found:', configResponse?.data?.socialaccount?.providers || []);

        setAuth(authResponse);
        setConfig(configResponse);
      } catch (error) {
        console.error('AllAuth: Error initializing:', error);
        // Set default states on error
        setAuth({ status: 401, meta: { is_authenticated: false } });
        setConfig({ data: { socialaccount: { providers: [] } } });
      } finally {
        console.log('AllAuth: Initialization complete');
        setLoading(false);
      }
    };

    initializeAllAuth();

    return () => {
      document.removeEventListener('allauth.auth.change', handleAuthChange);
    };
  }, []);

  const value = {
    auth,
    config,
    loading,
    isAuthenticated: auth?.meta?.is_authenticated || false,
    user: auth?.data?.user || null,
    providers: config?.data?.socialaccount?.providers || []
  };

  return (
    <AllAuthContext.Provider value={value}>
      {children}
    </AllAuthContext.Provider>
  );
}

export function useAllAuth() {
  const context = useContext(AllAuthContext);
  if (!context) {
    throw new Error('useAllAuth must be used within an AllAuthProvider');
  }
  return context;
}

export function useConfig() {
  const { config, loading } = useAllAuth();
  return { config: config?.data || {}, loading };
}

export function useUser() {
  const { user, loading } = useAllAuth();
  return { user, loading };
}

export default AllAuthContext;

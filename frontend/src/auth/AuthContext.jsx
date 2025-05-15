import React, { createContext, useState, useEffect, useContext } from 'react';
import { jwtDecode } from 'jwt-decode';
import api from '../api';
import { getConfig } from '../lib/allauth';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [config, setConfig] = useState(null);

  // Check for token on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const accessToken = localStorage.getItem('access_token');
        if (!accessToken) {
          setLoading(false);
          return;
        }

        // Validate token and get user data
        try {
          const decoded = jwtDecode(accessToken);
          
          // Check if token is expired
          if (decoded.exp * 1000 < Date.now()) {
            // Try to refresh the token
            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
              const response = await api.post('/api/token/refresh/', {
                refresh: refreshToken
              });
              
              if (response.status === 200) {
                localStorage.setItem('access_token', response.data.access);
                setUser(jwtDecode(response.data.access));
              } else {
                // Failed to refresh, logout
                logout();
              }
            } else {
              logout();
            }
          } else {
            // Token is valid
            setUser(decoded);
          }
        } catch (error) {
          console.error('Token validation error:', error);
          logout();
        }
      } catch (error) {
        setError(error);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  // Load configuration information
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const configResponse = await getConfig();
        if (configResponse && configResponse.status === 200) {
          setConfig(configResponse);
        }
      } catch (error) {
        console.error('Error loading configuration:', error);
      }
    };
    
    loadConfig();
  }, []);

  const login = (tokens) => {
    localStorage.setItem('access_token', tokens.access_token);
    if (tokens.refresh_token) {
      localStorage.setItem('refresh_token', tokens.refresh_token);
    }
    setUser(jwtDecode(tokens.access_token));
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    isAuthenticated: !!user,
    isAuthorized: !!user, // Added for compatibility with existing components
    config
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
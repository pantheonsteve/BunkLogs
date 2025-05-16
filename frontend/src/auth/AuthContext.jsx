import React, { createContext, useState, useEffect, useContext } from 'react';
import { jwtDecode } from 'jwt-decode';
import api from '../api';

const AuthContext = createContext(null);
export { AuthContext }; // Add named export alongside default export

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check for token on mount
  useEffect(() => {
  const checkAuth = async () => {
    try {
      // Check if localStorage is accessible (might not be in incognito with certain browser settings)
      let token = null;
      let storedProfile = null;
      
      try {
        token = localStorage.getItem('access_token');
        storedProfile = localStorage.getItem('user_profile');
        // Test writing to localStorage to verify it's available
        localStorage.setItem('test_storage', 'test');
        localStorage.removeItem('test_storage');
      } catch (storageError) {
        console.error("LocalStorage not available:", storageError);
        // Handle case when localStorage is not available (e.g., incognito mode with restrictions)
        setLoading(false);
        return;
      }
      
      if (token) {
        const decoded = jwtDecode(token);
        console.log('Token found, decoded:', decoded);
        
        // Use stored profile if available, or fetch it
        if (storedProfile) {
          const profile = JSON.parse(storedProfile);
          setUser(profile);
          console.log('User set from stored profile:', profile);
        } else if (decoded.email || decoded.user_id) {
          // Try to fetch by email first, then by user_id if available
          try {
            const endpoint = decoded.email 
              ? `/api/v1/users/email/${decoded.email}/` 
              : `/api/v1/users/${decoded.user_id}/`;
              
            const response = await api.get(endpoint);
            setUser(response.data);
            console.log('User set from API:', response.data);
            try {
              localStorage.setItem('user_profile', JSON.stringify(response.data));
            } catch (e) {
              console.warn('Could not save profile to localStorage:', e);
            }
          } catch (apiError) {
            console.error("Error fetching user data:", apiError);
          }
        }
      }
    } catch (error) {
      console.error("Auth error:", error);
    } finally {
      setLoading(false);
    }
  };
  
  checkAuth();
}, []);

  const login = (tokens) => {
    try {
      // Store tokens in localStorage
      localStorage.setItem('access_token', tokens.access_token);
      if (tokens.refresh_token) {
        localStorage.setItem('refresh_token', tokens.refresh_token);
      }
      
      // If we have a full user profile passed directly, use that
      if (tokens.user_profile) {
        console.log('Setting user from provided profile:', tokens.user_profile);
        setUser(tokens.user_profile);
        return;
      }
      
      // Otherwise decode and set user from token
      const decoded = jwtDecode(tokens.access_token);
      console.log('Login successful, decoded token:', decoded);
      
      // If we have user data in the token, use it
      if (decoded.user_data) {
        setUser(decoded.user_data);
      } else {
        // Try to get user profile from localStorage as a fallback
        const storedProfile = localStorage.getItem('user_profile');
        if (storedProfile) {
          try {
            const profile = JSON.parse(storedProfile);
            setUser(profile);
            console.log('User set from stored profile:', profile);
            return;
          } catch (e) {
            console.warn('Failed to parse stored profile:', e);
          }
        }
        
        // As a last resort, set minimal user info from token
        setUser({
          id: decoded.user_id,
          email: decoded.email,
          name: decoded.name || decoded.email
        });
      }
    } catch (error) {
      console.error("Login error:", error);
      // Even if localStorage fails, we can still set the user in memory
      try {
        const decoded = jwtDecode(tokens.access_token);
        setUser({
          id: decoded.user_id,
          email: decoded.email,
          name: decoded.name || decoded.email
        });
      } catch (decodeError) {
        console.error("Failed to decode token:", decodeError);
      }
    }
  };

  const logout = () => {
    try {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user_profile');
    } catch (error) {
      console.error("Logout localStorage error:", error);
    }
    setUser(null);
  };

  const value = {
    user,
    setUser, // Expose setUser for direct profile updates
    loading,
    error,
    login,
    logout,
    isAuthenticated: !!user
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  // Enhanced context with additional helper methods
  return {
    ...context,
    // Get user profile or an empty object
    userProfile: context.user || {},
    // Convenience method to update user profile
    updateUserProfile: (profileData) => {
      if (!context.user) return; // Don't update if no user exists
      
      // Merge existing user data with new profile data
      const updatedProfile = { ...context.user, ...profileData };
      context.setUser(updatedProfile);
      
      // Update localStorage if available
      try {
        localStorage.setItem('user_profile', JSON.stringify(updatedProfile));
      } catch (e) {
        console.warn('Could not save updated profile to localStorage:', e);
      }
    }
  };
}

export default AuthContext;
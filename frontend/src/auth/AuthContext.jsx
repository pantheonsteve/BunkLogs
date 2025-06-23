import React, { createContext, useState, useEffect, useContext } from 'react';
import { jwtDecode } from 'jwt-decode';
import api from '../api';

const AuthContext = createContext(null);
export { AuthContext }; // Add named export alongside default export

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false); // New state for active auth process

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

  const login = async (tokens) => {
    setIsAuthenticating(true); // Set authenticating state
    try {
      console.log('🔐 Starting login process with tokens');
      
      // Store tokens in localStorage first
      localStorage.setItem('access_token', tokens.access_token);
      if (tokens.refresh_token) {
        localStorage.setItem('refresh_token', tokens.refresh_token);
      }
      
      // If we have a user object directly from the API response (username/password login)
      if (tokens.user) {
        console.log('Setting user from API response:', tokens.user);
        setUser(tokens.user);
        // Also store in localStorage
        localStorage.setItem('user_profile', JSON.stringify(tokens.user));
        return tokens.user;
      }
      
      // If we have a full user profile passed directly (social login), use that
      if (tokens.user_profile) {
        console.log('Setting user from provided profile:', tokens.user_profile);
        setUser(tokens.user_profile);
        localStorage.setItem('user_profile', JSON.stringify(tokens.user_profile));
        return tokens.user_profile;
      }
      
      // For social login tokens, we need to fetch the user profile
      console.log('🔍 Fetching user profile from token...');
      const decoded = jwtDecode(tokens.access_token);
      console.log('Decoded token:', decoded);
      
      // Try to fetch user profile immediately after login
      let userProfile = null;
      
      if (decoded.email || decoded.user_id) {
        try {
          const endpoint = decoded.email 
            ? `/api/v1/users/email/${decoded.email}/` 
            : `/api/v1/users/${decoded.user_id}/`;
            
          console.log(`📡 Fetching user profile from ${endpoint}`);
          const response = await api.get(endpoint);
          userProfile = response.data;
          
          console.log('✅ User profile fetched:', userProfile);
          setUser(userProfile);
          localStorage.setItem('user_profile', JSON.stringify(userProfile));
          
          return userProfile;
          
        } catch (apiError) {
          console.error("❌ Error fetching user profile:", apiError);
          // Fall back to token data
        }
      }
      
      // If we have user data in the token, use it as fallback
      if (decoded.user_data) {
        userProfile = decoded.user_data;
        setUser(userProfile);
        localStorage.setItem('user_profile', JSON.stringify(userProfile));
        return userProfile;
      }
      
      // Try to get user profile from localStorage as a fallback
      const storedProfile = localStorage.getItem('user_profile');
      if (storedProfile) {
        try {
          const profile = JSON.parse(storedProfile);
          setUser(profile);
          console.log('📁 User set from stored profile:', profile);
          return profile;
        } catch (e) {
          console.warn('Failed to parse stored profile:', e);
        }
      }
      
      // As a last resort, set minimal user info from token
      userProfile = {
        id: decoded.user_id,
        email: decoded.email,
        name: decoded.name || decoded.email,
        role: decoded.role || 'Counselor'
      };
      
      setUser(userProfile);
      localStorage.setItem('user_profile', JSON.stringify(userProfile));
      console.log('⚠️ Using minimal user profile from token:', userProfile);
      
      return userProfile;
      
    } catch (error) {
      console.error("❌ Login error:", error);
      
      // Even if everything fails, try to set something from the token
      try {
        const decoded = jwtDecode(tokens.access_token);
        const fallbackUser = {
          id: decoded.user_id,
          email: decoded.email,
          name: decoded.name || decoded.email,
          role: decoded.role || 'Counselor'
        };
        setUser(fallbackUser);
        localStorage.setItem('user_profile', JSON.stringify(fallbackUser));
        return fallbackUser;
      } catch (decodeError) {
        console.error("Failed to decode token:", decodeError);
        throw new Error('Failed to process login tokens');
      }
    } finally {
      setIsAuthenticating(false); // Clear authenticating state
    }
  };

  const logout = async () => {
    try {
      // Try to call the logout endpoint if it exists
      // This will fail silently if the endpoint doesn't exist or there's no token
      try {
        const token = localStorage.getItem('access_token');
        if (token) {
          await api.post('/api/logout/', {}, {
            headers: { Authorization: `Bearer ${token}` }
          }).catch(e => console.log('Logout API call failed, proceeding with local logout'));
        }
      } catch (apiError) {
        // Continue with local logout even if API call fails
        console.log('API logout attempt failed:', apiError);
      }
      
      // Clear all auth data from localStorage
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user_profile');
      
      // Also clear any other potential auth-related items
      localStorage.removeItem('auth_state');
      
      // Clear user from state
      setUser(null);
      
      console.log('User successfully logged out');
    } catch (error) {
      console.error("Logout error:", error);
      // Even if localStorage fails, still reset the user state
      setUser(null);
    }
  };

  // Get token directly from localStorage
  const token = localStorage.getItem('access_token');
  
  const value = {
    user,
    setUser, // Expose setUser for direct profile updates
    loading,
    isAuthenticating, // Expose the authenticating state
    error,
    login,
    logout,
    isAuthenticated: !!user,
    token // Expose token directly in the context
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
    // Add token directly from localStorage
    token: localStorage.getItem('access_token'),
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
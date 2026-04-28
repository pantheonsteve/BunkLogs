import axios from 'axios';
import { getCSRFToken } from './django';

// Get and clean the API URL
const getApiUrl = () => {
  let url = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  // Remove any quotes and trim whitespace
  url = url.replace(/['"]/g, '').trim();
  // Ensure it has a protocol
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = url.includes('localhost') ? `http://${url}` : `https://${url}`;
  }
  return url;
};

const apiUrl = getApiUrl();
console.log('API URL configured as:', apiUrl);

const api = axios.create({
  baseURL: apiUrl,
  withCredentials: true, // Important for cookies
});

// Function to get CSRF token from the server
const getServerCSRFToken = async () => {
  try {
    const response = await api.get('/api/get-csrf-token/');
    return response.data.csrfToken;
  } catch (error) {
    console.warn('Failed to get CSRF token from server:', error);
    return null;
  }
};

// Add request interceptor to attach token and CSRF token
api.interceptors.request.use(
  async (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add CSRF token for non-GET requests (except user creation)
    if (config.method !== 'get' && !config.url.includes('/users/create/')) {
      // First try to get CSRF token from cookie
      let csrfToken = getCSRFToken();
      console.log('CSRF token from cookie:', csrfToken);
      
      // If no cookie token, get it from the server
      if (!csrfToken) {
        console.log('Getting CSRF token from server...');
        csrfToken = await getServerCSRFToken();
        console.log('CSRF token from server:', csrfToken);
      }
      
      if (csrfToken) {
        config.headers['x-csrftoken'] = csrfToken;
        console.log('Added CSRF token to request headers');
      } else {
        console.warn('No CSRF token available for request');
      }
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Enhanced error logging for 401 errors
    if (error.response?.status === 401) {
      console.error('🚨 401 Authentication Error:', {
        url: originalRequest.url,
        method: originalRequest.method,
        hasAuthHeader: !!originalRequest.headers?.Authorization,
        authHeaderPreview: originalRequest.headers?.Authorization?.substring(0, 20) + '...',
        errorData: error.response?.data,
        timestamp: new Date().toISOString()
      });
      
      // Check if token exists and if it's expired
      const accessToken = localStorage.getItem('access_token');
      if (accessToken) {
        try {
          const payload = JSON.parse(atob(accessToken.split('.')[1]));
          const isExpired = Date.now() >= payload.exp * 1000;
          console.error('🔍 Token analysis:', {
            hasToken: true,
            isExpired,
            exp: new Date(payload.exp * 1000).toISOString(),
            now: new Date().toISOString()
          });
        } catch (e) {
          console.error('❌ Error parsing stored token:', e);
        }
      } else {
        console.error('❌ No access token in localStorage');
      }
    } else {
      console.log('API Error:', error.response?.status, error.response?.data);
    }
    
    // If the error is due to an expired/invalid token (401) and we haven't
    // already retried, attempt one refresh + retry. If anything in this path
    // fails (or there's no refresh token at all), clear local auth state and
    // bounce the user to /signin so they aren't stuck on a broken page with a
    // generic "failed to load" message.
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const redirectToSignin = () => {
        try {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user_profile');
        } catch (_) {
          // Ignore localStorage failures (e.g. private browsing).
        }
        // Avoid redirect loops if we're already on the signin page.
        if (typeof window !== 'undefined'
            && window.location
            && !window.location.pathname.startsWith('/signin')) {
          window.location.href = '/signin?session_expired=1';
        }
      };

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        console.warn('🔒 401 with no refresh token — redirecting to /signin');
        redirectToSignin();
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(`${apiUrl}/api/auth/token/refresh/`, {
          refresh: refreshToken,
        });

        if (response.status === 200 && response.data?.access) {
          localStorage.setItem('access_token', response.data.access);
          if (response.data.refresh) {
            localStorage.setItem('refresh_token', response.data.refresh);
          }
          originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
          return axios(originalRequest);
        }

        // Refresh returned 2xx but didn't include an access token — treat as failure.
        console.warn('🔒 Token refresh returned no access token — redirecting to /signin');
        redirectToSignin();
        return Promise.reject(error);
      } catch (refreshError) {
        console.warn('🔒 Token refresh failed — redirecting to /signin', refreshError?.response?.status);
        redirectToSignin();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Helper functions for common API operations

// Safely fetch staff assignment - returns null if user doesn't have assignment (e.g., admin)
export const fetchStaffAssignmentSafe = async (userId) => {
  try {
    const response = await api.get(`/api/v1/unit-staff-assignments/${userId}/`);
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      // User doesn't have staff assignment - likely admin
      console.log('No staff assignment found for user - likely admin or user without assignment');
      return null;
    }
    throw error;
  }
};

// Get appropriate date range based on user role
export const getDateRangeForUser = (user) => {
  // Use local timezone date to avoid off-by-one errors
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  const todayStr = `${year}-${month}-${day}`;
  
  // For admin users and camper care team, allow a broader range
  if (user?.role === 'Admin' || user?.role === 'Camper Care' || user?.is_staff === true || user?.is_superuser === true) {
    const startOfYearStr = `${year}-01-01`;
    return {
      start_date: startOfYearStr,
      end_date: null // Allow all dates including future for full access
    };
  }
  
  // For regular users, be more restrictive
  return {
    start_date: todayStr,
    end_date: null
  };
};

export default api;
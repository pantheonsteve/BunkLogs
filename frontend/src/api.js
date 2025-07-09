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

    console.log('API Error:', error.response?.status, error.response?.data);
    
    // If the error is due to an expired token (401) and we haven't tried to refresh yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          // No refresh token available, just reject
          return Promise.reject(error);
        }
        
        // Try to refresh the token
        const response = await axios.post(`${apiUrl}/api/auth/token/refresh/`, {
          refresh: refreshToken
        });
        
        if (response.status === 200) {
          // Update tokens
          localStorage.setItem('access_token', response.data.access);
          
          // Retry the original request with the new token
          originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
          return axios(originalRequest);
        }
      } catch (refreshError) {
        // If refresh fails, redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/signin';
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

// Check user role/permissions
export const checkUserRole = async () => {
  try {
    const response = await api.get('/api/auth/user/');
    return response.data;
  } catch (error) {
    console.error('Error checking user role:', error);
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
  
  // For admin users, allow a broader range
  if (user?.role === 'Admin' || user?.is_staff === true || user?.is_superuser === true) {
    const startOfYearStr = `${year}-01-01`;
    return {
      start_date: startOfYearStr,
      end_date: todayStr
    };
  }
  
  // For regular users, be more restrictive
  return {
    start_date: todayStr,
    end_date: null
  };
};

export default api;
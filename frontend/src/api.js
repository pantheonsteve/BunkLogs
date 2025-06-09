import axios from 'axios';
import { getCSRFToken } from './django';

const apiUrl = import.meta.env.VITE_API_URL || 'https://admin.bunklogs.net';

const api = axios.create({
  baseURL: apiUrl,
  withCredentials: true, // Important for cookies
});

// Function to get CSRF token from the server
const getServerCSRFToken = async () => {
  try {
    const response = await axios.get(`${apiUrl}/api/get-csrf-token/`, {
      withCredentials: true
    });
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

export default api;
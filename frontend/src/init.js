import { setup } from './lib/allauth'

// Import the CSRF token functions to ensure they're available
let cachedCSRFToken = null;

import { datadogRum } from '@datadog/browser-rum';
import { reactPlugin } from '@datadog/browser-rum-react';

datadogRum.init({
    applicationId: '06f040c0-8a9c-4ca0-865c-9ad82ae138a0',
    clientToken: 'pub61357afeab81d99906c5d9ddf48dfaf5',
    site: 'datadoghq.com',
    service:'bunlogs-frontend',
    env: 'prod',
    
    // Specify a version number to identify the deployed version of your application in Datadog
    // version: '1.0.0',
    sessionSampleRate:  100,
    sessionReplaySampleRate: 20,
    defaultPrivacyLevel: 'mask-user-input',
    plugins: [reactPlugin({ router: true })],
});

export async function init() {
  console.log('Initializing application...');
  
  // Get the backend URL from environment variables
  const getBackendUrl = () => {
    const envUrl = import.meta.env.VITE_API_URL;
    if (envUrl) {
      // If env URL already has protocol, use it as-is
      if (envUrl.startsWith('http://') || envUrl.startsWith('https://')) {
        return envUrl;
      }
      // If no protocol, assume https for production domains, http for localhost
      return envUrl.includes('localhost') ? `http://${envUrl}` : `https://${envUrl}`;
    }
    // Default fallback
    return "http://localhost:8000";
  };

  const backendUrl = getBackendUrl();
  const baseUrl = `${backendUrl}/_allauth/browser/v1`;
  
  // Configure allauth with proper backend URL and credentials
  setup('browser', baseUrl, true);
  
  // Pre-fetch CSRF token to ensure it's available for subsequent requests
  try {
    const response = await fetch(`${backendUrl}/api/get-csrf-token/`, {
      credentials: 'include'
    });
    if (response.ok) {
      const data = await response.json();
      cachedCSRFToken = data.csrfToken;
      console.log('CSRF token pre-fetched during initialization:', cachedCSRFToken.substring(0, 8) + '...');
      
      // Set a cookie so the django.js getCSRFToken function can find it
      // Use production cookie name and domain settings for cross-subdomain access
      const isProduction = window.location.hostname.includes('bunklogs.net');
      if (isProduction) {
        // Production: use secure cookie with domain sharing
        document.cookie = `__Secure-csrftoken=${data.csrfToken}; path=/; domain=.bunklogs.net; SameSite=Lax; Secure`;
      } else {
        // Development: use standard cookie
        document.cookie = `csrftoken=${data.csrfToken}; path=/; SameSite=Lax`;
      }
    }
  } catch (error) {
    console.warn('Failed to pre-fetch CSRF token during initialization:', error);
  }
  
  console.log('Allauth initialized with:', {
    client: 'browser',
    baseUrl,
    withCredentials: true
  });
}
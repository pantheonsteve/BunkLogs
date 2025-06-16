import { setup } from './lib/allauth'

export function init() {
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
  
  console.log('Allauth initialized with:', {
    client: 'browser',
    baseUrl,
    withCredentials: true
  });
}
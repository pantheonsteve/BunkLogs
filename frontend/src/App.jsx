import { useState, useEffect } from 'react';
import { AuthProvider } from './auth/AuthContext';
import { AllAuthProvider } from './context/AllAuthContext';
import { BunkProvider } from './contexts/BunkContext';
import { useThemeProvider } from './utils/ThemeContext';
import Router from './Router';
import './css/style.css';

import { datadogRum } from '@datadog/browser-rum';
import { reactPlugin } from '@datadog/browser-rum-react';

// Initialize Datadog RUM
const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;
const environment = import.meta.env.VITE_DATADOG_ENV || (isProduction ? 'production' : 'development');

console.log('🔍 Datadog RUM Environment Check:', {
  isDevelopment,
  isProduction,
  environment,
  hasAppId: !!import.meta.env.VITE_DATADOG_APPLICATION_ID,
  hasClientToken: !!import.meta.env.VITE_DATADOG_CLIENT_TOKEN,
  apiUrl: import.meta.env.VITE_API_URL,
});

// Initialize Datadog RUM if we have the required configuration
if (import.meta.env.VITE_DATADOG_APPLICATION_ID && import.meta.env.VITE_DATADOG_CLIENT_TOKEN) {
  try {
    datadogRum.init({
      applicationId: import.meta.env.VITE_DATADOG_APPLICATION_ID,
      clientToken: import.meta.env.VITE_DATADOG_CLIENT_TOKEN,
      site: import.meta.env.VITE_DATADOG_SITE || 'datadoghq.com',
      service: import.meta.env.VITE_DATADOG_SERVICE || 'bunklogs-frontend',
      env: environment,
      version: import.meta.env.VITE_DATADOG_VERSION || '1.0.0',
      
      // Sampling rates - optimized for production
      sessionSampleRate: 100,
      sessionReplaySampleRate: 20, // Reduced from 98% to save costs
      
      // Privacy settings - better for user privacy
      defaultPrivacyLevel: 'mask-user-input', // More secure than 'allow'
      
      // Performance tracking
      trackUserInteractions: true,
      trackResources: true,
      trackLongTasks: true,
      
      // Enable distributed tracing between frontend and backend
      allowedTracingUrls: [
        // Track API calls to your backend for full-stack traces
        (url) => {
          const apiUrl = import.meta.env.VITE_API_URL;
          return apiUrl && url.startsWith(apiUrl);
        },
      ],
      
      // React-specific plugin
      plugins: [reactPlugin({ router: true })],
    });
    
    console.log('✅ Datadog RUM initialized successfully:', {
      applicationId: import.meta.env.VITE_DATADOG_APPLICATION_ID?.slice(0, 8) + '...',
      service: import.meta.env.VITE_DATADOG_SERVICE,
      environment,
      version: import.meta.env.VITE_DATADOG_VERSION,
      tracingEnabled: !!import.meta.env.VITE_API_URL,
    });

    // Send initialization event
    datadogRum.addAction('datadog_rum_initialized', {
      timestamp: Date.now(),
      environment,
      version: import.meta.env.VITE_DATADOG_VERSION || '1.0.0',
      userAgent: navigator.userAgent.substring(0, 100), // Truncated for privacy
    });
    
  } catch (error) {
    console.error('❌ Failed to initialize Datadog RUM:', error);
  }
} else {
  console.log('⚠️ Datadog RUM not initialized - missing configuration:', {
    hasAppId: !!import.meta.env.VITE_DATADOG_APPLICATION_ID,
    hasClientToken: !!import.meta.env.VITE_DATADOG_CLIENT_TOKEN,
    environment,
  });
}

function App() {
  const [appReady, setAppReady] = useState(false);
  const { themeLoaded } = useThemeProvider();

  useEffect(() => {
    // Wait for theme to be loaded before showing the app
    if (themeLoaded) {
      // Add a small delay to ensure CSS variables are fully applied
      const timer = setTimeout(() => {
        setAppReady(true);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [themeLoaded]);

  if (!appReady) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-500 mx-auto"></div>
          <p className="mt-3 text-gray-700 dark:text-gray-300">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <AllAuthProvider>
      <AuthProvider>
        <BunkProvider>
          <Router />
        </BunkProvider>
      </AuthProvider>
    </AllAuthProvider>
  );
}

export default App;
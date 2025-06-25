import { useState, useEffect } from 'react';
import { AuthProvider } from './auth/AuthContext';
import { AllAuthProvider } from './context/AllAuthContext';
import { BunkProvider } from './contexts/BunkContext';
import { useThemeProvider } from './utils/ThemeContext';
import Router from './Router';
import './css/style.css';

import { datadogRum } from '@datadog/browser-rum';
import { reactPlugin } from '@datadog/browser-rum-react';

datadogRum.init({
    applicationId: 'b9ea1bc9-4292-4a87-ac04-c6299ff6f2e8',
    clientToken: 'puba04f5160f90ae85243fa0ac315411d27',
    site: 'datadoghq.com',
    service:'bunklogs-frontend',
    env: 'prod',
    
    // Specify a version number to identify the deployed version of your application in Datadog
    // version: '1.0.0',
    sessionSampleRate:  100,
    sessionReplaySampleRate: 100,
    defaultPrivacyLevel: 'mask-user-input',
    plugins: [reactPlugin({ router: true })],
});

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
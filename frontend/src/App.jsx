import { useState, useEffect } from 'react';
import { ErrorBoundary } from '@datadog/browser-rum-react';
import { AuthProvider } from './auth/AuthContext';
import { AllAuthProvider } from './context/AllAuthContext';
import { BunkProvider } from './contexts/BunkContext';
import SubmissionQueueProvider from './lib/submissionQueue/SubmissionQueueProvider';
import { useThemeProvider } from './utils/ThemeContext';
import Router from './Router';
import './css/style.css';

function AppErrorFallback({ resetError, error }) {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="text-center max-w-md px-4">
        <p className="text-gray-700 dark:text-gray-300">
          Something went wrong.{' '}
          <strong className="block mt-2 text-sm">{String(error)}</strong>
        </p>
        <button
          type="button"
          onClick={resetError}
          className="mt-4 px-4 py-2 bg-violet-500 text-white rounded hover:bg-violet-600"
        >
          Retry
        </button>
      </div>
    </div>
  );
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
    <ErrorBoundary fallback={AppErrorFallback}>
      <AllAuthProvider>
        <AuthProvider>
          <SubmissionQueueProvider>
            <BunkProvider>
              <Router />
            </BunkProvider>
          </SubmissionQueueProvider>
        </AuthProvider>
      </AllAuthProvider>
    </ErrorBoundary>
  );
}

export default App;
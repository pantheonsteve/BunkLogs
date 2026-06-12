import React from 'react';
import { createRoot } from 'react-dom/client';
import { addReactError } from '@datadog/browser-rum-react';
import { initDatadogRum, waitForDatadogSession } from './lib/datadog';
import ThemeProvider from './utils/ThemeContext';
import App from './App';

import { init } from './init';

function renderApp() {
  try {
    const rootElement = document.getElementById('root');
    if (!rootElement) {
      console.error('Root element not found');
      return;
    }

    const root = createRoot(rootElement, {
      onUncaughtError: (error, errorInfo) => {
        addReactError(error, errorInfo);
        console.error('Uncaught error:', error, errorInfo);
      },
      onCaughtError: (error, errorInfo) => {
        addReactError(error, errorInfo);
        console.error('Caught error:', error, errorInfo);
      },
      onRecoverableError: (error, errorInfo) => {
        addReactError(error, errorInfo);
        console.warn('Recoverable error:', error, errorInfo);
      },
    });

    root.render(
      <React.StrictMode>
        <ThemeProvider>
          <App />
        </ThemeProvider>
      </React.StrictMode>
    );
    console.log('App rendered successfully');
  } catch (error) {
    console.error('Error rendering the app:', error);
  }
}

async function bootstrap() {
  initDatadogRum();
  await waitForDatadogSession();

  if (document.readyState === 'loading') {
    await new Promise((resolve) => {
      document.addEventListener('DOMContentLoaded', resolve, { once: true });
    });
  }

  renderApp();

  try {
    await init();
    console.log('App initialization completed');
  } catch (error) {
    console.error('App initialization failed:', error);
  }
}

bootstrap();

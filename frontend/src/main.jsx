import React from 'react';
import ReactDOM from 'react-dom/client';
import { initDatadogRum, waitForDatadogSession } from './lib/datadog';
import ThemeProvider from './utils/ThemeContext';
import App from './App';

import { init } from './init';

// Create a function to safely render the app after DOM is ready
function renderApp() {
  try {
    const rootElement = document.getElementById('root');
    if (!rootElement) {
      console.error('Root element not found');
      return;
    }

    ReactDOM.createRoot(rootElement).render(
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

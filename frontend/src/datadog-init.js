import { datadogRum } from '@datadog/browser-rum';
import { reactPlugin } from '@datadog/browser-rum-react';

const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;
const environment = import.meta.env.VITE_DATADOG_ENV || (isProduction ? 'production' : 'development');

console.log('🔍 Datadog Environment Check:', {
  isDevelopment,
  isProduction,
  environment,
  hasAppId: !!import.meta.env.VITE_DATADOG_APPLICATION_ID,
  hasClientToken: !!import.meta.env.VITE_DATADOG_CLIENT_TOKEN,
  nodeEnv: import.meta.env.NODE_ENV,
  mode: import.meta.env.MODE
});

if ((isProduction || import.meta.env.VITE_DATADOG_FORCE_ENABLE) && import.meta.env.VITE_DATADOG_APPLICATION_ID) {
  try {
    datadogRum.init({
      applicationId: import.meta.env.VITE_DATADOG_APPLICATION_ID,
      clientToken: import.meta.env.VITE_DATADOG_CLIENT_TOKEN,
      site: import.meta.env.VITE_DATADOG_SITE || 'datadoghq.com',
      service: import.meta.env.VITE_DATADOG_SERVICE || 'bunklogs-frontend',
      env: environment,
      version: import.meta.env.VITE_DATADOG_VERSION || '1.0.0',
      sessionSampleRate: 100,
      sessionReplaySampleRate: 20,
      defaultPrivacyLevel: 'mask-user-input',
      trackUserInteractions: true,
      trackResources: true,
      trackLongTasks: true,
      allowedTracingUrls: [
        (url) => url.startsWith(import.meta.env.VITE_API_URL),
      ],
      plugins: [reactPlugin({ router: true })],
    });

    console.log('✅ Datadog RUM initialized successfully:', {
      environment,
      service: import.meta.env.VITE_DATADOG_SERVICE || 'bunklogs-frontend',
      version: import.meta.env.VITE_DATADOG_VERSION || '1.0.0'
    });

    console.log('VITE env at runtime:', {
      VITE_DATADOG_APPLICATION_ID: import.meta.env.VITE_DATADOG_APPLICATION_ID,
      VITE_DATADOG_CLIENT_TOKEN: import.meta.env.VITE_DATADOG_CLIENT_TOKEN,
      VITE_DATADOG_SITE: import.meta.env.VITE_DATADOG_SITE,
      VITE_DATADOG_SERVICE: import.meta.env.VITE_DATADOG_SERVICE,
      VITE_DATADOG_ENV: import.meta.env.VITE_DATADOG_ENV,
      VITE_DATADOG_VERSION: import.meta.env.VITE_DATADOG_VERSION,
      VITE_API_URL: import.meta.env.VITE_API_URL,
      MODE: import.meta.env.MODE,
    });

    datadogRum.addAction('datadog_rum_initialized', {
      timestamp: Date.now(),
      environment,
      userAgent: navigator.userAgent
    });
  } catch (error) {
    console.error('❌ Failed to initialize Datadog RUM:', error);
  }
} else {
  console.log('⚠️ Datadog RUM not initialized:', {
    reason: !isProduction && !import.meta.env.VITE_DATADOG_FORCE_ENABLE 
      ? 'Not in production mode' 
      : 'Missing configuration',
    isProduction,
    hasAppId: !!import.meta.env.VITE_DATADOG_APPLICATION_ID,
    hasClientToken: !!import.meta.env.VITE_DATADOG_CLIENT_TOKEN
  });
}

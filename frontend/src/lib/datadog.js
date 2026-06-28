import { datadogRum } from '@datadog/browser-rum';
import { datadogLogs } from '@datadog/browser-logs';
import { reactPlugin } from '@datadog/browser-rum-react';
import { resolveOrganizationSlug } from '../utils/orgSlug';

let rumInitialized = false;
let logsInitialized = false;

function normalizeApiUrl(url) {
  if (!url) return null;
  let normalized = url.replace(/['"]/g, '').trim();
  if (!normalized.startsWith('http://') && !normalized.startsWith('https://')) {
    normalized = normalized.includes('localhost') ? `http://${normalized}` : `https://${normalized}`;
  }
  return normalized.replace(/\/$/, '');
}

function shouldEnableDatadog() {
  const hasCredentials =
    import.meta.env.VITE_DATADOG_APPLICATION_ID &&
    import.meta.env.VITE_DATADOG_CLIENT_TOKEN;

  if (!hasCredentials) return false;

  return import.meta.env.PROD || import.meta.env.VITE_DATADOG_FORCE_ENABLE === 'true';
}

function getDatadogConfig() {
  const environment =
    import.meta.env.VITE_DATADOG_ENV ||
    (import.meta.env.PROD ? 'prod' : 'development');

  return {
    applicationId: import.meta.env.VITE_DATADOG_APPLICATION_ID,
    clientToken: import.meta.env.VITE_DATADOG_CLIENT_TOKEN,
    site: import.meta.env.VITE_DATADOG_SITE || 'datadoghq.com',
    service: import.meta.env.VITE_DATADOG_SERVICE || 'bunklogs-frontend',
    env: environment,
    version: import.meta.env.VITE_DATADOG_VERSION || '1.0.0',
  };
}

export function isDatadogRumEnabled() {
  return rumInitialized;
}

export function isDatadogLogsEnabled() {
  return logsInitialized;
}

/**
 * reactPlugin({ router: true }) enables trackViewsManually, so RUM does not
 * trace API calls until a view exists. Bootstrap network calls (CSRF prefetch,
 * auth) run before React mounts Routes — start the current path immediately.
 */
export function startInitialDatadogView() {
  if (!rumInitialized) return;

  const path = window.location.pathname || '/';
  datadogRum.startView({ name: path });
}

export async function waitForDatadogSession(timeoutMs = 5000) {
  if (!shouldEnableDatadog()) return;

  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (datadogRum.getInternalContext?.()?.session_id) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
}

export function initDatadogRum() {
  if (rumInitialized || !shouldEnableDatadog()) {
    return;
  }

  const config = getDatadogConfig();

  try {
    datadogRum.init({
      applicationId: config.applicationId,
      clientToken: config.clientToken,
      site: config.site,
      service: config.service,
      env: config.env,
      version: config.version,
      sessionSampleRate: 100,
      sessionReplaySampleRate: 100,
      traceSampleRate: 100,
      traceContextInjection: 'all',
      defaultPrivacyLevel: 'mask-user-input',
      trackUserInteractions: true,
      trackResources: true,
      trackLongTasks: true,
      trackSessionAcrossSubdomains: true,
      trackingConsent: 'granted',
      silentMultipleInit: true,
      allowedTracingUrls: [
        {
          match: normalizeApiUrl(import.meta.env.VITE_API_URL) || 'https://admin.bunklogs.net',
          propagatorTypes: ['datadog', 'tracecontext'],
        },
        {
          match: 'http://localhost:8000',
          propagatorTypes: ['datadog', 'tracecontext'],
        },
      ],
      plugins: [reactPlugin({ router: true })],
    });

    rumInitialized = true;
    startInitialDatadogView();

    // Logs SDK must share env/service/version/site/clientToken with RUM for correlation.
    // See https://docs.datadoghq.com/real_user_monitoring/correlate_with_other_telemetry/logs/
    datadogLogs.init({
      clientToken: config.clientToken,
      site: config.site,
      service: config.service,
      env: config.env,
      version: config.version,
      forwardErrorsToLogs: true,
      // Avoid forwarding hundreds of dev console.log calls; capture warn/error only.
      forwardConsoleLogs: ['error', 'warn'],
      sessionSampleRate: 100,
    });
    logsInitialized = true;

    if (import.meta.env.DEV) {
      console.info('Datadog RUM + Logs initialized', {
        env: config.env,
        service: config.service,
        tracing: true,
      });
    }
  } catch (error) {
    console.error('Failed to initialize Datadog RUM:', error);
  }
}

export function setDatadogUser(user) {
  if (!rumInitialized || !user) return;

  const displayName =
    user.name ||
    [user.first_name, user.last_name].filter(Boolean).join(' ') ||
    user.email;

  datadogRum.setUser({
    id: String(user.id ?? user.user_id ?? user.email),
    email: user.email,
    name: displayName,
  });

  if (user.role) {
    datadogRum.setGlobalContextProperty('user.role', user.role);
  }

  const roles = user.membership_roles;
  if (Array.isArray(roles) && roles.length > 0) {
    datadogRum.setGlobalContextProperty('user.membership_roles', roles.join(','));
  }

  const orgSlug = resolveOrganizationSlug();
  if (orgSlug) {
    datadogRum.setGlobalContextProperty('org.slug', orgSlug);
  }
}

export function clearDatadogUser() {
  if (!rumInitialized) return;

  datadogRum.clearUser();
  datadogRum.removeGlobalContextProperty('user.role');
  datadogRum.removeGlobalContextProperty('user.membership_roles');
  datadogRum.removeGlobalContextProperty('org.slug');
}

export function addDatadogAction(name, context = {}) {
  if (!rumInitialized) return;
  datadogRum.addAction(name, context);
}

/** Structured browser log correlated with the active RUM session/trace. */
export function logToDatadog(level, message, context = {}) {
  if (!logsInitialized) return;
  const logger = datadogLogs.logger;
  if (typeof logger[level] === 'function') {
    logger[level](message, context);
  }
}

function detectLoginMethod(tokens) {
  if (tokens?.google_token) return 'google';
  if (tokens?.user_profile) return 'social';
  if (tokens?.user) return 'password';
  return 'token';
}

export function trackUserLogin(tokens) {
  addDatadogAction('user_login', { method: detectLoginMethod(tokens) });
}

export function trackUserLogout() {
  addDatadogAction('user_logout');
}

export function trackApiSuccess(config, response) {
  if (!rumInitialized || !config?.url) return;

  const method = (config.method || 'get').toLowerCase();
  const url = config.url;

  if (method === 'post' && /\/api\/v1\/reflections\/?$/.test(url)) {
    addDatadogAction('reflection_submitted', {
      reflectionId: response?.data?.id,
      templateId: response?.data?.template,
      programSlug: response?.data?.program_slug,
    });
    return;
  }

  if ((method === 'patch' || method === 'put') && /\/api\/v1\/reflections\/[^/]+\/?$/.test(url)) {
    const reflectionId = url.match(/\/api\/v1\/reflections\/([^/]+)/)?.[1];
    addDatadogAction('reflection_updated', { reflectionId });
    return;
  }

  if (method === 'post' && /\/api\/v1\/orders\/?$/.test(url)) {
    addDatadogAction('order_created', {
      orderId: response?.data?.id,
      status: response?.data?.status,
    });
    return;
  }

  if (method === 'post' && /\/transition\/?$/.test(url)) {
    const orderId = url.match(/\/(orders|maintenance)\/([^/]+)\/transition/)?.[2];
    const contentType = url.includes('/maintenance/') ? 'maintenance_ticket' : 'order';
    addDatadogAction('order_transitioned', {
      orderId,
      contentType,
      toState: config.data?.to_state ?? response?.data?.status,
    });
    return;
  }

  if (method === 'post' && /\/bulk-transition\/?$/.test(url)) {
    const contentType = url.includes('/maintenance/') ? 'maintenance_ticket' : 'order';
    addDatadogAction('order_bulk_transitioned', {
      contentType,
      count: config.data?.ids?.length,
      toState: config.data?.to_state,
    });
  }
}

export { datadogRum, datadogLogs };

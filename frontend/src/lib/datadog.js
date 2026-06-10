import { datadogRum } from '@datadog/browser-rum';
import { resolveOrganizationSlug } from '../utils/orgSlug';

let initialized = false;

function createTraceIdentifier(bits = 64) {
  const buffer = crypto.getRandomValues(new Uint32Array(2));
  if (bits === 63) {
    buffer[buffer.length - 1] >>>= 1;
  }
  return {
    toString(radix = 10) {
      let high = buffer[1];
      let low = buffer[0];
      let str = '';
      do {
        const mod = (high % radix) * 4294967296 + low;
        high = Math.floor(high / radix);
        low = Math.floor(mod / radix);
        str = (mod % radix).toString(radix) + str;
      } while (high || low);
      return str;
    },
  };
}

function toPaddedHexadecimalString(id) {
  return id.toString(16).padStart(16, '0');
}

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

function isApiTracingUrl(url) {
  const apiUrl = normalizeApiUrl(import.meta.env.VITE_API_URL);
  if (apiUrl && url.startsWith(apiUrl)) {
    return true;
  }

  return (
    /^https:\/\/admin\.bunklogs\.net/.test(url) ||
    /^http:\/\/localhost:8000/.test(url)
  );
}

export function isDatadogRumEnabled() {
  return initialized;
}

function resolveRequestUrl(baseURL, url) {
  if (!url) return null;
  if (/^https?:\/\//.test(url)) return url;
  const base = (baseURL || '').replace(/\/$/, '');
  return `${base}${url.startsWith('/') ? url : `/${url}`}`;
}

/**
 * Inject Datadog + W3C trace headers on API requests.
 * RUM's passive XHR hook is unreliable with axios; set headers explicitly here.
 */
export function applyTraceHeaders(headers, requestUrl) {
  if (!initialized || !requestUrl || !isApiTracingUrl(requestUrl)) {
    return;
  }

  const traceId = createTraceIdentifier(64);
  const spanId = createTraceIdentifier(63);
  const traceIdHex = toPaddedHexadecimalString(traceId);
  const spanIdHex = toPaddedHexadecimalString(spanId);

  const setHeader = (name, value) => {
    if (headers?.set) {
      headers.set(name, value);
    } else {
      headers[name] = value;
    }
  };

  setHeader('x-datadog-origin', 'rum');
  setHeader('x-datadog-trace-id', traceId.toString());
  setHeader('x-datadog-parent-id', spanId.toString());
  setHeader('x-datadog-sampling-priority', '1');
  setHeader('traceparent', `00-0000000000000000${traceIdHex}-${spanIdHex}-01`);
  setHeader('tracestate', 'dd=s:1;o:rum');
}

export async function waitForDatadogSession(timeoutMs = 3000) {
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
  if (initialized || !shouldEnableDatadog()) {
    return;
  }

  const environment =
    import.meta.env.VITE_DATADOG_ENV ||
    (import.meta.env.PROD ? 'production' : 'development');

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
    });

    initialized = true;

    if (import.meta.env.DEV) {
      console.info('Datadog RUM initialized', {
        env: environment,
        service: import.meta.env.VITE_DATADOG_SERVICE || 'bunklogs-frontend',
        tracing: true,
      });
    }
  } catch (error) {
    console.error('Failed to initialize Datadog RUM:', error);
  }
}

export function setDatadogUser(user) {
  if (!initialized || !user) return;

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
  if (!initialized) return;

  datadogRum.clearUser();
  datadogRum.removeGlobalContextProperty('user.role');
  datadogRum.removeGlobalContextProperty('user.membership_roles');
  datadogRum.removeGlobalContextProperty('org.slug');
}

export function addDatadogAction(name, context = {}) {
  if (!initialized) return;
  datadogRum.addAction(name, context);
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
  if (!initialized || !config?.url) return;

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

export { datadogRum };

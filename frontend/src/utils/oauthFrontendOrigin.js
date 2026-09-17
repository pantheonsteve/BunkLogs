/**
 * Remember which tenant SPA started Google login.
 *
 * Multi-org users (CLC + TBE) must return to the host they clicked
 * "Sign in with Google" on. Membership in CLC must not send a TBE
 * sign-in to clc.bunklogs.net.
 */

export const OAUTH_ORIGIN_COOKIE = 'oauth_frontend_origin';

const RESERVED_LABELS = new Set(['', 'www', 'admin', 'api', 'localhost']);
const LOCAL_DEV_PORTS = new Set(['5173', '5174', '3000']);

export function isAllowedFrontendOrigin(origin) {
  let parsed;
  try {
    parsed = new URL(origin);
  } catch {
    return false;
  }
  if (parsed.pathname !== '/' || parsed.search || parsed.hash || parsed.username) {
    return false;
  }
  const host = parsed.hostname.toLowerCase();
  if (host === 'localhost' || host === '127.0.0.1') {
    return parsed.protocol === 'http:' && LOCAL_DEV_PORTS.has(parsed.port);
  }
  const parts = host.split('.');
  if (
    parsed.protocol === 'https:'
    && !parsed.port
    && parts.length === 3
    && parts.slice(-2).join('.') === 'bunklogs.net'
  ) {
    return !RESERVED_LABELS.has(parts[0]);
  }
  return false;
}

function cookieDomainSuffix() {
  if (typeof window === 'undefined') return '';
  return window.location.hostname.endsWith('bunklogs.net')
    ? '; Domain=.bunklogs.net'
    : '';
}

export function rememberOauthFrontendOrigin(origin = window.location.origin) {
  if (typeof document === 'undefined' || !isAllowedFrontendOrigin(origin)) {
    return;
  }
  const secure = window.location.protocol === 'https:' ? '; Secure' : '';
  document.cookie = `${OAUTH_ORIGIN_COOKIE}=${encodeURIComponent(origin)}; Path=/; Max-Age=600; SameSite=Lax${secure}${cookieDomainSuffix()}`;
}

export function readOauthFrontendOrigin() {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${OAUTH_ORIGIN_COOKIE}=([^;]*)`));
  if (!match) return null;
  try {
    const origin = decodeURIComponent(match[1]);
    return isAllowedFrontendOrigin(origin) ? new URL(origin).origin : null;
  } catch {
    return null;
  }
}

export function clearOauthFrontendOrigin() {
  if (typeof document === 'undefined') return;
  document.cookie = `${OAUTH_ORIGIN_COOKIE}=; Path=/; Max-Age=0${cookieDomainSuffix()}`;
}

/**
 * If Google (or FRONTEND_URL) dropped the user on the wrong tenant,
 * hop to the origin they started on and keep the token hash.
 */
export function bounceToIntendedOauthOrigin() {
  const intended = readOauthFrontendOrigin();
  if (!intended || typeof window === 'undefined') return false;
  if (intended === window.location.origin) return false;
  const dest = `${intended}${window.location.pathname}${window.location.search}${window.location.hash}`;
  window.location.replace(dest);
  return true;
}

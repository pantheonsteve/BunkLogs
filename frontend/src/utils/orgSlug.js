/** Reserved first labels on *.bunklogs.net — must match backend middleware. */
const SUBDOMAIN_SKIP = new Set(['', 'www', 'admin', 'api', 'localhost']);

/**
 * Tenant slug from the SPA hostname (e.g. clc.bunklogs.net → "clc").
 * Returns null on localhost, admin host, or non-bunklogs hosts.
 */
export function orgSlugFromHost(hostname) {
  const host = String(hostname || '').toLowerCase().replace(/\.$/, '');
  const parts = host.split('.');
  if (parts.length < 3 || parts.slice(-2).join('.') !== 'bunklogs.net') {
    return null;
  }
  const label = parts[0];
  return SUBDOMAIN_SKIP.has(label) ? null : label;
}

/** Dev env override, else tenant subdomain on production hosts. */
export function resolveOrganizationSlug() {
  const devSlug = import.meta.env.VITE_DEV_ORGANIZATION_SLUG;
  if (devSlug) {
    return String(devSlug).trim() || null;
  }
  if (typeof window !== 'undefined' && window.location?.hostname) {
    return orgSlugFromHost(window.location.hostname);
  }
  return null;
}

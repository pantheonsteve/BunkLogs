/** Reserved first labels on *.bunklogs.net — must match backend middleware. */
const SUBDOMAIN_SKIP = new Set(['', 'www', 'admin', 'api', 'localhost']);

const DEV_ORG_OVERRIDE_KEY = 'dev_org_slug_override';

/** Orgs the dev-only org switcher (DevOrgSwitcher) offers. Add new tenants here. */
export const DEV_KNOWN_ORGS = [
  { slug: 'clc', label: 'Crane Lake Camp (clc)' },
  { slug: 'tbe', label: 'Temple Beth-El (tbe)' },
];

/**
 * Runtime tenant override for local dev, set via the DevOrgSwitcher widget.
 * Lets you flip tenants without editing .env / restarting Vite. Never active
 * outside `vite dev` (import.meta.env.DEV is false in production builds).
 */
export function getDevOrgOverride() {
  if (!import.meta.env.DEV) return null;
  try {
    return localStorage.getItem(DEV_ORG_OVERRIDE_KEY) || null;
  } catch {
    return null;
  }
}

export function setDevOrgOverride(slug) {
  if (!import.meta.env.DEV) return;
  try {
    if (slug) {
      localStorage.setItem(DEV_ORG_OVERRIDE_KEY, slug);
    } else {
      localStorage.removeItem(DEV_ORG_OVERRIDE_KEY);
    }
  } catch {
    // Ignore storage failures (e.g. private browsing).
  }
}

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

/** Runtime dev override, else dev env var, else tenant subdomain on production hosts. */
export function resolveOrganizationSlug() {
  const runtimeOverride = getDevOrgOverride();
  if (runtimeOverride) {
    return runtimeOverride;
  }
  const devSlug = import.meta.env.VITE_DEV_ORGANIZATION_SLUG;
  if (devSlug) {
    return String(devSlug).trim() || null;
  }
  if (typeof window !== 'undefined' && window.location?.hostname) {
    return orgSlugFromHost(window.location.hostname);
  }
  return null;
}

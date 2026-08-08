/**
 * Current-tenant public branding (TBE Frontend Readiness).
 *
 * Unauthenticated -- sign-in/sign-up/password-reset pages need the org
 * display name before a user is logged in. The shared `api` client's
 * request interceptor already attaches `X-Organization-Slug` from the
 * SPA hostname, so this is a plain GET with no extra config.
 */
import api from '../api';

/** GET /api/v1/organization/branding/ */
export async function fetchOrganizationBranding() {
  const { data } = await api.get('/api/v1/organization/branding/');
  return data;
}

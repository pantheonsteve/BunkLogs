/**
 * Faculty (TBE) home API client — Step 7_24.
 *
 * Sibling of `facultyChallenges.js`, bound to the faculty dashboard.
 * All requests carry the `X-Organization-Slug` header for multi-tenant
 * routing.
 */
import api from '../api';

const BASE = '/api/v1/faculty';

/** GET /api/v1/faculty/dashboard/ */
export async function fetchFacultyDashboard(orgSlug) {
  const { data } = await api.get(`${BASE}/dashboard/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

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

/** GET /api/v1/faculty/queue/ — routed entries awaiting a reply, oldest first. */
export async function fetchFacultyQueue(orgSlug, { page = 1, pageSize = 20 } = {}) {
  const { data } = await api.get(`${BASE}/queue/`, {
    params: { page, page_size: pageSize },
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** GET /api/v1/faculty/roster/ */
export async function fetchFacultyRoster(orgSlug, { assignmentGroup } = {}) {
  const params = assignmentGroup ? { assignment_group: assignmentGroup } : {};
  const { data } = await api.get(`${BASE}/roster/`, {
    params,
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** GET /api/v1/faculty/roster/:personId/ */
export async function fetchFacultyRosterDetail(orgSlug, personId) {
  const { data } = await api.get(`${BASE}/roster/${personId}/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

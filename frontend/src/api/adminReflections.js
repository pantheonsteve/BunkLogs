import api from '../api';

/**
 * Admin reflections completion dashboard client (Step 4_4 — TBE).
 *
 * Wraps `/api/v1/admin/reflections/teams/<role>/`. `X-Organization-Slug`
 * is injected automatically by the shared `api` instance (see api.js),
 * so callers don't need to pass `orgSlug` explicitly.
 */
const BASE = '/api/v1/admin/reflections/teams';

function buildParams({ date, gradeLevels } = {}) {
  const params = {};
  if (date) params.date = date;
  if (Array.isArray(gradeLevels) && gradeLevels.length > 0) {
    params.grade_level = gradeLevels.join(',');
  }
  return params;
}

export async function fetchAdminReflectionsTeam(role, options = {}) {
  const { data } = await api.get(`${BASE}/${role}/`, { params: buildParams(options) });
  return data;
}

export async function fetchAdminReflectionMember(role, membershipId) {
  const { data } = await api.get(`${BASE}/${role}/members/${membershipId}/`);
  return data;
}

export function exportAdminReflectionsTeamUrl(role, options = {}) {
  const params = buildParams(options);
  const qs = new URLSearchParams(params).toString();
  return `${BASE}/${role}/export/${qs ? `?${qs}` : ''}`;
}

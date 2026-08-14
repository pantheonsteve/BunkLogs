import api from '../api';

/**
 * Admin growth-by-grade dashboard client.
 *
 * Wraps `/api/v1/admin/reflections/growth/`. `X-Organization-Slug` is
 * injected automatically by the shared `api` instance (see api.js), so
 * callers don't need to pass `orgSlug` explicitly.
 */
const BASE = '/api/v1/admin/reflections/growth';

function buildParams({ role, start, end, gradeLevels } = {}) {
  const params = {};
  if (role) params.role = role;
  if (start) params.start = start;
  if (end) params.end = end;
  if (Array.isArray(gradeLevels) && gradeLevels.length > 0) {
    params.grade_level = gradeLevels.join(',');
  }
  return params;
}

export async function fetchAdminGrowth(options = {}) {
  const { data } = await api.get(`${BASE}/`, { params: buildParams(options) });
  return data;
}

export async function fetchAdminGrowthExamples({ theme, dashboardRole, ...options } = {}) {
  const params = buildParams(options);
  if (theme) params.theme = theme;
  if (dashboardRole) params.dashboard_role = dashboardRole;
  const { data } = await api.get(`${BASE}/examples/`, { params });
  return data;
}

export function exportAdminGrowthUrl(options = {}) {
  const qs = new URLSearchParams(buildParams(options)).toString();
  return `${BASE}/export/${qs ? `?${qs}` : ''}`;
}

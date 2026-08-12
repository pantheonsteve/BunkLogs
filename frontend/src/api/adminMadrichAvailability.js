import api from '../api';

/**
 * Admin Madrich availability staffing matrix client (Step 4_7).
 *
 * Wraps `/api/v1/admin/madrich-availability/`. `X-Organization-Slug` is
 * injected automatically by the shared `api` instance (see api.js).
 */
const BASE = '/api/v1/admin/madrich-availability';

function buildParams({ program, from, to } = {}) {
  const params = {};
  if (program) params.program = program;
  if (from) params.from = from;
  if (to) params.to = to;
  return params;
}

export async function fetchAdminMadrichAvailability(options = {}) {
  const { data } = await api.get(`${BASE}/`, { params: buildParams(options) });
  return data;
}

export function exportAdminMadrichAvailabilityUrl(options = {}) {
  const params = buildParams(options);
  const qs = new URLSearchParams(params).toString();
  return `${BASE}/export.csv${qs ? `?${qs}` : ''}`;
}

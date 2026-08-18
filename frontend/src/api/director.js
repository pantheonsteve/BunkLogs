/**
 * Director homepage client (Step 4_9 §6).
 *
 * "Director" is the admin role scoped to a religious-school org, so these
 * live under `/api/v1/admin/reflections/` alongside the existing completion
 * dashboard. `X-Organization-Slug` is injected by the shared `api` instance.
 */
import api from '../api';

const BASE = '/api/v1/admin/reflections';

/** GET /api/v1/admin/reflections/pulse/ */
export async function fetchDirectorPulse() {
  const { data } = await api.get(`${BASE}/pulse/`);
  return data;
}

/** GET /api/v1/admin/reflections/queue/ */
export async function fetchDirectorQueue({ page = 1, pageSize = 20 } = {}) {
  const { data } = await api.get(`${BASE}/queue/`, {
    params: { page, page_size: pageSize },
  });
  return data;
}

/** GET /api/v1/admin/reflections/coverage/ */
export async function fetchDirectorCoverage() {
  const { data } = await api.get(`${BASE}/coverage/`);
  return data;
}

/** GET /api/v1/admin/reflections/faculty-activity/ */
export async function fetchDirectorFacultyActivity() {
  const { data } = await api.get(`${BASE}/faculty-activity/`);
  return data;
}

/** GET /api/v1/admin/reflections/themes/ */
export async function fetchDirectorThemes() {
  const { data } = await api.get(`${BASE}/themes/`);
  return data;
}

/** GET /api/v1/admin/reflections/madrichim/ */
export async function fetchDirectorMadrichim({ page = 1, pageSize = 25 } = {}) {
  const { data } = await api.get(`${BASE}/madrichim/`, {
    params: { page, page_size: pageSize },
  });
  return data;
}

/**
 * Downloads the roster CSV.
 *
 * Fetched through the authenticated client rather than linked with a plain
 * `href`: the API is a different origin from the SPA, so a bare anchor would
 * resolve against the SPA host and carry no bearer token.
 */
export async function downloadMadrichimCsv() {
  const response = await api.get(`${BASE}/madrichim/export/`, { responseType: 'blob' });
  const url = URL.createObjectURL(response.data);
  try {
    const link = document.createElement('a');
    link.href = url;
    link.download = 'madrichim.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

/**
 * Director homepage client (Step 4_9 §6).
 *
 * "Director" is the admin role scoped to a religious-school org, so these
 * live under `/api/v1/admin/reflections/` alongside the existing completion
 * dashboard. `X-Organization-Slug` is injected by the shared `api` instance.
 */
import api from '../api';

const BASE = '/api/v1/admin/reflections';

function withProgram(params, program) {
  if (program) return { ...params, program };
  return params;
}

/** GET /api/v1/admin/reflections/pulse/ */
export async function fetchDirectorPulse({ program } = {}) {
  const { data } = await api.get(`${BASE}/pulse/`, { params: withProgram({}, program) });
  return data;
}

/** GET /api/v1/admin/reflections/queue/ */
export async function fetchDirectorQueue({ page = 1, pageSize = 20, program } = {}) {
  const { data } = await api.get(`${BASE}/queue/`, {
    params: withProgram({ page, page_size: pageSize }, program),
  });
  return data;
}

/** GET /api/v1/admin/reflections/coverage/ */
export async function fetchDirectorCoverage({ program } = {}) {
  const { data } = await api.get(`${BASE}/coverage/`, { params: withProgram({}, program) });
  return data;
}

/** GET /api/v1/admin/reflections/coverage/<session_date>/ */
export async function fetchDirectorCoverageDetail(sessionDate, { program } = {}) {
  const { data } = await api.get(`${BASE}/coverage/${sessionDate}/`, {
    params: withProgram({}, program),
  });
  return data;
}

/** GET /api/v1/admin/reflections/faculty-activity/ */
export async function fetchDirectorFacultyActivity({ program } = {}) {
  const { data } = await api.get(`${BASE}/faculty-activity/`, {
    params: withProgram({}, program),
  });
  return data;
}

/** GET /api/v1/admin/reflections/themes/ */
export async function fetchDirectorThemes({ program } = {}) {
  const { data } = await api.get(`${BASE}/themes/`, { params: withProgram({}, program) });
  return data;
}

/** GET /api/v1/admin/reflections/madrichim/ */
export async function fetchDirectorMadrichim({ page = 1, pageSize = 25, program } = {}) {
  const { data } = await api.get(`${BASE}/madrichim/`, {
    params: withProgram({ page, page_size: pageSize }, program),
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
export async function downloadMadrichimCsv({ program } = {}) {
  const response = await api.get(`${BASE}/madrichim/export/`, {
    params: withProgram({}, program),
    responseType: 'blob',
  });
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

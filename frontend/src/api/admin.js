import api from '../api';

/**
 * Step 7_13 — Admin Flow API client.
 *
 * Wraps the endpoints under `/api/v1/admin/`. Each helper returns the
 * raw payload (no transformation) so component code stays the source
 * of truth for shape interpretation.
 */
export const ADMIN_BASE = '/api/v1/admin';

export async function fetchAdminDashboard() {
  const resp = await api.get(`${ADMIN_BASE}/dashboard/`);
  return resp?.data ?? null;
}

export async function postAdminOverrideEdit({
  contentType,
  contentId,
  patch,
  reason,
}) {
  const resp = await api.post(`${ADMIN_BASE}/override-edit/`, {
    content_type: contentType,
    content_id: contentId,
    patch,
    reason,
  });
  return resp?.data ?? null;
}

// ---------------------------------------------------------------------------
// People (Story 55)
// ---------------------------------------------------------------------------

export async function listAdminPeople(params = {}, config = {}) {
  const resp = await api.get(`${ADMIN_BASE}/people/`, { params, ...config });
  return resp?.data ?? { results: [] };
}

/** Build query params for GET /admin/people/ — omits empty filters. */
export function buildAdminPeopleListParams({
  search = '',
  role = '',
  status = '',
  last_name_initial = '',
  offset = 0,
  page_size = 50,
} = {}) {
  const params = { offset, page_size };
  const trimmedSearch = search.trim();
  if (trimmedSearch) params.search = trimmedSearch;
  if (role) params.role = role;
  if (status) params.status = status;
  if (last_name_initial) params.last_name_initial = last_name_initial;
  return params;
}

export async function getAdminPerson(personId) {
  const resp = await api.get(`${ADMIN_BASE}/people/${personId}/`);
  return resp?.data ?? null;
}

export async function createAdminPerson(payload) {
  const resp = await api.post(`${ADMIN_BASE}/people/`, payload);
  return resp?.data ?? null;
}

export async function patchAdminPerson(personId, patch) {
  const resp = await api.patch(`${ADMIN_BASE}/people/${personId}/`, patch);
  return resp?.data ?? null;
}

export async function addAdminMembership(personId, payload) {
  const resp = await api.post(`${ADMIN_BASE}/people/${personId}/memberships/`, payload);
  return resp?.data ?? null;
}

export async function patchAdminMembership(membershipId, patch) {
  const resp = await api.patch(`${ADMIN_BASE}/memberships/${membershipId}/`, patch);
  return resp?.data ?? null;
}

export async function deactivateAdminMembership(membershipId, reason) {
  const resp = await api.post(`${ADMIN_BASE}/memberships/${membershipId}/deactivate/`, { reason });
  return resp?.data ?? null;
}

export async function inviteAdminPerson(personId, payload = {}) {
  const resp = await api.post(`${ADMIN_BASE}/people/${personId}/invite/`, payload);
  return resp?.data ?? null;
}

export async function previewAdminPeopleDedupe(payload) {
  const resp = await api.post(`${ADMIN_BASE}/people/dedupe/preview/`, payload);
  return resp?.data ?? null;
}

export async function commitAdminPeopleDedupe(payload) {
  const resp = await api.post(`${ADMIN_BASE}/people/dedupe/`, payload);
  return resp?.data ?? null;
}

export async function previewAdminPersonDelete(personId, payload = {}) {
  const resp = await api.post(`${ADMIN_BASE}/people/${personId}/delete/preview/`, payload);
  return resp?.data ?? null;
}

export async function commitAdminPersonDelete(personId, payload) {
  const resp = await api.post(`${ADMIN_BASE}/people/${personId}/delete/`, payload);
  return resp?.data ?? null;
}

// ---------------------------------------------------------------------------
// Assignments (Story 56)
// ---------------------------------------------------------------------------

export async function listAdminAssignments(params = {}) {
  const query = typeof params === 'string' ? { sub_tab: params } : { ...params };
  if (query.sub_tab === undefined && query.subTab) {
    query.sub_tab = query.subTab;
    delete query.subTab;
  }
  const resp = await api.get(`${ADMIN_BASE}/assignments/`, { params: query });
  return resp?.data ?? { results: [] };
}

export async function createAdminAssignment(payload) {
  const resp = await api.post(`${ADMIN_BASE}/assignments/`, payload);
  return resp?.data ?? null;
}

export async function patchAdminAssignment(assignmentId, kind, patch) {
  const resp = await api.patch(
    `${ADMIN_BASE}/assignments/${assignmentId}/?kind=${encodeURIComponent(kind)}`,
    { ...patch, kind },
  );
  return resp?.data ?? null;
}

// ---------------------------------------------------------------------------
// Programs + Settings (Story 58)
// ---------------------------------------------------------------------------

export async function listAdminPrograms(status) {
  const params = status ? { status } : {};
  const resp = await api.get(`${ADMIN_BASE}/programs/`, { params });
  return resp?.data ?? { results: [] };
}

export async function createAdminProgram(payload) {
  const resp = await api.post(`${ADMIN_BASE}/programs/`, payload);
  return resp?.data ?? null;
}

export async function patchAdminProgram(programId, patch) {
  const resp = await api.patch(`${ADMIN_BASE}/programs/${programId}/`, patch);
  return resp?.data ?? null;
}

export async function endAdminProgram(programId, reason) {
  const resp = await api.post(`${ADMIN_BASE}/programs/${programId}/end/`, { reason });
  return resp?.data ?? null;
}

export async function getAdminSettings() {
  const resp = await api.get(`${ADMIN_BASE}/settings/`);
  return resp?.data ?? null;
}

export async function patchAdminSettings(patch) {
  const resp = await api.patch(`${ADMIN_BASE}/settings/`, patch);
  return resp?.data ?? null;
}

// ---------------------------------------------------------------------------
// PR3 — Global search, Templates oversight, Bulk import
// ---------------------------------------------------------------------------

export async function searchAdmin(query) {
  const resp = await api.get(`${ADMIN_BASE}/search/`, { params: { q: query } });
  return resp?.data ?? { groups: {} };
}

export async function listAdminTemplates() {
  const resp = await api.get(`${ADMIN_BASE}/templates/`);
  return resp?.data ?? { results: [], grouped: {} };
}

export async function reviewAdminTemplate(templateId, payload) {
  const resp = await api.post(`${ADMIN_BASE}/templates/${templateId}/review/`, payload);
  return resp?.data ?? null;
}

export async function previewAdminPeopleImport(source, programSlug, file) {
  const fd = new FormData();
  fd.append('source', source);
  fd.append('program_slug', programSlug);
  fd.append('csv', file);
  const resp = await api.post(`${ADMIN_BASE}/people/import/preview/`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return resp?.data ?? null;
}

export async function commitAdminPeopleImport(source, programSlug, file) {
  const fd = new FormData();
  fd.append('source', source);
  fd.append('program_slug', programSlug);
  fd.append('csv', file);
  const resp = await api.post(`${ADMIN_BASE}/people/import/commit/`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return resp?.data ?? null;
}

export async function listAdminPeopleImportTemplates(source = 'campminder') {
  const resp = await api.get(`${ADMIN_BASE}/people/import/template/`, {
    params: { source },
  });
  return resp?.data ?? { templates: [] };
}

export async function downloadAdminPeopleImportTemplate(source, variant) {
  const resp = await api.get(`${ADMIN_BASE}/people/import/template/`, {
    params: { source, variant },
    responseType: 'blob',
  });
  const disposition = resp.headers['content-disposition'] || '';
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match?.[1] || `${source}-${variant}-import-template.csv`;
  const url = window.URL.createObjectURL(resp.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.URL.revokeObjectURL(url);
}

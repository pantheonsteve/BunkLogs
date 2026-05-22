/**
 * Leadership Team API client — Step 7_12 PRs A + B (Stories 45-53).
 *
 * Mirrors ``api/kitchenStaff.js`` shape: every call accepts an
 * ``orgSlug`` and injects ``X-Organization-Slug`` so the multi-tenant
 * middleware resolves the right org.
 */
import api from '../api';

const BASE = '/api/v1/leadership-team';

const headers = (orgSlug) => ({ 'X-Organization-Slug': orgSlug });

// ---------------------------------------------------------------------------
// Dashboards (Stories 45-47)
// ---------------------------------------------------------------------------

export async function fetchDashboard(orgSlug) {
  const { data } = await api.get(`${BASE}/dashboard/`, { headers: headers(orgSlug) });
  return data;
}

export async function fetchTeamDashboard(orgSlug, teamRole, { date } = {}) {
  const { data } = await api.get(`${BASE}/teams/${teamRole}/`, {
    params: date ? { date } : {},
    headers: headers(orgSlug),
  });
  return data;
}

export async function fetchMemberReflection(orgSlug, teamRole, membershipId, { period } = {}) {
  const { data } = await api.get(
    `${BASE}/teams/${teamRole}/members/${membershipId}/reflection/`,
    { params: period ? { period } : {}, headers: headers(orgSlug) },
  );
  return data;
}

// ---------------------------------------------------------------------------
// Self-reflection (Story 50)
// ---------------------------------------------------------------------------

export async function submitSelfReflection(orgSlug, payload) {
  const { data } = await api.post(`${BASE}/self-reflection/`, payload, {
    headers: headers(orgSlug),
  });
  return data;
}

export async function updateSelfReflection(orgSlug, reflectionId, payload) {
  const { data } = await api.patch(`${BASE}/self-reflection/${reflectionId}/`, payload, {
    headers: headers(orgSlug),
  });
  return data;
}

// ---------------------------------------------------------------------------
// Mark-attention (Story 46 c5)
// ---------------------------------------------------------------------------

export async function markAttention(orgSlug, reflectionId, { note = '' } = {}) {
  const { data } = await api.post(
    `${BASE}/reflections/${reflectionId}/mark-attention/`,
    { note },
    { headers: headers(orgSlug) },
  );
  return data;
}

export async function unmarkAttention(orgSlug, reflectionId) {
  await api.delete(`${BASE}/reflections/${reflectionId}/mark-attention/`, {
    headers: headers(orgSlug),
  });
}

// ---------------------------------------------------------------------------
// Template builder (Story 51)
// ---------------------------------------------------------------------------

export async function listTemplates(orgSlug, { status, role } = {}) {
  const { data } = await api.get(`${BASE}/templates/`, {
    params: { status, role },
    headers: headers(orgSlug),
  });
  return data;
}

export async function getTemplate(orgSlug, id) {
  const { data } = await api.get(`${BASE}/templates/${id}/`, { headers: headers(orgSlug) });
  return data;
}

export async function createTemplate(orgSlug, payload) {
  const { data } = await api.post(`${BASE}/templates/`, payload, { headers: headers(orgSlug) });
  return data;
}

export async function patchTemplate(orgSlug, id, payload, { forceNewVersion = false } = {}) {
  const { data } = await api.patch(`${BASE}/templates/${id}/`, payload, {
    params: forceNewVersion ? { force_new_version: 'true' } : {},
    headers: headers(orgSlug),
  });
  return data;
}

export async function publishTemplate(orgSlug, id) {
  const { data } = await api.post(`${BASE}/templates/${id}/publish/`, {}, {
    headers: headers(orgSlug),
  });
  return data;
}

export async function cloneTemplate(orgSlug, id) {
  const { data } = await api.post(`${BASE}/templates/${id}/clone/`, {}, {
    headers: headers(orgSlug),
  });
  return data;
}

export async function archiveTemplate(orgSlug, id) {
  const { data } = await api.post(`${BASE}/templates/${id}/archive/`, {}, {
    headers: headers(orgSlug),
  });
  return data;
}

// ---------------------------------------------------------------------------
// Assignments (Story 52)
// ---------------------------------------------------------------------------

export async function listAssignments(orgSlug, { template } = {}) {
  const { data } = await api.get(`${BASE}/assignments/`, {
    params: template ? { template } : {},
    headers: headers(orgSlug),
  });
  return data;
}

export async function createAssignment(orgSlug, payload) {
  const { data } = await api.post(`${BASE}/assignments/`, payload, {
    headers: headers(orgSlug),
  });
  return data;
}

export async function patchAssignment(orgSlug, id, payload) {
  const { data } = await api.patch(`${BASE}/assignments/${id}/`, payload, {
    headers: headers(orgSlug),
  });
  return data;
}

export async function cancelAssignment(orgSlug, id) {
  await api.delete(`${BASE}/assignments/${id}/`, { headers: headers(orgSlug) });
}

// ---------------------------------------------------------------------------
// Responses (Story 53)
// ---------------------------------------------------------------------------

export async function fetchResponses(orgSlug, templateId, params = {}) {
  const { data } = await api.get(`${BASE}/templates/${templateId}/responses/`, {
    params,
    headers: headers(orgSlug),
  });
  return data;
}

export function exportResponsesUrl(templateId, params = {}) {
  const qs = new URLSearchParams(params).toString();
  return `${BASE}/templates/${templateId}/responses/export/${qs ? `?${qs}` : ''}`;
}

export function exportTeamAggregateUrl(teamRole) {
  return `${BASE}/teams/${teamRole}/aggregate/export/`;
}

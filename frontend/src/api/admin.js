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

export async function listAdminPeople(params = {}) {
  const resp = await api.get(`${ADMIN_BASE}/people/`, { params });
  return resp?.data ?? { results: [] };
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

// ---------------------------------------------------------------------------
// Assignments (Story 56)
// ---------------------------------------------------------------------------

export async function listAdminAssignments(subTab) {
  const params = subTab ? { sub_tab: subTab } : {};
  const resp = await api.get(`${ADMIN_BASE}/assignments/`, { params });
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

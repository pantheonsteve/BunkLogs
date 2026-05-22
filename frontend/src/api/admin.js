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

/**
 * Unified dashboards API client.
 *
 * Wraps the role-agnostic `/api/v1/dashboards/*` endpoints. The bunk
 * dashboard endpoint resolves the caller's role server-side and
 * returns a `role_context` block the page uses to drive role-
 * conditional chrome (back link, future edit affordances). One URL,
 * one fetcher — UH/CC/Counselor/LT/Admin all read here.
 *
 * See `frontend/src/pages/dashboards/BunkDashboardPage.jsx`.
 */

import api from '../api';

/** Bunk Dashboard payload for any role authorized to view the bunk. */
export async function fetchBunkDashboard(bunkId, { date } = {}) {
  const params = date ? { date } : {};
  const { data } = await api.get(
    `/api/v1/dashboards/bunks/${bunkId}/`,
    { params },
  );
  return data;
}

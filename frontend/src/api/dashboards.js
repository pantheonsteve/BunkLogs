/**
 * Unified dashboards API client.
 *
 * Wraps the role + group-type agnostic `/api/v1/dashboards/group/<id>/`
 * endpoint. The backend resolves the caller's role server-side and
 * dispatches on `group.group_type` to return the right payload shape
 * (bunk, unit, division, classroom). The response always includes a
 * `role_context` block (role + group_type + can_edit) that the page
 * uses to pick the right presentational component and drive role-
 * conditional chrome.
 *
 * See `frontend/src/pages/dashboards/GroupDashboardPage.jsx`.
 */

import api from '../api';

/** Group dashboard payload for any role + group_type the viewer is authorized for. */
export async function fetchGroupDashboard(groupId, { date } = {}) {
  const params = date ? { date } : {};
  const { data } = await api.get(
    `/api/v1/dashboards/group/${groupId}/`,
    { params },
  );
  return data;
}

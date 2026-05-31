/**
 * Camper Care flow API client (Step 7_8).
 *
 * Wrappers around `/api/v1/camper-care/*` (Stories 18-23). Mirrors the
 * shape of `api/unitHead.js`: thin axios calls, named exports per
 * endpoint, the role-namespaced order transition aliases delegate to
 * the shared state machine (Step 7_2) so behaviour matches the
 * generic `/api/v1/orders/...` paths.
 */

import api from '../api';
import { newClientSubmissionId } from './counselor';

export { newClientSubmissionId };

/** CC dashboard (Story 18 + 19) for a date (default today). */
export async function fetchCamperCareDashboard({ date, noCache = false } = {}) {
  const params = {};
  if (date) params.date = date;
  if (noCache) params.nocache = '1';
  const { data } = await api.get('/api/v1/camper-care/dashboard/', { params });
  return data;
}

// NOTE: `fetchBunkDashboard` removed when the bunk dashboard was
// consolidated under `/api/v1/dashboards/group/<id>/`. Use
// `frontend/src/api/dashboards.js#fetchGroupDashboard` instead.

/**
 * Camper drill-down payload (Story 18 c.9 + Story 21 in-context notes).
 * Reuses the role-agnostic shape served by the shared payload builder.
 */
export async function fetchCamperDashboard(camperId, {
  date,
  range = 'last_4_weeks',
  dateStart,
  dateEnd,
  notes_from,
  notes_to,
} = {}) {
  const params = { range };
  if (date) params.date = date;
  if (dateStart) params.date_start = dateStart;
  if (dateEnd) params.date_end = dateEnd;
  if (notes_from) params.notes_from = notes_from;
  if (notes_to) params.notes_to = notes_to;
  const { data } = await api.get(
    `/api/v1/camper-care/campers/${camperId}/`,
    { params },
  );
  return data;
}

/**
 * Flag workspace listing (Story 20).
 *
 * @param status — `'active'` / `'followed_up'` / `'resolved'` (omit for
 *   the unresolved bucket = active + followed_up).
 * @param caseloadOnly — narrow to viewer's caseload (default false per CC2).
 */
export async function fetchFlags({ status, caseloadOnly = false } = {}) {
  const params = {};
  if (status) params.status = status;
  if (caseloadOnly) params.caseload_only = 'true';
  const { data } = await api.get('/api/v1/camper-care/flags/', { params });
  return data;
}

/**
 * Full activity for a single flag (Story 20 expand): the untruncated
 * source note/reflection body plus the audit history (every follow-up,
 * resolve, and reopen note the Camper Care team wrote).
 */
export async function fetchFlagDetail(flagId) {
  const { data } = await api.get(`/api/v1/camper-care/flags/${flagId}/`);
  return data;
}

/** Transition a flag to followed_up (interim, note optional). */
export async function followUpFlag(flagId, { note } = {}) {
  const { data } = await api.post(
    `/api/v1/camper-care/flags/${flagId}/follow-up/`,
    { note: note || '' },
  );
  return data;
}

/** Resolve a flag (terminal, closing note required per Story 20.5.ii). */
export async function resolveFlag(flagId, { note }) {
  const { data } = await api.post(
    `/api/v1/camper-care/flags/${flagId}/resolve/`,
    { note },
  );
  return data;
}

/** Reopen a flag from resolved or followed_up (reason required per 5.iii). */
export async function reopenFlag(flagId, { note }) {
  const { data } = await api.post(
    `/api/v1/camper-care/flags/${flagId}/reopen/`,
    { note },
  );
  return data;
}

/**
 * Orders workspace listing (Story 22).
 *
 * Filter values: `'all'`, `'my_caseload'`, `'by_bunk'`, `'by_item'`.
 */
export async function fetchOrders({
  filter = 'all',
  bunkId,
  item,
  resolvedSince,
  resolvedUntil,
} = {}) {
  const params = { filter };
  if (bunkId) params.bunk_id = bunkId;
  if (item) params.item = item;
  if (resolvedSince) params.resolved_since = resolvedSince;
  if (resolvedUntil) params.resolved_until = resolvedUntil;
  const { data } = await api.get('/api/v1/camper-care/orders/', { params });
  return data;
}

/** Single-order transition via the camper-care alias to the shared state machine. */
export async function transitionOrder(orderId, { toState, note, reason } = {}) {
  const payload = { to_state: toState };
  if (note) payload.note = note;
  if (reason) payload.reason = reason;
  const { data } = await api.post(
    `/api/v1/camper-care/orders/${orderId}/transition/`,
    payload,
  );
  return data;
}

/** Bulk transition (Story 23.5). All ids share the same target state. */
export async function bulkTransitionOrders({ ids, toState, note, reason } = {}) {
  const payload = { ids, to_state: toState };
  if (note) payload.note = note;
  if (reason) payload.reason = reason;
  const { data } = await api.post(
    '/api/v1/camper-care/orders/bulk-transition/',
    payload,
  );
  return data;
}

/**
 * Submit a Camper Care self-reflection (Step 7_8d). Mirrors the UH
 * write contract: `dayOff: true` is the canonical shortcut and a
 * complete payload — server fills `answers: { day_off: true }`.
 */
export async function createCamperCareSelfReflection({
  answers,
  dayOff = false,
  language = 'en',
  clientSubmissionId,
}) {
  const payload = {
    day_off: dayOff,
    language,
    client_submission_id: clientSubmissionId,
  };
  if (!dayOff && answers !== undefined) {
    payload.answers = answers;
  }
  const res = await api.post('/api/v1/camper-care/self-reflection/', payload);
  return { data: res.data, status: res.status };
}

/** Edit a CC self-reflection inside today's edit window. */
export async function patchCamperCareSelfReflection(reflectionId, {
  answers,
  dayOff,
  language,
}) {
  const payload = {};
  if (answers !== undefined) payload.answers = answers;
  if (dayOff !== undefined) payload.day_off = dayOff;
  if (language !== undefined) payload.language = language;
  const { data } = await api.patch(
    `/api/v1/camper-care/self-reflection/${reflectionId}/`,
    payload,
  );
  return data;
}

/** Paginated CC self-reflection history. */
export async function fetchCamperCareSelfReflectionHistory({ page = 1, pageSize } = {}) {
  const params = { page };
  if (pageSize) params.page_size = pageSize;
  const { data } = await api.get(
    '/api/v1/camper-care/self-reflection/history/',
    { params },
  );
  return data;
}

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
 * Submit a Camper Care note (Story 21). Returns `{ data, status }` so
 * the caller can distinguish 201 (created) from any retry semantics
 * the backend grows later.
 */
export async function createCamperCareNote({
  subjectId, body, category, isSensitive = false, language = 'en',
}) {
  const payload = {
    subject_id: subjectId,
    body,
    category,
    is_sensitive: isSensitive,
    language,
  };
  const res = await api.post('/api/v1/camper-care/notes/', payload);
  return { data: res.data, status: res.status };
}

/** Edit a Camper Care note within the 24h window (Story 21.6). */
export async function patchCamperCareNote(noteId, {
  body, isSensitive, category, language,
}) {
  const payload = {};
  if (body !== undefined) payload.body = body;
  if (isSensitive !== undefined) payload.is_sensitive = isSensitive;
  if (category !== undefined) payload.category = category;
  if (language !== undefined) payload.language = language;
  const { data } = await api.patch(
    `/api/v1/camper-care/notes/${noteId}/`,
    payload,
  );
  return data;
}

/**
 * Resolve the audience disclosure copy for the note form (Story 21.10).
 * Server-side resolution keeps a single source of truth for the role
 * labels so the Sensitive toggle gets the authoritative list.
 */
export async function fetchCamperCareNoteAudience({ isSensitive = false } = {}) {
  const params = { is_sensitive: isSensitive ? 'true' : 'false' };
  const { data } = await api.get(
    '/api/v1/camper-care/notes/audience/',
    { params },
  );
  return data;
}

/** Categories enum mirroring `Note.Category` on the backend. */
export const NOTE_CATEGORIES = Object.freeze([
  { value: 'medical', label: 'Medical' },
  { value: 'family', label: 'Family' },
  { value: 'social', label: 'Social' },
  { value: 'behavioral', label: 'Behavioral' },
  { value: 'other', label: 'Other' },
]);

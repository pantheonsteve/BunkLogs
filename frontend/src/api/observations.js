/**
 * Observations API client (Step 7_23).
 *
 * Thin wrappers around `/api/v1/observations/*` — the converged note system
 * that supersedes the notes platform + subject notes.
 */

import api from '../api';

export const SENSITIVITY_AUDIENCE = Object.freeze({
  normal: 'Everyone',
  sensitive: 'Unit Heads and above',
  domain: 'Leadership Team and above',
  confidential: 'Pro Team only',
});

export const SENSITIVITY_OPTIONS = Object.freeze([
  { value: 'normal', label: `Normal — ${SENSITIVITY_AUDIENCE.normal}` },
  { value: 'sensitive', label: `Sensitive — ${SENSITIVITY_AUDIENCE.sensitive}` },
  { value: 'domain', label: `Domain — ${SENSITIVITY_AUDIENCE.domain}` },
  { value: 'confidential', label: `Confidential — ${SENSITIVITY_AUDIENCE.confidential}` },
]);

/** Audience label for a sensitivity tier (badges, inbox rows, etc.). */
export function sensitivityAudience(value) {
  return SENSITIVITY_AUDIENCE[value] ?? value;
}

/** Search subjects the viewer may write observations about. */
export async function searchObservationSubjects(q) {
  const r = await api.get(`/api/v1/observations/subjects/?q=${encodeURIComponent(q)}`);
  return r.data?.subjects ?? [];
}

/** People the viewer may tag as recipients at a given sensitivity tier. */
export async function fetchRecipientCandidates(sensitivity) {
  const r = await api.get(
    `/api/v1/observations/recipient-candidates/?sensitivity=${encodeURIComponent(sensitivity)}`,
  );
  return r.data?.persons ?? [];
}

/** Create an observation. */
export async function createObservation({
  subjectIds,
  recipientIds = [],
  body,
  context = '',
  sensitivity = 'normal',
  subjectVisible = false,
  observedAt = null,
}) {
  const payload = {
    subject_ids: subjectIds,
    recipient_ids: recipientIds,
    body,
    context,
    sensitivity,
    subject_visible: subjectVisible,
  };
  if (observedAt) {
    payload.observed_at = observedAt;
  }
  const r = await api.post('/api/v1/observations/', payload);
  return r.data;
}

export async function fetchObservationInbox() {
  const r = await api.get('/api/v1/observations/inbox/');
  return r.data;
}

export async function fetchObservationSent() {
  const r = await api.get('/api/v1/observations/sent/');
  return r.data;
}

/** All observations in the org (admin only). */
export async function fetchObservationAll() {
  const r = await api.get('/api/v1/observations/all/');
  return r.data;
}

export async function fetchObservationThread(id) {
  const r = await api.get(`/api/v1/observations/${id}/`);
  return r.data;
}

export async function replyToObservation(id, body) {
  const r = await api.post(`/api/v1/observations/${id}/replies/`, { body });
  return r.data;
}

export async function archiveObservation(id) {
  const r = await api.post(`/api/v1/observations/${id}/archive/`);
  return r.data;
}

export async function unarchiveObservation(id) {
  const r = await api.post(`/api/v1/observations/${id}/unarchive/`);
  return r.data;
}

export async function fetchObservationUnreadCount() {
  const r = await api.get('/api/v1/observations/unread-count/');
  return r.data?.count ?? 0;
}

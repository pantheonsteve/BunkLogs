/**
 * Maintenance staff flow API client (Step 7_10).
 *
 * Wrappers around `/api/v1/maintenance/*` (Stories 30-35). Transition
 * endpoints are shared with the state machine from Step 7_2 (same URLs);
 * the queue, detail, and notes endpoints are new in this step.
 */

import api from '../api';

/** Maintenance ticket queue with optional filter and closed-view params. */
export async function fetchMaintenanceQueue({
  filter = 'open',
  search,
  dateFrom,
  dateTo,
} = {}) {
  const params = { filter };
  if (search) params.search = search;
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;
  const { data } = await api.get('/api/v1/maintenance/queue/', { params });
  return data;
}

/** Full ticket detail including photos and activity. */
export async function fetchTicketDetail(ticketId) {
  const { data } = await api.get(`/api/v1/maintenance/tickets/${ticketId}/`);
  return data;
}

/** Transition a single ticket (delegates to the 7_2 state machine endpoint). */
export async function transitionTicket(ticketId, { toState, note, reason } = {}) {
  const { data } = await api.post(
    `/api/v1/maintenance/${ticketId}/transition/`,
    { to_state: toState, note, reason },
  );
  return data;
}

/** Correct the last transition within the 5-minute window. */
export async function correctLastTransition(ticketId) {
  const { data } = await api.post(`/api/v1/maintenance/${ticketId}/correct-last/`);
  return data;
}

/** Bulk transition multiple tickets. */
export async function bulkTransitionTickets({ ids, toState, note } = {}) {
  const { data } = await api.post('/api/v1/maintenance/bulk-transition/', {
    ids,
    to_state: toState,
    note,
  });
  return data;
}

/** Add a note to a ticket. */
export async function createTicketNote(ticketId, { body, visibility = 'team_only' } = {}) {
  const { data } = await api.post(
    `/api/v1/maintenance/tickets/${ticketId}/notes/`,
    { body, visibility },
  );
  return data;
}

/** Edit a note within the 24h window. */
export async function editTicketNote(ticketId, noteId, { body, visibility } = {}) {
  const payload = {};
  if (body !== undefined) payload.body = body;
  if (visibility !== undefined) payload.visibility = visibility;
  const { data } = await api.patch(
    `/api/v1/maintenance/tickets/${ticketId}/notes/${noteId}/`,
    payload,
  );
  return data;
}

/** Audience disclosure label for a given visibility value. */
export async function fetchNoteAudience(visibility = 'team_only') {
  const { data } = await api.get('/api/v1/maintenance/notes/audience/', {
    params: { visibility },
  });
  return data;
}

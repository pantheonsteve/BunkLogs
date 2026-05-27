/**
 * Specialist flow API client (Step 7_9).
 *
 * Wrappers around `/api/v1/specialist/*` (Stories 24-29). Mirrors the
 * shape of `api/camperCare.js`: thin axios calls, named exports per endpoint.
 */

import api from '../api';
import { newClientSubmissionId } from './counselor';

export { newClientSubmissionId };

/** Specialist dashboard (Story 24). */
export async function fetchSpecialistDashboard({ noCache = false } = {}) {
  const params = {};
  if (noCache) params.nocache = '1';
  const { data } = await api.get('/api/v1/specialist/dashboard/', { params });
  return data;
}

/**
 * Camper picker (Story 25).
 * @param q      — search query (empty = all campers).
 * @param bunkId — optional bunk ID to restrict results to a single bunk.
 *
 * Response includes a `bunks` array for populating the bunk dropdown.
 */
export async function fetchSpecialistCampers({ q = '', bunkId = null } = {}) {
  const params = {};
  if (q) params.q = q;
  if (bunkId) params.bunk_id = bunkId;
  const { data } = await api.get('/api/v1/specialist/campers/', { params });
  return data;
}

/**
 * Specialist-scoped camper view (Story 28).
 * Returns only the requesting Specialist's notes for the camper.
 * @param dateFrom / dateTo — ISO date strings for date-range filter.
 */
export async function fetchSpecialistCamperView(camperId, { dateFrom, dateTo } = {}) {
  const params = {};
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;
  const { data } = await api.get(`/api/v1/specialist/campers/${camperId}/`, { params });
  return data;
}

/**
 * Submit a specialist note (Story 26).
 * Returns `{ data, status }` so the caller can distinguish 201 from retries.
 */
export async function createSpecialistNote({
  subjectId, body, category = '', isSensitive = false,
  flagForCamperCare = false, language = 'en',
}) {
  const payload = {
    subject_id: subjectId,
    body,
    is_sensitive: isSensitive,
    flag_for_camper_care: flagForCamperCare,
    language,
  };
  if (category) payload.category = category;
  const res = await api.post('/api/v1/specialist/notes/', payload);
  return { data: res.data, status: res.status };
}

/** Edit a specialist note within the 24h window (Story 27). */
export async function patchSpecialistNote(noteId, { body, isSensitive, category, language }) {
  const payload = {};
  if (body !== undefined) payload.body = body;
  if (isSensitive !== undefined) payload.is_sensitive = isSensitive;
  if (category !== undefined) payload.category = category;
  if (language !== undefined) payload.language = language;
  const { data } = await api.patch(`/api/v1/specialist/notes/${noteId}/`, payload);
  return data;
}

/**
 * Resolve the audience disclosure copy for the note form (Story 26.5).
 */
export async function fetchSpecialistNoteAudience({ isSensitive = false } = {}) {
  const params = { is_sensitive: isSensitive ? 'true' : 'false' };
  const { data } = await api.get('/api/v1/specialist/notes/audience/', { params });
  return data;
}

/** Categories enum for specialist notes (Story 26 criterion 2). */
export const SPECIALIST_NOTE_CATEGORIES = Object.freeze([
  { value: 'positive', label: 'Positive observation' },
  { value: 'concern', label: 'Concern' },
  { value: 'milestone', label: 'Skill milestone' },
  { value: 'behavioral', label: 'Behavioral' },
  { value: 'other', label: 'Other' },
]);

/**
 * Submit a Specialist self-reflection (Story 29).
 * Mirrors the CC/UH write contract.
 */
export async function createSpecialistSelfReflection({
  answers, dayOff = false, language = 'en', clientSubmissionId,
}) {
  const payload = {
    day_off: dayOff,
    language,
    client_submission_id: clientSubmissionId,
  };
  if (!dayOff && answers !== undefined) {
    payload.answers = answers;
  }
  const res = await api.post('/api/v1/specialist/self-reflection/', payload);
  return { data: res.data, status: res.status };
}

/** Edit a Specialist self-reflection inside today's edit window. */
export async function patchSpecialistSelfReflection(reflectionId, { answers, dayOff, language }) {
  const payload = {};
  if (answers !== undefined) payload.answers = answers;
  if (dayOff !== undefined) payload.day_off = dayOff;
  if (language !== undefined) payload.language = language;
  const { data } = await api.patch(
    `/api/v1/specialist/self-reflection/${reflectionId}/`,
    payload,
  );
  return data;
}

/** Paginated Specialist self-reflection history. */
export async function fetchSpecialistSelfReflectionHistory({ page = 1, pageSize } = {}) {
  const params = { page };
  if (pageSize) params.page_size = pageSize;
  const { data } = await api.get('/api/v1/specialist/self-reflection/history/', { params });
  return data;
}

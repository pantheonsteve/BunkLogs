/**
 * Unit Head flow API client (Step 7_7).
 *
 * Wrappers around `/api/v1/unit-head/*` (Stories 10-17). Mirrors the
 * shape of `api/counselor.js`: thin axios calls, named exports per
 * endpoint, idempotent self-reflection writes via
 * `client_submission_id`.
 *
 * The Camper Dashboard fetcher is intentionally generic — UH is the
 * first consumer but Camper Care (7_8), Leadership Team (7_12), and
 * Admin (7_13) will hit the same payload contract through their own
 * role-scoped endpoints. We export the shape here so a shared
 * `<CamperDashboard />` component stays role-agnostic.
 */

import api from '../api';
import { newClientSubmissionId } from './counselor';

export { newClientSubmissionId };

/** UH dashboard (Story 10). */
export async function fetchUnitHeadDashboard({ noCache = false } = {}) {
  const params = noCache ? { nocache: '1' } : {};
  const { data } = await api.get('/api/v1/unit-head/dashboard/', { params });
  return data;
}

// NOTE: `fetchBunkDashboard` removed when the bunk dashboard was
// consolidated under `/api/v1/dashboards/group/<id>/`. Use
// `frontend/src/api/dashboards.js#fetchGroupDashboard` instead.

/** Camper Dashboard payload (Story 13) for a camper on a date + range. */
export async function fetchCamperDashboard(camperId, {
  date,
  range = 'last_4_weeks',
  dateStart,
  dateEnd,
} = {}) {
  const params = { range };
  if (date) params.date = date;
  if (dateStart) params.date_start = dateStart;
  if (dateEnd) params.date_end = dateEnd;
  const { data } = await api.get(
    `/api/v1/unit-head/campers/${camperId}/`,
    { params },
  );
  return data;
}

/**
 * Submit a UH self-reflection (Story 16). `dayOff: true` is the
 * canonical shortcut and a complete payload — the server fills
 * answers with `{ day_off: true }` regardless of what's passed in
 * `answers`.
 */
export async function createUnitHeadSelfReflection({
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
  const res = await api.post('/api/v1/unit-head/self-reflection/', payload);
  return { data: res.data, status: res.status };
}

/** Edit a UH self-reflection inside today's window (Story 17). */
export async function patchUnitHeadSelfReflection(reflectionId, {
  answers,
  dayOff,
  language,
}) {
  const payload = {};
  if (answers !== undefined) payload.answers = answers;
  if (dayOff !== undefined) payload.day_off = dayOff;
  if (language !== undefined) payload.language = language;
  const { data } = await api.patch(
    `/api/v1/unit-head/self-reflection/${reflectionId}/`,
    payload,
  );
  return data;
}

/** Paginated UH self-reflection history (Story 17). */
export async function fetchUnitHeadSelfReflectionHistory({ page = 1, pageSize } = {}) {
  const params = { page };
  if (pageSize) params.page_size = pageSize;
  const { data } = await api.get(
    '/api/v1/unit-head/self-reflection/history/',
    { params },
  );
  return data;
}

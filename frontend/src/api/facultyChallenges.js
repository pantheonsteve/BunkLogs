/**
 * Faculty Classroom Challenge Log client — Step 4_8, MA7.
 *
 * Faculty always see the reporting Madrich's identity (semi-anonymity
 * is peer-Madrich only). Mirrors `madrichChallenges.js`'s pattern.
 */
import api from '../api';

const BASE = '/api/v1/faculty/challenges';

/** GET /api/v1/faculty/challenges/?classroom=&status=&session_date= */
export async function fetchFacultyChallenges(orgSlug, { classroom, status, sessionDate } = {}) {
  const params = {};
  if (classroom) params.classroom = classroom;
  if (status) params.status = status;
  if (sessionDate) params.session_date = sessionDate;
  const { data } = await api.get(`${BASE}/`, {
    params,
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** GET /api/v1/faculty/challenges/:id/ */
export async function fetchFacultyChallenge(orgSlug, challengeId) {
  const { data } = await api.get(`${BASE}/${challengeId}/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** POST /api/v1/faculty/challenges/:id/responses/ */
export async function replyToChallenge(orgSlug, challengeId, body) {
  const { data } = await api.post(`${BASE}/${challengeId}/responses/`, { body }, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** PATCH /api/v1/faculty/challenges/:id/ */
export async function updateChallengeStatus(orgSlug, challengeId, status) {
  const { data } = await api.patch(`${BASE}/${challengeId}/`, { status }, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

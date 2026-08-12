/**
 * Madrich Classroom Challenge Log client — Step 4_8, MA7.
 *
 * Mirrors `madrichAvailability.js`'s header/pattern. Separate module
 * from the reflection + availability clients since challenges are a
 * distinct operational channel (semi-anonymous to peers, faculty
 * follow-up), not a reflection.
 */
import api from '../api';

const BASE = '/api/v1/madrich/challenges';

/** GET /api/v1/madrich/challenges/classrooms/ */
export async function fetchClassrooms(orgSlug) {
  const { data } = await api.get(`${BASE}/classrooms/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** GET /api/v1/madrich/challenges/?classroom=&session_date=&mine=1 */
export async function fetchChallenges(orgSlug, { classroom, sessionDate, mine } = {}) {
  const params = {};
  if (classroom) params.classroom = classroom;
  if (sessionDate) params.session_date = sessionDate;
  if (mine) params.mine = '1';
  const { data } = await api.get(`${BASE}/`, {
    params,
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** GET /api/v1/madrich/challenges/:id/ */
export async function fetchChallenge(orgSlug, challengeId) {
  const { data } = await api.get(`${BASE}/${challengeId}/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** POST /api/v1/madrich/challenges/ */
export async function createChallenge(orgSlug, payload) {
  const { data } = await api.post(`${BASE}/`, payload, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** POST /api/v1/madrich/challenges/:id/close/ */
export async function withdrawChallenge(orgSlug, challengeId) {
  await api.post(`${BASE}/${challengeId}/close/`, {}, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
}

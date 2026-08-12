/**
 * Madrich Sunday availability calendar client — Step 4_7.
 *
 * Mirrors `madrich.js`'s header/pattern. Separate module from the
 * reflection client since availability is an operational scheduling
 * signal, not a reflection.
 */
import api from '../api';

const BASE = '/api/v1/madrich/availability';

/** GET /api/v1/madrich/availability/ */
export async function fetchAvailability(orgSlug) {
  const { data } = await api.get(`${BASE}/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** PUT /api/v1/madrich/availability/:sessionDate/ */
export async function upsertAvailability(orgSlug, sessionDate, { status, note = '' }) {
  const { data } = await api.put(`${BASE}/${sessionDate}/`, { status, note }, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** DELETE /api/v1/madrich/availability/:sessionDate/ */
export async function clearAvailability(orgSlug, sessionDate) {
  await api.delete(`${BASE}/${sessionDate}/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
}

/**
 * Self-service Sunday availability client — Step 4_7.
 *
 * One module for both roles: the Madrich and Faculty endpoints are the
 * same shape under a different prefix, so `scope` picks the caller's
 * namespace. Separate from the reflection clients since availability is an
 * operational scheduling signal, not a reflection.
 */
import api from '../api';

const base = (scope) => `/api/v1/${scope}/availability`;

/** GET /api/v1/:scope/availability/ */
export async function fetchAvailability(orgSlug, scope = 'madrich') {
  const { data } = await api.get(`${base(scope)}/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** PUT /api/v1/:scope/availability/:sessionDate/ */
export async function upsertAvailability(orgSlug, sessionDate, { status, note = '' }, scope = 'madrich') {
  const { data } = await api.put(`${base(scope)}/${sessionDate}/`, { status, note }, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** DELETE /api/v1/:scope/availability/:sessionDate/ */
export async function clearAvailability(orgSlug, sessionDate, scope = 'madrich') {
  await api.delete(`${base(scope)}/${sessionDate}/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
}

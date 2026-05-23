/**
 * Madrich (TBE) API client — Step 7_14, Stories 61-65.
 *
 * Mirrors `kitchenStaff.js` but bound to the weekly Madrich endpoints.
 * All requests carry the `X-Organization-Slug` header for multi-tenant
 * routing.
 */
import api from '../api';

const BASE = '/api/v1/madrich';

/** GET /api/v1/madrich/dashboard/ */
export async function fetchDashboard(orgSlug) {
  const { data } = await api.get(`${BASE}/dashboard/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** POST /api/v1/madrich/reflection/ */
export async function submitReflection(orgSlug, payload) {
  const { data } = await api.post(`${BASE}/reflection/`, payload, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** PATCH /api/v1/madrich/reflection/:id/ */
export async function updateReflection(orgSlug, reflectionId, payload) {
  const { data } = await api.patch(`${BASE}/reflection/${reflectionId}/`, payload, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** GET /api/v1/madrich/reflection/history/ */
export async function fetchHistory(orgSlug, { page = 1, pageSize = 12 } = {}) {
  const { data } = await api.get(`${BASE}/reflection/history/`, {
    params: { page, page_size: pageSize },
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/**
 * GET /api/v1/reflections/template-for-me/?role=madrich&language=en
 *
 * The shared template-for-me endpoint resolves to the Madrich weekly
 * template via the viewer's active Membership; we pass `role=madrich`
 * explicitly for the elevated-actor codepath (admins viewing on behalf
 * of a Madrich).
 */
export async function fetchTemplate(orgSlug, language = 'en') {
  const { data } = await api.get('/api/v1/reflections/template-for-me/', {
    params: { role: 'madrich', language },
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

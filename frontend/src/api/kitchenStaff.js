/**
 * Kitchen Staff API client — Step 7_11, Stories 37-44.
 *
 * All requests include the organization slug header required by the
 * multi-tenant middleware.  Callers should pass `orgSlug` from context.
 */
import api from '../api';

const BASE = '/api/v1/kitchen-staff';

/** GET /api/v1/kitchen-staff/dashboard/ */
export async function fetchDashboard(orgSlug) {
  const { data } = await api.get(`${BASE}/dashboard/`, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** POST /api/v1/kitchen-staff/reflection/ */
export async function submitReflection(orgSlug, payload) {
  const { data } = await api.post(`${BASE}/reflection/`, payload, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** PATCH /api/v1/kitchen-staff/reflection/:id/ */
export async function updateReflection(orgSlug, reflectionId, payload) {
  const { data } = await api.patch(`${BASE}/reflection/${reflectionId}/`, payload, {
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** GET /api/v1/kitchen-staff/reflection/history/ */
export async function fetchHistory(orgSlug, { page = 1, pageSize = 14 } = {}) {
  const { data } = await api.get(`${BASE}/reflection/history/`, {
    params: { page, page_size: pageSize },
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

/** GET /api/v1/reflections/template-for-me/?role=kitchen_staff&language=xx */
export async function fetchTemplate(orgSlug, language = 'en') {
  const { data } = await api.get('/api/v1/reflections/template-for-me/', {
    params: { role: 'kitchen_staff', language },
    headers: { 'X-Organization-Slug': orgSlug },
  });
  return data;
}

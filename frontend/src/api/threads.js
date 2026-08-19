/**
 * Entry threads and the cohort feed — Step 4_9.
 *
 * Role-agnostic on purpose: the same endpoints back the Madrich, Faculty, and
 * Director surfaces, and the backend decides what each caller may see.
 */
import api from '../api';

const THREADS = '/api/v1/threads';
const COHORT = '/api/v1/cohort';

const orgHeaders = (orgSlug) => ({ headers: { 'X-Organization-Slug': orgSlug } });

/** GET /api/v1/threads/ */
export async function fetchThreads(orgSlug, {
  routesTo, resolved, subjectPerson, assignmentGroup, unread, page = 1, pageSize = 20,
} = {}) {
  const params = { page, page_size: pageSize };
  if (routesTo) params.routes_to = routesTo;
  if (resolved !== undefined) params.resolved = resolved;
  if (subjectPerson) params.subject_person = subjectPerson;
  if (assignmentGroup) params.assignment_group = assignmentGroup;
  if (unread) params.unread = 'true';
  const { data } = await api.get(`${THREADS}/`, { params, ...orgHeaders(orgSlug) });
  return data;
}

/** GET /api/v1/threads/{id}/ — also marks the thread read. */
export async function fetchThread(orgSlug, threadId) {
  const { data } = await api.get(`${THREADS}/${threadId}/`, orgHeaders(orgSlug));
  return data;
}

/** POST /api/v1/threads/{id}/messages/ */
export async function postThreadMessage(orgSlug, threadId, body) {
  const { data } = await api.post(
    `${THREADS}/${threadId}/messages/`, { body }, orgHeaders(orgSlug),
  );
  return data;
}

/** POST /api/v1/threads/{id}/read/ */
export async function markThreadRead(orgSlug, threadId) {
  const { data } = await api.post(`${THREADS}/${threadId}/read/`, {}, orgHeaders(orgSlug));
  return data;
}

/** POST /api/v1/threads/{id}/resolve/ */
export async function resolveThread(orgSlug, threadId) {
  const { data } = await api.post(`${THREADS}/${threadId}/resolve/`, {}, orgHeaders(orgSlug));
  return data;
}

/** GET /api/v1/cohort/feed/ */
export async function fetchCohortFeed(orgSlug, { page = 1, pageSize = 20 } = {}) {
  const { data } = await api.get(`${COHORT}/feed/`, {
    params: { page, page_size: pageSize },
    ...orgHeaders(orgSlug),
  });
  return data;
}

/** GET /api/v1/cohort/members/ */
export async function fetchCohortMembers(orgSlug) {
  const { data } = await api.get(`${COHORT}/members/`, orgHeaders(orgSlug));
  return data;
}

/** POST /api/v1/cohort/shares/{id}/react/ — toggles the caller's like. */
export async function toggleShareLike(orgSlug, shareId) {
  const { data } = await api.post(
    `${COHORT}/shares/${shareId}/react/`, {}, orgHeaders(orgSlug),
  );
  return data;
}

/** POST /api/v1/cohort/shares/{id}/hide/ — admin only. */
export async function setShareHidden(orgSlug, shareId, hidden) {
  const { data } = await api.post(
    `${COHORT}/shares/${shareId}/hide/`, { hidden }, orgHeaders(orgSlug),
  );
  return data;
}

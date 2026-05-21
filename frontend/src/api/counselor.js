/**
 * Counselor flow API client (Step 7_6).
 *
 * Thin wrappers around the `/api/v1/counselor/*` endpoints built in
 * `7_6b` (reads) and `7_6c` (writes). Centralized so each page doesn't
 * hand-roll URLs / payloads and so the offline-queue work in 7_6e can
 * intercept submission paths in one place.
 *
 * Convention: every write helper takes (or generates) a
 * `client_submission_id` UUID for backend idempotency. Callers should
 * persist the UUID until the server confirms the write so retries land
 * on the same row instead of duplicating data.
 */

import api from '../api';

/**
 * Generate a UUIDv4 for `client_submission_id`.
 *
 * Browsers running on `https://` (or localhost) expose `crypto.randomUUID`.
 * We fall back to a Math.random()-based polyfill for very old runtimes /
 * jsdom in test mode so unit tests don't have to stub `globalThis.crypto`.
 */
export function newClientSubmissionId() {
  if (typeof globalThis !== 'undefined'
      && globalThis.crypto
      && typeof globalThis.crypto.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  // RFC4122 v4 fallback. Not cryptographically strong; only used in
  // environments where Web Crypto is missing.
  const r = () => Math.floor(Math.random() * 0xffff).toString(16).padStart(4, '0');
  const time = Date.now().toString(16).padStart(12, '0');
  return `${time.slice(0, 8)}-${time.slice(8, 12)}-4${r().slice(0, 3)}-${
    ((Math.floor(Math.random() * 4) + 8).toString(16))}${r().slice(0, 3)}-${r()}${r()}${r()}`;
}

/** Counselor dashboard payload (Story 2 + 9). */
export async function fetchCounselorDashboard({ noCache = false } = {}) {
  const params = noCache ? { nocache: '1' } : {};
  const { data } = await api.get('/api/v1/counselor/dashboard/', { params });
  return data;
}

/**
 * Camper reflection roster for `date` (defaults to org "today").
 * Returns `{ date, editable, template, bunks: [{ id, name, covered, total, campers, off_camp }] }`.
 */
export async function fetchCamperReflections({ date } = {}) {
  const params = date ? { date } : {};
  const { data } = await api.get('/api/v1/counselor/camper-reflections/', { params });
  return data;
}

/** Submit a new camper reflection (Story 3). */
export async function createCamperReflection({
  subjectId,
  assignmentGroupId,
  answers,
  language = 'en',
  teamVisibility = 'team',
  clientSubmissionId,
}) {
  const payload = {
    subject_id: subjectId,
    assignment_group_id: assignmentGroupId,
    answers,
    language,
    team_visibility: teamVisibility,
    client_submission_id: clientSubmissionId,
  };
  const res = await api.post('/api/v1/counselor/camper-reflections/', payload);
  return { data: res.data, status: res.status };
}

/** Edit a camper reflection within today's window (Story 4). */
export async function patchCamperReflection(reflectionId, {
  answers,
  language,
  teamVisibility,
}) {
  const payload = {};
  if (answers !== undefined) payload.answers = answers;
  if (language !== undefined) payload.language = language;
  if (teamVisibility !== undefined) payload.team_visibility = teamVisibility;
  const { data } = await api.patch(
    `/api/v1/counselor/camper-reflections/${reflectionId}/`,
    payload,
  );
  return data;
}

/**
 * Fetch a template by ID — used to load the full schema once the camper
 * reflection list endpoint has handed us back ``template.id``. We don't
 * hit ``template-for-me`` for camper reflections because that resolver
 * uses ``subject_mode='self'`` semantics; the camper bunk-roster template
 * is selected server-side by ``CamperReflectionListView`` and we just
 * need its ``schema`` to render the form.
 */
export async function fetchTemplateById(templateId) {
  const { data } = await api.get(`/api/v1/templates/${templateId}/`);
  return data;
}

/** Read a single reflection (for prefilling the edit form). */
export async function fetchReflection(reflectionId) {
  const { data } = await api.get(`/api/v1/reflections/${reflectionId}/`);
  return data;
}

/**
 * Static audience labels for a camper reflection (write-time disclosure).
 *
 * The backend computes the canonical list from
 * ``audience_labels(ContentType.CAMPER_REFLECTION, ...)`` and returns it
 * on each write response, but at form-render time we don't yet have a
 * server-computed value. The set is constant for camper reflections
 * regardless of ``team_visibility`` (no sensitive override is configured
 * in ``_SENSITIVE_AUDIENCES`` for this content type), so we mirror the
 * default list here in alphabetical order to match the server output.
 *
 * Keep in sync with ``bunk_logs/core/content_visibility.py``.
 */
export const CAMPER_REFLECTION_AUDIENCE = Object.freeze([
  'Admin',
  'Camper Care',
  'Counselor',
  'Leadership Team',
  'Unit Head',
]);

/**
 * Static audience labels for a counselor self-reflection.
 *
 * Mirrors ``audience_labels(ContentType.COUNSELOR_SELF_REFLECTION)`` from
 * ``bunk_logs/core/content_visibility.py``. No ``supports_privacy`` toggle
 * applies to the seeded counselor template, so this set is fixed.
 */
export const COUNSELOR_SELF_REFLECTION_AUDIENCE = Object.freeze([
  'Admin',
  'Counselor',
  'Leadership Team',
  'Unit Head',
]);

// ---------------------------------------------------------------------------
// Self-reflection (Stories 5 + 6)
// ---------------------------------------------------------------------------

/**
 * Submit today's self-reflection (Story 5).
 *
 * Two payload shapes:
 *
 *   * ``{ dayOff: true }`` — shortcut. The server fills ``answers`` with
 *     ``{"day_off": true}`` regardless of what we send, so the offline
 *     queue can record a day off without knowing the schema.
 *   * ``{ dayOff: false, answers: {...} }`` — full submission. ``answers``
 *     must validate against the seeded counselor template schema.
 *
 * The view also accepts an explicit ``team_visibility`` but the seeded
 * template ships ``supports_privacy=false``, so the server always stores
 * ``team`` for self-reflections. We don't send the field to keep the
 * payload minimal.
 */
export async function createSelfReflection({
  dayOff = false,
  answers,
  language = 'en',
  clientSubmissionId,
}) {
  const payload = {
    day_off: !!dayOff,
    language,
    client_submission_id: clientSubmissionId,
  };
  if (!dayOff) {
    payload.answers = answers || {};
  }
  const res = await api.post('/api/v1/counselor/self-reflection/', payload);
  return { data: res.data, status: res.status };
}

/**
 * Patch an existing self-reflection within today's edit window (Story 6).
 *
 * ``dayOff`` is a tri-state: ``true`` flips to the day-off shortcut and
 * blanks the rest of the answers; ``false`` flips back to a normal entry
 * (and requires ``answers``); ``undefined`` leaves the shortcut state
 * untouched. The view enforces the rollover-aware edit window and returns
 * 403 once "today" passes.
 */
export async function patchSelfReflection(reflectionId, {
  dayOff,
  answers,
  language,
}) {
  const payload = {};
  if (dayOff !== undefined) payload.day_off = !!dayOff;
  if (answers !== undefined) payload.answers = answers;
  if (language !== undefined) payload.language = language;
  const { data } = await api.patch(
    `/api/v1/counselor/self-reflection/${reflectionId}/`,
    payload,
  );
  return data;
}

/**
 * Paginated history view of the viewer's own self-reflections (Story 6).
 *
 * Returns one row per calendar day in the page window — including "no
 * submission" gap rows — so the client can render Story 6 criterion 6
 * without inferring missing dates client-side.
 */
export async function fetchSelfReflectionHistory({ page = 1, pageSize } = {}) {
  const params = { page };
  if (pageSize) params.page_size = pageSize;
  const { data } = await api.get('/api/v1/counselor/self-reflection/history/', {
    params,
  });
  return data;
}

/**
 * Subject notes API client (Prompt 3.15/3.16).
 *
 * Thin wrappers around `/api/v1/subjects/{person_id}/notes/*`.
 */

import api from '../api';

export const VISIBILITY_OPTIONS = Object.freeze([
  { value: 'supervisors_only', label: 'Supervisors only (default)' },
  { value: 'team', label: 'Team — all with dashboard access' },
  { value: 'domain_only', label: 'Domain specialists and above' },
  { value: 'admin_only', label: 'Admin only' },
]);

/** Create a new SubjectNote. Returns `{ data, status }`. */
export async function createSubjectNote(personId, {
  body,
  context = '',
  visibility = 'supervisors_only',
  isSensitive = false,
  subjectVisible = false,
}) {
  const res = await api.post(`/api/v1/subjects/${personId}/notes/`, {
    body,
    context,
    visibility,
    is_sensitive: isSensitive,
    subject_visible: subjectVisible,
  });
  return { data: res.data, status: res.status };
}

/** Append an amendment to an existing immutable note. */
export async function amendSubjectNote(personId, noteId, { body }) {
  const res = await api.post(
    `/api/v1/subjects/${personId}/notes/${noteId}/amend/`,
    { body },
  );
  return { data: res.data, status: res.status };
}

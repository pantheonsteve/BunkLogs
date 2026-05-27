/**
 * Shared note-reply API helpers.
 *
 * Two reply surfaces:
 *   - Camper notes (core.Note, types specialist + camper_care):
 *       GET|POST /api/v1/camper-notes/<noteId>/replies/
 *   - Subject notes (SubjectNote, subject dashboard):
 *       GET|POST /api/v1/subjects/<personId>/notes/<noteId>/replies/
 *
 * Reply shape (both types):
 *   { id, author_name, author_role, body, created_at }
 */

import api from '../api';

/**
 * List replies for a camper note (specialist or camper_care).
 */
export async function fetchCamperNoteReplies(noteId) {
  const { data } = await api.get(`/api/v1/camper-notes/${noteId}/replies/`);
  return data;
}

/**
 * Post a reply to a camper note (specialist or camper_care).
 * Returns the created reply object.
 */
export async function postCamperNoteReply(noteId, body) {
  const { data } = await api.post(`/api/v1/camper-notes/${noteId}/replies/`, { body });
  return data;
}

/**
 * List replies for a SubjectNote (subject dashboard).
 */
export async function fetchSubjectNoteReplies(personId, noteId) {
  const { data } = await api.get(`/api/v1/subjects/${personId}/notes/${noteId}/replies/`);
  return data;
}

/**
 * Post a reply to a SubjectNote.
 * Returns the created reply object.
 */
export async function postSubjectNoteReply(personId, noteId, body) {
  const { data } = await api.post(
    `/api/v1/subjects/${personId}/notes/${noteId}/replies/`,
    { body },
  );
  return data;
}

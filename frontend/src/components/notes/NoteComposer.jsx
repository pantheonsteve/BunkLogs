/**
 * NoteComposer — modal/page for composing a new note (Story 66).
 *
 * Can be opened standalone (from NotesPage compose button) or pre-filled
 * via cross-reference paths (Stories 69, 70). Supports local draft
 * auto-save to localStorage (30-second interval + on blur).
 *
 * Props:
 *   initialDraft  — optional pre-filled fields from cross-reference endpoints
 *   onClose       — called when the modal is dismissed (sent or cancelled)
 *   onSent        — called after a successful submission with the new note data
 */
import { useEffect, useRef, useState } from 'react';
import api from '../../api';
import AudiencePicker from './AudiencePicker';
import SourceReferenceIndicator from './SourceReferenceIndicator';

const DRAFT_KEY_PREFIX = 'note_draft_';
const AUTO_SAVE_INTERVAL = 30000;

function loadDraft(draftId) {
  try {
    return JSON.parse(localStorage.getItem(`${DRAFT_KEY_PREFIX}${draftId}`)) ?? null;
  } catch {
    return null;
  }
}

function saveDraft(draftId, data) {
  try {
    localStorage.setItem(`${DRAFT_KEY_PREFIX}${draftId}`, JSON.stringify(data));
  } catch {}
}

function clearDraft(draftId) {
  try {
    localStorage.removeItem(`${DRAFT_KEY_PREFIX}${draftId}`);
  } catch {}
}

export default function NoteComposer({ initialDraft = null, onClose, onSent }) {
  const draftId = useRef(initialDraft?.draftId ?? `new_${Date.now()}`).current;
  const savedDraft = loadDraft(draftId);

  const [audience, setAudience] = useState(
    initialDraft?.audience ?? savedDraft?.audience ?? [],
  );
  const [subject, setSubject] = useState(
    initialDraft?.subject ?? savedDraft?.subject ?? '',
  );
  const [body, setBody] = useState(
    initialDraft?.body ?? savedDraft?.body ?? '',
  );
  const [sourceContentType] = useState(initialDraft?.source_content_type ?? '');
  const [sourceObjectId] = useState(initialDraft?.source_object_id ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [candidates, setCandidates] = useState({ persons: [], bunks: [] });

  useEffect(() => {
    let cancelled = false;
    api.get('/api/v1/notes/audience-candidates/').then(r => {
      if (!cancelled) setCandidates(r.data ?? { persons: [], bunks: [] });
    }).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  // Auto-save every 30s
  useEffect(() => {
    const id = setInterval(() => {
      saveDraft(draftId, { audience, subject, body });
    }, AUTO_SAVE_INTERVAL);
    return () => clearInterval(id);
  }, [draftId, audience, subject, body]);

  function handleBlur() {
    saveDraft(draftId, { audience, subject, body });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (audience.length === 0) {
      setError('Please select at least one audience member.');
      return;
    }
    if (!subject.trim()) {
      setError('Subject is required.');
      return;
    }
    if (!body.trim()) {
      setError('Body is required.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        audience,
        subject: subject.trim(),
        body: body.trim(),
        source_content_type: sourceContentType,
        source_object_id: sourceObjectId,
      };
      const r = await api.post('/api/v1/notes/', payload);
      clearDraft(draftId);
      onSent?.(r.data);
      onClose?.();
    } catch (err) {
      const detail =
        err.response?.data?.audience?.[0] ??
        err.response?.data?.detail ??
        'Failed to send note. Please try again.';
      setError(detail);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Compose a note"
    >
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">New note</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5 overflow-y-auto flex-1">
          {/* Source reference indicator (cross-reference path) */}
          {sourceContentType && (
            <SourceReferenceIndicator
              sourceContentType={sourceContentType}
              sourceObjectId={sourceObjectId}
            />
          )}

          {/* Audience — shown first (criterion 3: audience-first UX) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              To <span className="text-red-500">*</span>
            </label>
            <AudiencePicker
              value={audience}
              onChange={setAudience}
              persons={candidates.persons}
              bunks={candidates.bunks}
            />
          </div>

          {/* Subject */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Subject <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={subject}
              onChange={e => setSubject(e.target.value)}
              onBlur={handleBlur}
              maxLength={200}
              placeholder="What's this about?"
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>

          {/* Body */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Message <span className="text-red-500">*</span>
            </label>
            <textarea
              value={body}
              onChange={e => setBody(e.target.value)}
              onBlur={handleBlur}
              maxLength={10000}
              rows={6}
              placeholder="Write your message…"
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-violet-500 focus:border-transparent resize-none"
            />
            <p className="text-xs text-gray-400 text-right mt-0.5">{body.length}/10000</p>
          </div>

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="note-composer-form"
            onClick={handleSubmit}
            disabled={submitting}
            className="px-4 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? 'Sending…' : 'Send note'}
          </button>
        </div>
      </div>
    </div>
  );
}

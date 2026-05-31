/**
 * SubjectNoteComposer — modal to compose a quick SubjectNote from anywhere.
 *
 * Subject typeahead is bound to GET /api/v1/subject-notes/subjects/?q=...
 * (the viewer's writeable subject set). Submission reuses the existing
 * createSubjectNote helper that POSTs /api/v1/subjects/{id}/notes/.
 */
import { useEffect, useRef, useState } from 'react';
import api from '../../api';
import { VISIBILITY_OPTIONS, createSubjectNote } from '../../api/subjects';

const SEARCH_DEBOUNCE_MS = 200;

export default function SubjectNoteComposer({ onClose, onSent }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [subject, setSubject] = useState(null);
  const [body, setBody] = useState('');
  const [context, setContext] = useState('');
  const [visibility, setVisibility] = useState('supervisors_only');
  const [subjectVisible, setSubjectVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (subject) return undefined;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setResults([]);
      setSearching(false);
      return undefined;
    }
    setSearching(true);
    debounceRef.current = setTimeout(() => {
      api.get(`/api/v1/subject-notes/subjects/?q=${encodeURIComponent(query.trim())}`)
        .then(r => setResults(r.data?.subjects ?? []))
        .catch(() => setResults([]))
        .finally(() => setSearching(false));
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(debounceRef.current);
  }, [query, subject]);

  function pickSubject(s) {
    setSubject(s);
    setQuery(s.full_name);
    setResults([]);
  }

  function clearSubject() {
    setSubject(null);
    setQuery('');
    setResults([]);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!subject) {
      setError('Please pick a subject.');
      return;
    }
    if (!body.trim()) {
      setError('Note body is required.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const { data } = await createSubjectNote(subject.id, {
        body: body.trim(),
        context: context.trim(),
        visibility,
        subjectVisible,
      });
      onSent?.({ ...data, subject });
      onClose?.();
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to save note.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Compose a subject note"
    >
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">New subject note</h2>
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
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              About <span className="text-rose-500">*</span>
            </label>
            {subject ? (
              <div className="flex items-center justify-between rounded-md border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20 px-3 py-2">
                <span className="text-sm font-medium text-indigo-900 dark:text-indigo-100">
                  {subject.full_name}
                </span>
                <button
                  type="button"
                  onClick={clearSubject}
                  className="text-xs text-indigo-600 dark:text-indigo-300 hover:underline"
                >
                  Change
                </button>
              </div>
            ) : (
              <div className="relative">
                <input
                  type="text"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Search by name…"
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  data-testid="subject-note-composer-search"
                />
                {(searching || results.length > 0) && (
                  <ul
                    className="absolute z-10 mt-1 w-full rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-lg max-h-56 overflow-y-auto"
                    data-testid="subject-note-composer-results"
                  >
                    {searching && results.length === 0 && (
                      <li className="px-3 py-2 text-xs text-gray-400">Searching…</li>
                    )}
                    {!searching && results.length === 0 && query.trim() && (
                      <li className="px-3 py-2 text-xs text-gray-400">No matches.</li>
                    )}
                    {results.map(s => (
                      <li key={s.id}>
                        <button
                          type="button"
                          onClick={() => pickSubject(s)}
                          className="block w-full text-left px-3 py-2 text-sm hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-gray-800 dark:text-gray-100"
                        >
                          {s.full_name}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Note <span className="text-rose-500">*</span>
            </label>
            <textarea
              value={body}
              onChange={e => setBody(e.target.value)}
              rows={5}
              placeholder="Write your observation…"
              className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-y"
              data-testid="subject-note-composer-body"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Context tag <span className="text-gray-400">(optional)</span>
              </label>
              <input
                type="text"
                value={context}
                onChange={e => setContext(e.target.value)}
                maxLength={64}
                placeholder="e.g. swim_instruction"
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Visibility
              </label>
              <select
                value={visibility}
                onChange={e => setVisibility(e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                {VISIBILITY_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <label className="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={subjectVisible}
              onChange={e => setSubjectVisible(e.target.checked)}
              className="rounded border-gray-300 dark:border-gray-600 text-indigo-600"
            />
            Make visible to the subject on their dashboard
          </label>

          {error && (
            <p className="text-sm text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 rounded-md px-3 py-2">
              {error}
            </p>
          )}
        </form>

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
            onClick={handleSubmit}
            disabled={submitting}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="subject-note-composer-submit"
          >
            {submitting ? 'Saving…' : 'Save note'}
          </button>
        </div>
      </div>
    </div>
  );
}

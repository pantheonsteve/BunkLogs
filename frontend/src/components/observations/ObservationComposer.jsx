/**
 * ObservationComposer — modal to compose an Observation (Step 7_23).
 *
 * Evolves SubjectNoteComposer with:
 *   - multi-subject picker (chips)
 *   - recipient picker bound to recipient-candidates/?sensitivity=
 *   - sensitivity selector that re-filters recipients on change
 *   - context tag + subject_visible toggle
 */
import { useEffect, useRef, useState } from 'react';
import {
  SENSITIVITY_OPTIONS,
  createObservation,
  fetchRecipientCandidates,
  searchObservationSubjects,
} from '../../api/observations';

const SEARCH_DEBOUNCE_MS = 200;

function defaultObservedAtLocal() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

function localDatetimeToIso(local) {
  if (!local) return null;
  return new Date(local).toISOString();
}

export default function ObservationComposer({ onClose, onSent, initialSubjects = [] }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [subjects, setSubjects] = useState(initialSubjects);
  const [body, setBody] = useState('');
  const [observedAtLocal, setObservedAtLocal] = useState(defaultObservedAtLocal);
  const [context, setContext] = useState('');
  const [sensitivity, setSensitivity] = useState('normal');
  const [subjectVisible, setSubjectVisible] = useState(false);
  const [candidates, setCandidates] = useState([]);
  const [recipientIds, setRecipientIds] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const debounceRef = useRef(null);

  // Subject typeahead.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setResults([]);
      setSearching(false);
      return undefined;
    }
    setSearching(true);
    debounceRef.current = setTimeout(() => {
      searchObservationSubjects(query.trim())
        .then(setResults)
        .catch(() => setResults([]))
        .finally(() => setSearching(false));
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  // Re-fetch recipient candidates whenever the sensitivity tier changes.
  useEffect(() => {
    let cancelled = false;
    fetchRecipientCandidates(sensitivity)
      .then((people) => {
        if (cancelled) return;
        setCandidates(people);
        // Drop any selected recipients that no longer clear the tier.
        const allowed = new Set(people.map((p) => p.id));
        setRecipientIds((prev) => prev.filter((id) => allowed.has(id)));
      })
      .catch(() => {
        if (!cancelled) setCandidates([]);
      });
    return () => {
      cancelled = true;
    };
  }, [sensitivity]);

  function addSubject(s) {
    setSubjects((prev) => (prev.some((p) => p.id === s.id) ? prev : [...prev, s]));
    setQuery('');
    setResults([]);
  }

  function removeSubject(id) {
    setSubjects((prev) => prev.filter((p) => p.id !== id));
  }

  function toggleRecipient(id) {
    setRecipientIds((prev) => (prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (subjects.length === 0) {
      setError('Please add at least one subject.');
      return;
    }
    if (!body.trim()) {
      setError('Observation body is required.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const data = await createObservation({
        subjectIds: subjects.map((s) => s.id),
        recipientIds,
        body: body.trim(),
        context: context.trim(),
        sensitivity,
        subjectVisible,
        observedAt: localDatetimeToIso(observedAtLocal),
      });
      onSent?.(data);
      onClose?.();
    } catch (err) {
      const detail = err.response?.data;
      setError(
        (detail && (detail.detail || detail.recipient_ids || detail.subject_ids))
          || 'Failed to save observation.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Compose an observation"
    >
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">New observation</h2>
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
          {/* Subjects (multi) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              About <span className="text-rose-500">*</span>
            </label>
            {subjects.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2" data-testid="observation-subject-chips">
                {subjects.map((s) => (
                  <span
                    key={s.id}
                    className="inline-flex items-center gap-1 rounded-full bg-indigo-50 dark:bg-indigo-900/20 px-3 py-1 text-xs font-medium text-indigo-800 dark:text-indigo-100"
                  >
                    {s.full_name}
                    <button
                      type="button"
                      onClick={() => removeSubject(s.id)}
                      className="text-indigo-500 hover:text-indigo-700"
                      aria-label={`Remove ${s.full_name}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div className="relative">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by name…"
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                data-testid="observation-composer-search"
              />
              {(searching || results.length > 0) && (
                <ul
                  className="absolute z-10 mt-1 w-full rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-lg max-h-56 overflow-y-auto"
                  data-testid="observation-composer-results"
                >
                  {searching && results.length === 0 && (
                    <li className="px-3 py-2 text-xs text-gray-400">Searching…</li>
                  )}
                  {results.map((s) => (
                    <li key={s.id}>
                      <button
                        type="button"
                        onClick={() => addSubject(s)}
                        className="block w-full text-left px-3 py-2 text-sm hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-gray-800 dark:text-gray-100"
                      >
                        {s.full_name}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Body */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Observation <span className="text-rose-500">*</span>
            </label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={5}
              maxLength={10000}
              placeholder="Write your observation…"
              className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-y"
              data-testid="observation-composer-body"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              When did this happen?
            </label>
            <input
              type="datetime-local"
              value={observedAtLocal}
              onChange={(e) => setObservedAtLocal(e.target.value)}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              data-testid="observation-composer-observed-at"
            />
          </div>

          {/* Context + Sensitivity */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Context tag <span className="text-gray-400">(optional)</span>
              </label>
              <input
                type="text"
                value={context}
                onChange={(e) => setContext(e.target.value)}
                maxLength={64}
                placeholder="e.g. swim_instruction"
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Sensitivity
              </label>
              <select
                value={sensitivity}
                onChange={(e) => setSensitivity(e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                data-testid="observation-composer-sensitivity"
              >
                {SENSITIVITY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Recipients (sensitivity-filtered) */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Notify <span className="text-gray-400">(optional)</span>
            </label>
            {candidates.length === 0 ? (
              <p className="text-xs text-gray-400" data-testid="observation-no-candidates">
                No one clears this sensitivity tier.
              </p>
            ) : (
              <div
                className="max-h-40 overflow-y-auto rounded-md border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700"
                data-testid="observation-recipient-list"
              >
                {candidates.map((p) => (
                  <label
                    key={p.id}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-800 dark:text-gray-100 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/40"
                  >
                    <input
                      type="checkbox"
                      checked={recipientIds.includes(p.id)}
                      onChange={() => toggleRecipient(p.id)}
                      className="rounded border-gray-300 dark:border-gray-600 text-indigo-600"
                    />
                    {p.full_name}
                  </label>
                ))}
              </div>
            )}
          </div>

          <label className="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={subjectVisible}
              onChange={(e) => setSubjectVisible(e.target.checked)}
              className="rounded border-gray-300 dark:border-gray-600 text-indigo-600"
            />
            Make visible to the subject on their Profile
          </label>

          {error && (
            <p className="text-sm text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 rounded-md px-3 py-2">
              {String(error)}
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
            data-testid="observation-composer-submit"
          >
            {submitting ? 'Saving…' : 'Save observation'}
          </button>
        </div>
      </div>
    </div>
  );
}

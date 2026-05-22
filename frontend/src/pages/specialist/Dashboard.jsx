/**
 * Specialist dashboard — Step 7_9, Story 24.
 *
 * Exactly three top-level elements (criterion 3):
 *   1. Write a camper note — opens the camper picker.
 *   2. My reflection — daily self-reflection card.
 *   3. My recent notes — top 10 chronological, with Show older expansion.
 *
 * Header: user name, role label (from membership tags), active program.
 * No operational signals, no bunk lists, no flag aggregates.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchSpecialistDashboard } from '../../api/specialist';

const REFRESH_INTERVAL_MS = 60_000;

function SelfReflectionCard({ selfReflection }) {
  if (!selfReflection) return null;
  const { state, reflection_id, template_id, editable } = selfReflection;

  if (state === 'no_template') {
    return (
      <section
        aria-label="My reflection"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="sp-self-reflection-card"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-1">My reflection</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">No reflection template configured.</p>
      </section>
    );
  }

  const isComplete = state === 'complete' || state === 'day_off';
  const editPath = editable && reflection_id
    ? `/specialist/self-reflection/${reflection_id}/edit`
    : '/specialist/self-reflection/new';

  return (
    <section
      aria-label="My reflection"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="sp-self-reflection-card"
    >
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">My reflection</h2>
        {isComplete ? (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200">
            {state === 'day_off' ? 'Day off' : 'Done'}
          </span>
        ) : (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
            Pending
          </span>
        )}
      </div>
      <Link
        to={editPath}
        className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
      >
        {isComplete ? (editable ? 'Edit reflection' : 'View reflection') : 'Start reflection'}
      </Link>
    </section>
  );
}

function NoteRow({ note }) {
  const categoryLabel = note.category
    ? note.category.charAt(0).toUpperCase() + note.category.slice(1)
    : null;
  const date = note.created_at
    ? new Date(note.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : '';

  return (
    <li className="py-3 first:pt-0 last:pb-0 border-b border-gray-100 dark:border-gray-700 last:border-0">
      <Link
        to={`/specialist/campers/${note.subject_id}`}
        className="flex items-start gap-2 group"
        data-testid={`sp-note-row-${note.id}`}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {note.subject_name}
            </span>
            {note.bunk_name && (
              <span className="text-xs text-gray-500 dark:text-gray-400">· {note.bunk_name}</span>
            )}
            {categoryLabel && (
              <span className="text-xs text-gray-500 dark:text-gray-400">· {categoryLabel}</span>
            )}
            {note.is_sensitive && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-200">
                Sensitive
              </span>
            )}
            {note.flag_raised && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-200">
                Flagged
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5 line-clamp-1">
            {note.body_preview}
          </p>
        </div>
        <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0 mt-0.5">{date}</span>
      </Link>
    </li>
  );
}

export default function SpecialistDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const load = useCallback(async (force = false) => {
    try {
      const result = await fetchSpecialistDashboard({ noCache: force });
      setData(result);
      setError('');
    } catch (err) {
      setError(err?.message || 'Could not load dashboard.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(() => load(), REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [load]);

  if (loading) {
    return (
      <div className="px-4 py-6 max-w-lg mx-auto" data-testid="sp-dashboard-loading">
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-6 max-w-lg mx-auto">
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">{error}</p>
        <button
          onClick={() => load(true)}
          className="mt-2 text-sm text-blue-600 dark:text-blue-400 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  const { header, self_reflection, recent_notes = [] } = data || {};

  return (
    <div className="px-4 py-6 max-w-lg mx-auto space-y-5" data-testid="sp-dashboard">
      {/* Header */}
      <header>
        <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {header?.role_label} · {header?.program_name}
        </p>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mt-0.5">
          {header?.name}
        </h1>
      </header>

      {/* 1. Write a camper note */}
      <button
        type="button"
        onClick={() => navigate('/specialist/notes/new')}
        className="w-full flex items-center justify-between rounded-xl border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20 px-4 py-3 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
        data-testid="sp-write-note-btn"
      >
        <span>Write a camper note</span>
        <span aria-hidden="true">→</span>
      </button>

      {/* 2. My reflection */}
      <SelfReflectionCard selfReflection={self_reflection} />

      {/* 3. My recent notes */}
      <section aria-label="My recent notes" data-testid="sp-recent-notes">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-3">
          My recent notes
        </h2>
        {recent_notes.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No notes yet. Use the button above to write your first.
          </p>
        ) : (
          <>
            <ul className="divide-y divide-gray-100 dark:divide-gray-700">
              {recent_notes.map((note) => (
                <NoteRow key={note.id} note={note} />
              ))}
            </ul>
            {recent_notes.length >= 10 && (
              <Link
                to="/specialist/notes/history"
                className="block mt-3 text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                Show older notes
              </Link>
            )}
          </>
        )}
      </section>
    </div>
  );
}

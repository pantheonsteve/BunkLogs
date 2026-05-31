/**
 * SubjectNotesPage — global feed of recent SubjectNotes the viewer can see.
 *
 * Route: /subject-notes. Mounted under AppLayout, which owns the chrome.
 * Compose button opens SubjectNoteComposer; submit posts via createSubjectNote
 * and the new note is prepended to the feed.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api';
import SubjectNoteComposer from '../../components/subject-notes/SubjectNoteComposer';

const VISIBILITY_BADGE = {
  team: { label: 'Team', cls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200' },
  supervisors_only: { label: 'Supervisors', cls: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-200' },
  domain_only: { label: 'Domain specialists', cls: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-200' },
  admin_only: { label: 'Admin only', cls: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-200' },
};

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function NoteRow({ note }) {
  const badge = VISIBILITY_BADGE[note.visibility] ?? { label: note.visibility, cls: 'bg-gray-100 text-gray-700' };
  const subjectId = note.subject?.id;
  const subjectName = note.subject?.full_name ?? 'Unknown subject';
  return (
    <li className="px-4 py-3 border-b border-gray-100 dark:border-gray-700/50 last:border-0">
      <div className="flex items-start justify-between gap-3 mb-1 flex-wrap">
        <div className="flex items-center gap-2 min-w-0">
          {subjectId ? (
            <Link
              to={`/subjects/${subjectId}/dashboard`}
              className="text-sm font-medium text-indigo-600 dark:text-indigo-300 hover:underline truncate"
            >
              {subjectName}
            </Link>
          ) : (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{subjectName}</span>
          )}
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badge.cls}`}>
            {badge.label}
          </span>
          {note.context && (
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
              {note.context}
            </span>
          )}
          {note.subject_visible && (
            <span className="text-xs px-2 py-0.5 rounded bg-yellow-50 text-yellow-700 border border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-200 dark:border-yellow-800">
              visible to subject
            </span>
          )}
          {note.amendment_of && (
            <span className="text-xs italic text-gray-400">amendment</span>
          )}
        </div>
        <span className="text-xs text-gray-400 shrink-0">
          {note.author?.name ?? 'Unknown'} · {formatDate(note.created_at)}
        </span>
      </div>
      <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
        {note.body}
      </p>
    </li>
  );
}

export default function SubjectNotesPage() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [composing, setComposing] = useState(false);

  const fetchNotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get('/api/v1/subject-notes/recent/');
      setNotes(r.data?.notes ?? []);
    } catch (err) {
      if (err.response?.status === 403) {
        setError('You do not have access to subject notes.');
      } else {
        setError('Failed to load subject notes.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  function handleSent() {
    // Refresh after compose so the new note plus author/visibility metadata
    // come back in canonical shape from the server.
    fetchNotes();
  }

  const grouped = useMemo(() => {
    const map = new Map();
    for (const n of notes) {
      const key = n.subject?.id ?? `unknown-${n.id}`;
      const entry = map.get(key) ?? {
        subject: n.subject,
        notes: [],
      };
      entry.notes.push(n);
      map.set(key, entry);
    }
    return Array.from(map.values());
  }, [notes]);

  return (
    <main className="grow">
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-gray-800 dark:text-white">Subject notes</h1>
          <button
            type="button"
            onClick={() => setComposing(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors"
            data-testid="subject-notes-compose"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New note
          </button>
        </div>

        {loading && (
          <div className="py-12 text-center text-gray-400">Loading…</div>
        )}
        {!loading && error && (
          <div className="py-8 text-center text-rose-500">{error}</div>
        )}
        {!loading && !error && notes.length === 0 && (
          <div className="py-12 text-center text-gray-400">
            No subject notes you have access to yet. Click <span className="font-medium">New note</span> to add one.
          </div>
        )}
        {!loading && !error && notes.length > 0 && (
          <div className="space-y-6">
            {grouped.map(group => (
              <div
                key={group.subject?.id ?? group.notes[0].id}
                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
                data-testid={`subject-notes-group-${group.subject?.id ?? 'unknown'}`}
              >
                <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900/40 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                    {group.subject?.full_name ?? 'Unknown subject'}
                  </h2>
                  {group.subject?.id && (
                    <Link
                      to={`/subjects/${group.subject.id}/dashboard`}
                      className="text-xs text-indigo-600 dark:text-indigo-300 hover:underline"
                    >
                      View dashboard →
                    </Link>
                  )}
                </div>
                <ul>
                  {group.notes.map(n => <NoteRow key={n.id} note={n} />)}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>

      {composing && (
        <SubjectNoteComposer
          onClose={() => setComposing(false)}
          onSent={handleSent}
        />
      )}
    </main>
  );
}

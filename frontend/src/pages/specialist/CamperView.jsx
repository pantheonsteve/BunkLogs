/**
 * Specialist-scoped camper view — Step 7_9, Story 28.
 *
 * Renders only the requesting Specialist's notes for this camper.
 * No trend graph, no other roles' notes, no reflections, no flags.
 * Server-side filtering (criterion 4); direct URL by non-Specialist returns 403.
 *
 * Sections:
 *   - Camper header (name, bunk)
 *   - Date-range filter (criterion 6)
 *   - My notes about this camper (chronological, full body)
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { fetchSpecialistCamperView } from '../../api/specialist';

const EDIT_WINDOW_MS = 24 * 60 * 60 * 1000;

function isWithinEditWindow(createdAt) {
  if (!createdAt) return false;
  const created = new Date(createdAt).getTime();
  if (Number.isNaN(created)) return false;
  return Date.now() - created <= EDIT_WINDOW_MS;
}

function NoteCard({ note }) {
  const created = new Date(note.created_at);
  const dateStr = created.toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
  const timeStr = created.toLocaleTimeString(undefined, {
    hour: '2-digit', minute: '2-digit',
  });
  const editable = isWithinEditWindow(note.created_at);
  const categoryLabel = note.category
    ? note.category.charAt(0).toUpperCase() + note.category.slice(1)
    : null;

  return (
    <article
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid={`sp-camper-note-${note.id}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          {categoryLabel && (
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200">
              {categoryLabel}
            </span>
          )}
          {note.is_sensitive && (
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200">
              Sensitive
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-gray-500 dark:text-gray-400">{dateStr} {timeStr}</span>
          {editable && (
            <Link
              to={`/specialist/notes/${note.id}/edit`}
              state={{ note }}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              Edit
            </Link>
          )}
        </div>
      </div>
      <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{note.body}</p>
      {note.updated_at && note.updated_at !== note.created_at && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
          Edited {new Date(note.updated_at).toLocaleDateString()}
        </p>
      )}
    </article>
  );
}

export default function SpecialistCamperView() {
  const { camperId } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [filterApplied, setFilterApplied] = useState(false);

  const load = useCallback(async (from, to) => {
    setLoading(true);
    try {
      const result = await fetchSpecialistCamperView(camperId, {
        dateFrom: from || undefined,
        dateTo: to || undefined,
      });
      setData(result);
      setError('');
    } catch (err) {
      if (err?.response?.status === 403) {
        setError("You don't have access to this view.");
      } else {
        setError(err?.message || 'Could not load camper data.');
      }
    } finally {
      setLoading(false);
    }
  }, [camperId]);

  useEffect(() => {
    load('', '');
  }, [load]);

  const handleFilterApply = () => {
    setFilterApplied(true);
    load(dateFrom, dateTo);
  };

  const handleFilterClear = () => {
    setDateFrom('');
    setDateTo('');
    setFilterApplied(false);
    load('', '');
  };

  if (loading) {
    return (
      <div className="px-4 py-6 max-w-lg mx-auto" data-testid="sp-camper-view-loading">
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-6 max-w-lg mx-auto space-y-3">
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">{error}</p>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-sm text-blue-600 dark:text-blue-400 underline"
        >
          Go back
        </button>
      </div>
    );
  }

  const camper = data?.camper;
  const notes = data?.my_notes || [];

  return (
    <div className="px-4 py-6 max-w-lg mx-auto space-y-5" data-testid="sp-camper-view">
      {/* Camper header */}
      <header>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-sm text-gray-500 dark:text-gray-400 mb-2 hover:underline"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">{camper?.display_name}</h1>
        {camper?.bunk_name && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {camper.bunk_name}
            {camper.unit_name && ` · ${camper.unit_name}`}
          </p>
        )}
      </header>

      {/* Date-range filter (criterion 6) */}
      <section
        className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 space-y-2"
        aria-label="Date range filter"
      >
        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
          Filter by date
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-sm"
            aria-label="From date"
          />
          <span className="text-sm text-gray-500">to</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-sm"
            aria-label="To date"
          />
          <button
            type="button"
            onClick={handleFilterApply}
            className="px-3 py-1 rounded-md bg-blue-600 text-white text-sm"
          >
            Apply
          </button>
          {filterApplied && (
            <button
              type="button"
              onClick={handleFilterClear}
              className="px-3 py-1 rounded-md border border-gray-300 dark:border-gray-600 text-sm text-gray-700 dark:text-gray-300"
            >
              Clear
            </button>
          )}
        </div>
      </section>

      {/* Notes */}
      <section aria-label="My notes about this camper">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            My notes about this camper
          </h2>
          <Link
            to={`/specialist/notes/new?camperId=${camper?.id}`}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            + Add note
          </Link>
        </div>
        {notes.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {filterApplied
              ? 'No notes in this date range.'
              : 'No notes for this camper yet.'}
          </p>
        ) : (
          <div className="space-y-3">
            {notes.map((note) => <NoteCard key={note.id} note={note} />)}
          </div>
        )}
      </section>
    </div>
  );
}

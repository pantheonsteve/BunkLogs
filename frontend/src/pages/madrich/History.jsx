/**
 * Madrich (TBE) weekly reflection history — Step 7_14, Story 65.
 *
 * Renders one row per week (Monday-Sunday) back through the program
 * start date. Weeks with no submission appear as "Missed" gap rows
 * (Story 65 criterion 4). Only the current week is editable; prior
 * weeks are read-only (Story 62 criterion 6 echoed in c5).
 *
 * Preview text is the first non-empty answer per Story 65 c2 (server
 * preference is the "1 question or concern" line).
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchHistory } from '../../api/madrich';
import { useAuth } from '../../auth/AuthContext';

function formatWeekRange(periodStart, periodEnd) {
  if (!periodStart || !periodEnd) return '';
  const start = new Date(`${periodStart}T00:00:00`);
  const end = new Date(`${periodEnd}T00:00:00`);
  const sameMonth = start.getMonth() === end.getMonth();
  const startLabel = start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  const endLabel = sameMonth
    ? end.toLocaleDateString(undefined, { day: 'numeric' })
    : end.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  return `Week of ${startLabel}\u2013${endLabel}`;
}

function HistoryRow({ row }) {
  const { period_start, period_end, submitted, reflection_id, preview, editable } = row;
  const weekLabel = formatWeekRange(period_start, period_end);

  const statusLabel = submitted ? 'Submitted' : 'Missed';
  const statusClass = submitted
    ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
    : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';

  return (
    <li
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="md-history-row"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-900 dark:text-white">{weekLabel}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusClass}`}>
              {statusLabel}
            </span>
          </div>
          {preview && (
            <p className="text-sm text-gray-600 dark:text-gray-400 truncate">{preview}</p>
          )}
        </div>
        {editable && reflection_id ? (
          <Link
            to={`/madrich/reflection/${reflection_id}/edit`}
            className="shrink-0 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
            data-testid="md-edit-link"
          >
            Edit
          </Link>
        ) : submitted && reflection_id ? (
          <span className="shrink-0 text-xs text-gray-400 dark:text-gray-500">Read-only</span>
        ) : null}
      </div>
    </li>
  );
}

export default function MadrichHistory() {
  const { orgSlug } = useAuth();

  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);

  const load = useCallback(async (p = 1) => {
    setLoading(true);
    try {
      const data = await fetchHistory(orgSlug, { page: p });
      setHistory(data);
      setError(null);
    } catch {
      setError('Could not load history.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug]);

  useEffect(() => {
    load(page);
  }, [load, page]);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" data-testid="md-history-heading">
            My reflections
          </h1>
          <Link
            to="/madrich"
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            ← Dashboard
          </Link>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm" data-testid="md-history-error">
            {error}
          </div>
        )}

        {loading && !history ? (
          <p className="text-gray-500 dark:text-gray-400 text-sm" data-testid="md-history-loading">
            Loading…
          </p>
        ) : history?.results?.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 text-sm" data-testid="md-history-empty">
            No reflections yet.
          </p>
        ) : (
          <>
            <ul className="space-y-3" data-testid="md-history-list">
              {(history?.results ?? []).map(row => (
                <HistoryRow key={row.period_start} row={row} />
              ))}
            </ul>

            <div className="mt-6 flex gap-3 justify-center">
              {history?.previous && (
                <button
                  onClick={() => setPage(p => p - 1)}
                  className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                  disabled={loading}
                >
                  ← Previous
                </button>
              )}
              {history?.next && (
                <button
                  onClick={() => setPage(p => p + 1)}
                  className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                  disabled={loading}
                >
                  Next →
                </button>
              )}
            </div>
          </>
        )}
    </div>
  );
}

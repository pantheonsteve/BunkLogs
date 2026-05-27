/**
 * Counselor self-reflection history — Step 7_6e (Story 6).
 *
 * Renders one row per calendar day in the page window. The server already
 * fills in "no submission" rows so we don't have to infer gaps client-side
 * (Story 6 criterion 6). Three row variants:
 *
 *   * submitted + content → date + preview text
 *   * submitted + day_off → "Day off" badge
 *   * not submitted      → "No submission" placeholder
 *
 * Today's row also exposes a "View / edit" link that deep-links into the
 * detail page; past rows expose a read-only "View" link (since the edit
 * window is closed, the form will load in read-only via the 403 path).
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchSelfReflectionHistory } from '../../api/counselor';

function StatusBadge({ submitted, isDayOff }) {
  if (!submitted) {
    return (
      <span
        data-testid="row-badge-missing"
        className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
      >
        No submission
      </span>
    );
  }
  if (isDayOff) {
    return (
      <span
        data-testid="row-badge-day-off"
        className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
      >
        Day off
      </span>
    );
  }
  return (
    <span
      data-testid="row-badge-submitted"
      className="text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200"
    >
      Submitted
    </span>
  );
}

function HistoryRow({ row }) {
  const { date, submitted, is_day_off: isDayOff, preview, reflection_id: reflectionId, editable } = row;

  return (
    <li
      data-testid={`history-row-${date}`}
      data-submitted={submitted ? 'true' : 'false'}
      data-day-off={isDayOff ? 'true' : 'false'}
      className="flex items-start justify-between gap-3 py-3 border-b border-gray-100 dark:border-gray-800 last:border-b-0"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-gray-900 dark:text-white">{date}</p>
          <StatusBadge submitted={submitted} isDayOff={isDayOff} />
        </div>
        {submitted && !isDayOff && preview ? (
          <p
            data-testid={`history-row-${date}-preview`}
            className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2"
          >
            {preview}
          </p>
        ) : null}
        {!submitted ? (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Nothing recorded for this day.
          </p>
        ) : null}
      </div>
      {submitted && reflectionId ? (
        <Link
          to={
            editable
              ? `/counselor/self-reflection/${reflectionId}/edit`
              : `/reflections/${reflectionId}`
          }
          data-testid={`history-row-${date}-link`}
          className="shrink-0 inline-flex items-center justify-center min-h-[44px] px-3 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          {editable ? 'Edit' : 'View'}
        </Link>
      ) : null}
    </li>
  );
}

export default function CounselorSelfReflectionHistoryPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  const load = useCallback(async (targetPage) => {
    setLoading(true);
    setError('');
    try {
      const payload = await fetchSelfReflectionHistory({ page: targetPage });
      setData(payload);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not load your history.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(page);
  }, [load, page]);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto space-y-4">
        <header>
          <button
            type="button"
            onClick={() => navigate('/counselor')}
            className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
          >
            ← Back to dashboard
          </button>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            My self-reflection history
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Most recent first. Empty rows mean nothing was submitted that day.
          </p>
        </header>

        {loading && !data ? (
          <p
            className="text-gray-600 dark:text-gray-400"
            data-testid="history-loading"
          >
            Loading history…
          </p>
        ) : error ? (
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
            role="alert"
            data-testid="history-error"
          >
            {error}
          </div>
        ) : (
          <>
            <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 shadow-sm">
              {data?.results?.length ? (
                <ul>
                  {data.results.map((row) => (
                    <HistoryRow key={row.date} row={row} />
                  ))}
                </ul>
              ) : (
                <p
                  className="text-sm text-gray-600 dark:text-gray-400 py-4"
                  data-testid="history-empty"
                >
                  No history yet — submit a reflection today to start your record.
                </p>
              )}
            </section>

            <nav
              data-testid="history-pagination"
              className="flex items-center justify-between gap-2"
            >
              <button
                type="button"
                data-testid="history-prev"
                disabled={!data?.previous || loading}
                onClick={() => data?.previous && setPage(data.previous)}
                className="min-h-[44px] px-4 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium text-gray-700 dark:text-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ← Newer
              </button>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Page {data?.page || page}
              </span>
              <button
                type="button"
                data-testid="history-next"
                disabled={!data?.next || loading}
                onClick={() => data?.next && setPage(data.next)}
                className="min-h-[44px] px-4 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium text-gray-700 dark:text-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Older →
              </button>
            </nav>
          </>
        )}
    </div>
  );
}

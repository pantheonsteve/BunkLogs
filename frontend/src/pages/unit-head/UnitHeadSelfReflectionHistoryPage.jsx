/**
 * Unit Head self-reflection history — Step 7_7, Story 17.
 *
 * Same shape as the counselor history page: one row per calendar
 * day, server-filled "no submission" placeholders, "Edit" CTA for
 * today only, "View" CTA for past entries. UH-specific addition:
 * each row also reports `referenced_bunk_ids` so we can surface
 * "Flagged X bunks" alongside the preview.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchUnitHeadSelfReflectionHistory } from '../../api/unitHead';

function StatusBadge({ submitted, isDayOff }) {
  if (!submitted) {
    return (
      <span
        data-testid="uh-row-badge-missing"
        className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
      >
        No submission
      </span>
    );
  }
  if (isDayOff) {
    return (
      <span
        data-testid="uh-row-badge-day-off"
        className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
      >
        Day off
      </span>
    );
  }
  return (
    <span
      data-testid="uh-row-badge-submitted"
      className="text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200"
    >
      Submitted
    </span>
  );
}

function HistoryRow({ row }) {
  const {
    date,
    submitted,
    is_day_off: isDayOff,
    preview,
    reflection_id: reflectionId,
    editable,
    referenced_bunk_ids: referencedBunkIds,
  } = row;
  const flaggedCount = Array.isArray(referencedBunkIds) ? referencedBunkIds.length : 0;

  return (
    <li
      data-testid={`uh-history-row-${date}`}
      data-submitted={submitted ? 'true' : 'false'}
      data-day-off={isDayOff ? 'true' : 'false'}
      data-flagged-count={flaggedCount}
      className="flex items-start justify-between gap-3 py-3 border-b border-gray-100 dark:border-gray-800 last:border-b-0"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-medium text-gray-900 dark:text-white">{date}</p>
          <StatusBadge submitted={submitted} isDayOff={isDayOff} />
          {flaggedCount > 0 && (
            <span
              data-testid={`uh-history-row-${date}-flagged`}
              className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200"
            >
              Flagged {flaggedCount} bunk{flaggedCount === 1 ? '' : 's'}
            </span>
          )}
        </div>
        {submitted && !isDayOff && preview && (
          <p
            data-testid={`uh-history-row-${date}-preview`}
            className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2"
          >
            {preview}
          </p>
        )}
        {!submitted && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Nothing recorded for this day.
          </p>
        )}
      </div>
      {submitted && reflectionId && (
        <Link
          to={
            editable
              ? `/unit-head/self-reflection/${reflectionId}/edit`
              : `/reflections/${reflectionId}`
          }
          data-testid={`uh-history-row-${date}-link`}
          className="shrink-0 inline-flex items-center justify-center min-h-[44px] px-3 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          {editable ? 'Edit' : 'View'}
        </Link>
      )}
    </li>
  );
}

export default function UnitHeadSelfReflectionHistoryPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  const load = useCallback(async (targetPage) => {
    setLoading(true);
    setError('');
    try {
      const payload = await fetchUnitHeadSelfReflectionHistory({ page: targetPage });
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
            onClick={() => navigate('/unit-head')}
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
            data-testid="uh-history-loading"
          >
            Loading history…
          </p>
        ) : error ? (
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
            role="alert"
            data-testid="uh-history-error"
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
                  data-testid="uh-history-empty"
                >
                  No history yet — submit a reflection today to start your record.
                </p>
              )}
            </section>

            <nav
              data-testid="uh-history-pagination"
              className="flex items-center justify-between gap-2"
            >
              <button
                type="button"
                data-testid="uh-history-prev"
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
                data-testid="uh-history-next"
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

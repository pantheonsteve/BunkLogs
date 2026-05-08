import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';

function StatusBadge({ submitted }) {
  return submitted ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400">
      ✓ Submitted
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-400">
      — Not submitted
    </span>
  );
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatDateTime(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

function PeriodLabel({ start, end, cadence }) {
  if (cadence === 'daily') return <span>{formatDate(start)}</span>;
  return (
    <span>
      {formatDate(start)}
      {start !== end && <> – {formatDate(end)}</>}
    </span>
  );
}

export default function MyReflectionsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get('/api/v1/reflections/my-summary/')
      .then((r) => setSummary(r.data))
      .catch((err) => {
        const msg = err.response?.data?.detail || 'Failed to load your reflection history.';
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, []);

  const cadence = summary?.template?.cadence;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-2xl mx-auto">

          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              My Reflections
            </h1>
            {summary?.template && (
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {summary.template.name} · {cadence}
              </p>
            )}
          </div>

          {loading && (
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading…</p>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 p-4 text-sm text-red-700 dark:text-red-400">
              {error}
              {error.includes('membership') && (
                <p className="mt-2">
                  <Link to="/reflect" className="underline font-medium">Go to reflection form</Link>
                </p>
              )}
            </div>
          )}

          {summary && (
            <>
              {/* Stats row */}
              <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm text-center">
                  <p className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">
                    {summary.streak}
                  </p>
                  <p className="mt-1 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    {cadence === 'daily' ? 'Day streak' : cadence === 'weekly' ? 'Week streak' : 'Period streak'}
                  </p>
                </div>
                <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm text-center">
                  <p className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">
                    {summary.total_completed}
                  </p>
                  <p className="mt-1 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    Total completed
                  </p>
                </div>
              </div>

              {/* Current period */}
              {summary.current_period && (
                <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm mb-6">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                      Current period
                    </h2>
                    <StatusBadge submitted={summary.current_period.submitted} />
                  </div>
                  <p className="text-base font-medium text-gray-900 dark:text-gray-100">
                    <PeriodLabel
                      start={summary.current_period.period_start}
                      end={summary.current_period.period_end}
                      cadence={cadence}
                    />
                  </p>
                  {summary.current_period.submitted_at && (
                    <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                      Submitted {formatDateTime(summary.current_period.submitted_at)}
                    </p>
                  )}
                  {!summary.current_period.submitted && (
                    <Link
                      to="/reflect"
                      className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
                    >
                      Submit now →
                    </Link>
                  )}
                </div>
              )}

              {/* History */}
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
                  <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                    Recent history
                  </h2>
                </div>
                <ul className="divide-y divide-gray-100 dark:divide-gray-700">
                  {summary.history.map((entry) => (
                    <li
                      key={entry.period_start}
                      className="flex items-center justify-between px-5 py-3"
                    >
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        <PeriodLabel
                          start={entry.period_start}
                          end={entry.period_end}
                          cadence={cadence}
                        />
                      </span>
                      <div className="flex items-center gap-3">
                        {entry.submitted_at && (
                          <span className="text-xs text-gray-400 dark:text-gray-500 hidden sm:block">
                            {formatDateTime(entry.submitted_at)}
                          </span>
                        )}
                        <StatusBadge submitted={entry.submitted} />
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

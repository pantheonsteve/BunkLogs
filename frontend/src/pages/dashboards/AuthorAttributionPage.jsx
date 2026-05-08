import { useCallback, useEffect, useState } from 'react';
import api from '../../api';
import Header from '../../partials/Header';
import Sidebar from '../../partials/Sidebar';
import AuthorAttribution from '../../dashboards/authors/AuthorAttribution';

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function isoDaysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export default function AuthorAttributionPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dateStart, setDateStart] = useState(() => isoDaysAgo(13));
  const [dateEnd, setDateEnd] = useState(todayIso);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get('/api/v1/dashboards/authors/', {
        params: { date_start: dateStart, date_end: dateEnd },
      });
      setPayload(data);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) setError('access');
      else setError(e.response?.data?.detail || e.message || 'Failed to load author attribution');
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [dateStart, dateEnd]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
                Author Attribution
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Who is logging reflections, and when. Available to org admins,
                leadership team, and supervisors with multi-bunk responsibility.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span>From</span>
                <input
                  type="date"
                  value={dateStart}
                  onChange={(e) => setDateStart(e.target.value)}
                  className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
                />
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span>To</span>
                <input
                  type="date"
                  value={dateEnd}
                  onChange={(e) => setDateEnd(e.target.value)}
                  className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
                />
              </label>
              <button
                type="button"
                onClick={load}
                className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
              >
                Refresh
              </button>
            </div>
          </div>

          {loading && <p className="text-gray-500 dark:text-gray-400 text-sm">Loading…</p>}
          {!loading && error === 'access' && (
            <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100 text-sm">
              Author attribution is restricted to supervisors. Reach out to your
              admin if you believe you should have access.
            </div>
          )}
          {!loading && error && error !== 'access' && (
            <p className="text-rose-600 dark:text-rose-400 text-sm">{error}</p>
          )}
          {!loading && payload && <AuthorAttribution payload={payload} />}
        </main>
      </div>
    </div>
  );
}

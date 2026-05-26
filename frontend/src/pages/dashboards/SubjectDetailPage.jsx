import { useCallback, useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import api from '../../api';
import Header from '../../partials/Header';
import Sidebar from '../../partials/Sidebar';
import SubjectDetail from '../../dashboards/subject/SubjectDetail';

/**
 * Wraps `SubjectDetail` in the standard app chrome and turns URL params
 * (`?date_start=&date_end=` for a range, or `?date=` for a single day
 * deep-link from LT Responses) into API query params.
 */
export default function SubjectDetailPage() {
  const { personId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const single = searchParams.get('date');
  const start = searchParams.get('date_start') ?? (single || '');
  const end = searchParams.get('date_end') ?? (single || '');

  const load = useCallback(async () => {
    if (!personId) return;
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (start) params.date_start = start;
      if (end) params.date_end = end;
      const { data } = await api.get(
        `/api/v1/dashboards/subject/${personId}/`,
        { params },
      );
      setPayload(data);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) setError('access');
      else if (status === 404) setError('not_found');
      else setError(e.response?.data?.detail || e.message || 'Failed to load subject');
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [personId, start, end]);

  useEffect(() => {
    load();
  }, [load]);

  const updateRange = (nextStart, nextEnd) => {
    const next = new URLSearchParams(searchParams);
    next.delete('date');
    if (nextStart) next.set('date_start', nextStart);
    else next.delete('date_start');
    if (nextEnd) next.set('date_end', nextEnd);
    else next.delete('date_end');
    setSearchParams(next, { replace: false });
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
          {loading && <p className="text-gray-500 dark:text-gray-400 text-sm">Loading…</p>}
          {!loading && error === 'access' && (
            <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100 text-sm">
              You do not have permission to view this subject.
            </div>
          )}
          {!loading && error === 'not_found' && (
            <p className="text-rose-600 dark:text-rose-400 text-sm">Subject not found.</p>
          )}
          {!loading && error && error !== 'access' && error !== 'not_found' && (
            <p className="text-rose-600 dark:text-rose-400 text-sm">{error}</p>
          )}
          {!loading && payload && (
            <SubjectDetail payload={payload} onRangeChange={updateRange} />
          )}
        </main>
      </div>
    </div>
  );
}

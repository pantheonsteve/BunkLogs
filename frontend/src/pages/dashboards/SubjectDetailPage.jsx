import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import api from '../../api';
import { fetchGroupDashboard } from '../../api/dashboards';
import Header from '../../partials/Header';
import Sidebar from '../../partials/Sidebar';
import SubjectDetail from '../../dashboards/subject/SubjectDetail';
import { localToday, periodRange, priorRange } from '../../dashboards/subject/profileStats';
import { resolveProfileBackGroup } from '../../utils/dashboardLinks';

/**
 * Wraps `SubjectDetail` in the standard app chrome and turns URL params
 * (`?date_start=&date_end=` for a range, or `?date=` for a single day
 * deep-link from LT Responses) into API query params. With no params the
 * range defaults to "Last 4 weeks". Also loads the prior equal-length
 * window (KPI deltas) and the back-link group's dashboard (left-rail
 * roster); both are optional and fail silently.
 */
export default function SubjectDetailPage() {
  const { personId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [payload, setPayload] = useState(null);
  const [priorPayload, setPriorPayload] = useState(null);
  const [groupPayload, setGroupPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const single = searchParams.get('date');
  const defaultRange = useMemo(() => periodRange('4weeks', { today: localToday() }), []);
  const start = searchParams.get('date_start') ?? (single || defaultRange.start);
  const end = searchParams.get('date_end') ?? (single || defaultRange.end);
  const backGroupId = searchParams.get('group');
  const backDate = single || searchParams.get('date_start') || '';

  const fetchSubject = useCallback(async (rangeStart, rangeEnd) => {
    const params = {};
    if (rangeStart) params.date_start = rangeStart;
    if (rangeEnd) params.date_end = rangeEnd;
    const { data } = await api.get(`/api/v1/dashboards/subject/${personId}/`, { params });
    return data;
  }, [personId]);

  const load = useCallback(async () => {
    if (!personId) return;
    setLoading(true);
    setError(null);
    try {
      setPayload(await fetchSubject(start, end));
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) setError('access');
      else if (status === 404) setError('not_found');
      else setError(e.response?.data?.detail || e.message || 'Failed to load subject');
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [personId, start, end, fetchSubject]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!personId || !start || !end) return undefined;
    let cancelled = false;
    setPriorPayload(null);
    const prior = priorRange(start, end);
    fetchSubject(prior.start, prior.end)
      .then((data) => { if (!cancelled) setPriorPayload(data); })
      .catch(() => { if (!cancelled) setPriorPayload(null); });
    return () => { cancelled = true; };
  }, [personId, start, end, fetchSubject]);

  const backGroup = resolveProfileBackGroup(backGroupId, payload?.subject_profile?.assignment_groups);
  const backGroupKey = backGroup?.id ?? null;
  useEffect(() => {
    if (!backGroupKey) {
      setGroupPayload(null);
      return undefined;
    }
    let cancelled = false;
    fetchGroupDashboard(backGroupKey, backDate ? { date: backDate } : {})
      .then((data) => { if (!cancelled) setGroupPayload(data); })
      .catch(() => { if (!cancelled) setGroupPayload(null); });
    return () => { cancelled = true; };
  }, [backGroupKey, backDate]);

  const updateRange = (nextStart, nextEnd) => {
    const next = new URLSearchParams(searchParams);
    next.delete('date');
    if (nextStart) next.set('date_start', nextStart);
    else next.delete('date_start');
    if (nextEnd) next.set('date_end', nextEnd);
    else next.delete('date_end');
    setSearchParams(next, { replace: true });
  };

  const profileReturnTo = useMemo(() => {
    const qs = searchParams.toString();
    return qs ? `/profile/${personId}?${qs}` : `/profile/${personId}`;
  }, [personId, searchParams]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden bg-ground">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-7 w-full max-w-9xl mx-auto">
          {loading && !payload && (
            <p className="text-gray-500 dark:text-gray-400 text-sm">Loading…</p>
          )}
          {!loading && !payload && error === 'access' && (
            <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100 text-sm">
              You do not have permission to view this subject.
            </div>
          )}
          {!loading && !payload && error === 'not_found' && (
            <p className="text-rose-600 dark:text-rose-400 text-sm">Subject not found.</p>
          )}
          {!loading && !payload && error && error !== 'access' && error !== 'not_found' && (
            <p className="text-rose-600 dark:text-rose-400 text-sm">{error}</p>
          )}
          {payload && (
            <SubjectDetail
              payload={payload}
              priorTemplates={priorPayload?.templates}
              groupPayload={groupPayload}
              rangeStart={start}
              rangeEnd={end}
              onRangeChange={updateRange}
              personId={personId}
              onNoteCreated={load}
              refreshing={loading}
              backGroupId={backGroupId}
              backDate={backDate}
              profileReturnTo={profileReturnTo}
            />
          )}
        </main>
      </div>
    </div>
  );
}

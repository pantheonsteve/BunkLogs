import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import api from '../../api';
import Header from '../../partials/Header';
import Sidebar from '../../partials/Sidebar';
import SubjectEntriesTable from '../../dashboards/subject/SubjectEntriesTable';
import {
  flattenSubjectEntries,
  downloadSubjectEntriesExport,
} from '../../dashboards/subject/flattenSubjectEntries';
import {
  ProfileHeader,
  PeriodStepper,
} from '../../dashboards/subject/SubjectDetail';

/**
 * Consolidated chronological view of a subject's reflections and observations.
 */
export default function SubjectEntriesPage() {
  const { personId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);

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
      else setError(e.response?.data?.detail || e.message || 'Failed to load entries');
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
    setSearchParams(next, { replace: true });
  };

  const rangeStart = start || payload?.period?.start || '';
  const rangeEnd = end || payload?.period?.end || '';

  const profileReturnTo = useMemo(() => {
    const qs = searchParams.toString();
    return qs ? `/profile/${personId}?${qs}` : `/profile/${personId}`;
  }, [personId, searchParams]);

  const entries = useMemo(() => flattenSubjectEntries(payload), [payload]);
  const language = payload?.subject_profile?.preferred_language ?? 'en';

  const handleExport = async () => {
    if (!personId || entries.length === 0) return;
    setExporting(true);
    setExportError(null);
    try {
      await downloadSubjectEntriesExport(personId, {
        start: rangeStart,
        end: rangeEnd,
        subjectName: payload.subject?.name ?? payload.subject_profile?.full_name,
      });
    } catch (e) {
      setExportError(e.response?.data?.detail || e.message || 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
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
            <div>
              <Link
                to={profileReturnTo}
                className="text-sm font-semibold text-blue-700 dark:text-blue-300 hover:underline mb-4 inline-block"
                data-testid="subject-entries-back"
              >
                Back to profile
              </Link>
              <ProfileHeader subject={payload.subject} profile={payload.subject_profile} />
              <PeriodStepper
                period={payload.period}
                rangeStart={rangeStart}
                rangeEnd={rangeEnd}
                onRangeChange={updateRange}
                refreshing={loading}
              />
              <section className="mb-6 bg-white dark:bg-gray-800 shadow-sm rounded-xl border border-gray-200 dark:border-gray-700 overflow-visible md:overflow-hidden">
                <header className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                      All entries
                    </h2>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {entries.length} entr{entries.length === 1 ? 'y' : 'ies'} in selected period
                    </p>
                  </div>
                  {entries.length > 0 && (
                    <button
                      type="button"
                      onClick={handleExport}
                      disabled={exporting}
                      className="inline-flex items-center rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
                      data-testid="subject-entries-export"
                    >
                      {exporting ? 'Exporting…' : 'Download CSV'}
                    </button>
                  )}
                </header>
                {exportError && (
                  <p className="px-4 pt-3 text-sm text-rose-600 dark:text-rose-400" role="alert">
                    {exportError}
                  </p>
                )}
                <div className="p-4">
                  <SubjectEntriesTable entries={entries} language={language} />
                </div>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

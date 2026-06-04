import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../../api';
import GroupPerformanceCard from './GroupPerformanceCard';

const GROUP_TYPES = [
  { value: '', label: 'All group types' },
  { value: 'bunk', label: 'Bunks' },
  { value: 'unit', label: 'Units' },
  { value: 'division', label: 'Divisions' },
  { value: 'classroom', label: 'Classrooms' },
  { value: 'caseload', label: 'Caseloads' },
  { value: 'cohort', label: 'Cohorts' },
  { value: 'specialty', label: 'Specialties' },
  { value: 'custom', label: 'Custom' },
];

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function formatDisplayDate(iso) {
  if (!iso) return '';
  const parsed = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });
}

export default function PerformanceDashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || '';
  const groupTypeParam = searchParams.get('group_type') ?? 'bunk';
  const programParam = searchParams.get('program') || '';

  const selectedDate = dateParam || todayIso();
  const groupType = groupTypeParam;
  const program = programParam;

  const [programOptions, setProgramOptions] = useState([]);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const syncParams = useCallback((next) => {
    const params = new URLSearchParams(searchParams);
    if (next.date) params.set('date', next.date);
    else if (next.date === '') params.delete('date');
    if (next.group_type !== undefined) {
      if (next.group_type) params.set('group_type', next.group_type);
      else params.delete('group_type');
    }
    if (next.program !== undefined) {
      if (next.program) params.set('program', next.program);
      else params.delete('program');
    }
    setSearchParams(params, { replace: true });
  }, [searchParams, setSearchParams]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get('/api/v1/dashboards/groups/performance/', {
        params: {
          group_type: groupType || undefined,
          program: program || undefined,
          date: selectedDate,
        },
      });
      setPayload(data);
      if (Array.isArray(data.programs)) setProgramOptions(data.programs);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) setError('access');
      else setError(e.response?.data?.detail || e.message || 'Failed to load performance data');
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [groupType, program, selectedDate]);

  useEffect(() => {
    load();
  }, [load]);

  const programName = useMemo(() => {
    if (!program) return null;
    return (
      payload?.program?.name
      ?? programOptions.find((p) => String(p.id) === String(program))?.name
      ?? null
    );
  }, [program, payload, programOptions]);
  const groups = payload?.groups ?? [];
  const completeCount = useMemo(
    () => groups.filter((g) => g.completion?.is_complete).length,
    [groups],
  );

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
      <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Group Performance
          </h1>
          {programName && (
            <p
              data-testid="performance-program-name"
              className="text-lg font-medium text-indigo-700 dark:text-indigo-300 mt-1"
            >
              {programName}
            </p>
          )}
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {formatDisplayDate(payload?.date || selectedDate)}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span>Program</span>
            <select
              value={program}
              onChange={(e) => syncParams({ program: e.target.value })}
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm"
            >
              <option value="">All programs</option>
              {programOptions.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span>Group type</span>
            <select
              value={groupType}
              onChange={(e) => syncParams({ group_type: e.target.value })}
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm"
            >
              {GROUP_TYPES.map((g) => (
                <option key={g.value} value={g.value}>{g.label}</option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span>Date</span>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => syncParams({ date: e.target.value })}
              data-testid="performance-date-picker"
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm"
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
      </header>

      {loading && <p className="text-gray-500 dark:text-gray-400 text-sm">Loading…</p>}

      {!loading && error === 'access' && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100 text-sm">
          You do not have permission to view the performance dashboard.
        </div>
      )}

      {!loading && error && error !== 'access' && (
        <p className="text-rose-600 dark:text-rose-400 text-sm">{error}</p>
      )}

      {!loading && payload && (
        <>
          {groups.length > 0 && (
            <div className="mb-6 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-4 py-3">
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {completeCount === groups.length
                  ? 'All groups complete!'
                  : `${completeCount} of ${groups.length} groups fully complete`}
              </p>
            </div>
          )}

          {groups.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-12">
              No groups visible for the selected filters.
            </p>
          ) : (
            <div
              className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4"
              data-testid="performance-groups"
            >
              {groups.map((group) => (
                <GroupPerformanceCard
                  key={group.id}
                  group={group}
                  date={payload.date}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

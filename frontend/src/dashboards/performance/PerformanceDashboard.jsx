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
  { value: 'team', label: 'Teams' },
  { value: 'specialty', label: 'Specialties' },
  { value: 'custom', label: 'Custom' },
];

const TABS = [
  { id: 'current', label: 'Current' },
  { id: 'past', label: 'Past' },
];

const PAST_PROGRAM_BANNERS = [
  'from-indigo-500 to-violet-500',
  'from-sky-500 to-indigo-500',
  'from-violet-500 to-fuchsia-500',
  'from-amber-500 to-orange-500',
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

function formatProgramDate(iso) {
  if (!iso) return '';
  const parsed = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(undefined, {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatProgramDateRange(start, end) {
  if (!start || !end) return '';
  return `${formatProgramDate(start)} → ${formatProgramDate(end)}`;
}

function isPastProgram(program, today) {
  if (!program || !today) return false;
  if (!program.is_active) return true;
  return program.end_date < today;
}

function defaultDateForPastProgram(program, today) {
  if (!program?.end_date || !today) return today || todayIso();
  return program.end_date < today ? program.end_date : today;
}

export default function PerformanceDashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab') || 'current';
  const dateParam = searchParams.get('date') || '';
  const groupTypeParam = searchParams.get('group_type') ?? 'bunk';
  const programParam = searchParams.get('program') || '';

  const tab = tabParam === 'past' ? 'past' : 'current';
  const selectedDate = dateParam || todayIso();
  const groupType = groupTypeParam;
  const program = programParam;

  const [programOptions, setProgramOptions] = useState([]);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const syncParams = useCallback((next) => {
    const params = new URLSearchParams(searchParams);
    if (next.tab !== undefined) {
      if (next.tab === 'past') params.set('tab', 'past');
      else params.delete('tab');
    }
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

  const shouldFetchGroups = tab === 'current' || (tab === 'past' && program);

  const load = useCallback(async () => {
    if (!shouldFetchGroups && programOptions.length > 0) return;

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
  }, [groupType, program, selectedDate, shouldFetchGroups, programOptions.length]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!payload || tab !== 'current' || program) return;
    if (payload.current_program?.id) {
      syncParams({ program: String(payload.current_program.id) });
    }
  }, [payload, tab, program, syncParams]);

  const orgToday = payload?.today ?? null;

  const selectedProgramMeta = useMemo(() => {
    if (program) {
      return programOptions.find((p) => String(p.id) === String(program))
        ?? (payload?.program && String(payload.program.id) === String(program) ? payload.program : null);
    }
    return payload?.current_program ?? payload?.program ?? null;
  }, [payload, program, programOptions]);

  const pastPrograms = useMemo(
    () => programOptions.filter((p) => isPastProgram(p, orgToday)),
    [programOptions, orgToday],
  );

  const showGroups = tab === 'current'
    ? Boolean(payload?.current_program)
    : Boolean(program);

  const groups = showGroups ? (payload?.groups ?? []) : [];
  const completeCount = useMemo(
    () => groups.filter((g) => g.completion?.is_complete).length,
    [groups],
  );

  const handleTabChange = (nextTab) => {
    if (nextTab === 'current') {
      const currentId = payload?.current_program?.id;
      syncParams({
        tab: 'current',
        program: currentId ? String(currentId) : '',
      });
      return;
    }
    syncParams({ tab: 'past', program: '' });
  };

  const handlePastProgramSelect = (pastProgram) => {
    const nextDate = defaultDateForPastProgram(pastProgram, orgToday);
    syncParams({
      tab: 'past',
      program: String(pastProgram.id),
      date: nextDate,
    });
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
      <header className="mb-6 flex flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
              Group Performance
            </h1>
            {selectedProgramMeta && showGroups && (
              <>
                <p
                  data-testid="performance-program-name"
                  className="text-lg font-medium text-indigo-700 dark:text-indigo-300 mt-1"
                >
                  {selectedProgramMeta.name}
                </p>
                <p
                  data-testid="performance-program-dates"
                  className="text-sm text-gray-600 dark:text-gray-300 mt-0.5"
                >
                  {formatProgramDateRange(
                    selectedProgramMeta.start_date,
                    selectedProgramMeta.end_date,
                  )}
                </p>
              </>
            )}
            {showGroups && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                {formatDisplayDate(payload?.date || selectedDate)}
              </p>
            )}
          </div>

          {showGroups && (
            <div className="flex flex-wrap items-center gap-3">
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
          )}
        </div>

        <div
          className="flex flex-wrap gap-2"
          role="tablist"
          aria-label="Program period"
        >
          {TABS.map((view) => {
            const active = tab === view.id;
            return (
              <button
                key={view.id}
                type="button"
                role="tab"
                aria-selected={active}
                data-testid={`performance-tab-${view.id}`}
                onClick={() => handleTabChange(view.id)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  active
                    ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300'
                    : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                {view.label}
              </button>
            );
          })}
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

      {!loading && payload && tab === 'current' && !payload.current_program && (
        <div
          className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-6 text-center"
          data-testid="performance-no-current-program"
        >
          <p className="text-sm text-gray-700 dark:text-gray-300">
            No program is active today.
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Browse past programs on the{' '}
            <button
              type="button"
              onClick={() => handleTabChange('past')}
              className="text-indigo-600 dark:text-indigo-400 font-medium hover:underline"
            >
              Past
            </button>
            {' '}tab.
          </p>
        </div>
      )}

      {!loading && payload && tab === 'past' && !program && (
        <>
          {pastPrograms.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-12">
              No past programs available.
            </p>
          ) : (
            <div
              className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4"
              data-testid="past-program-tiles"
            >
              {pastPrograms.map((pastProgram, index) => (
                <button
                  key={pastProgram.id}
                  type="button"
                  data-testid={`past-program-tile-${pastProgram.id}`}
                  onClick={() => handlePastProgramSelect(pastProgram)}
                  className="text-left rounded-2xl border border-gray-200 dark:border-gray-700 bg-gradient-to-br from-white to-slate-50 dark:from-gray-900 dark:to-gray-800/80 shadow-sm overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                >
                  <div
                    className={`h-1.5 bg-gradient-to-r ${PAST_PROGRAM_BANNERS[index % PAST_PROGRAM_BANNERS.length]}`}
                  />
                  <div className="p-5">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {pastProgram.name}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {formatProgramDateRange(pastProgram.start_date, pastProgram.end_date)}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </>
      )}

      {!loading && payload && showGroups && (
        <>
          {tab === 'past' && program && (
            <button
              type="button"
              onClick={() => syncParams({ tab: 'past', program: '' })}
              className="mb-4 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
              data-testid="past-programs-back"
            >
              ← Past programs
            </button>
          )}

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
                  date={payload?.date || selectedDate}
                  program={program}
                  tab={tab}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

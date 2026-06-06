import { useCallback, useEffect, useState } from 'react';
import api from '../../api';
import GroupCoverageHeatmap from './GroupCoverageHeatmap';

const GROUP_TYPES = [
  { value: '',           label: 'All group types' },
  { value: 'bunk',       label: 'Bunks' },
  { value: 'unit',       label: 'Units' },
  { value: 'division',   label: 'Divisions' },
  { value: 'classroom',  label: 'Classrooms' },
  { value: 'caseload',   label: 'Caseloads' },
  { value: 'cohort',     label: 'Cohorts' },
  { value: 'team',       label: 'Teams' },
  { value: 'specialty',  label: 'Specialties' },
  { value: 'custom',     label: 'Custom' },
];

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function isoDaysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export default function CoverageDashboard() {
  const [groupType, setGroupType] = useState('');
  const [program, setProgram] = useState('');
  const [programOptions, setProgramOptions] = useState([]);
  const [dateStart, setDateStart] = useState(() => isoDaysAgo(13));
  const [dateEnd, setDateEnd] = useState(todayIso);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedGroup, setSelectedGroup] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get('/api/v1/dashboards/coverage/', {
        params: {
          group_type: groupType || undefined,
          program: program || undefined,
          date_start: dateStart,
          date_end: dateEnd,
        },
      });
      setPayload(data);
      // Keep the program picker populated even after a program is selected
      // (the backend returns the full option set regardless of the filter).
      if (Array.isArray(data.programs)) setProgramOptions(data.programs);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) setError('access');
      else setError(e.response?.data?.detail || e.message || 'Failed to load coverage data');
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [groupType, program, dateStart, dateEnd]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Coverage Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Per-group, per-day completion across shared-roster reflection templates.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span>Program</span>
            <select
              value={program}
              onChange={(e) => setProgram(e.target.value)}
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
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
              onChange={(e) => setGroupType(e.target.value)}
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
            >
              {GROUP_TYPES.map((g) => (
                <option key={g.value} value={g.value}>{g.label}</option>
              ))}
            </select>
          </label>
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
          You do not have permission to view the coverage dashboard.
        </div>
      )}

      {!loading && error && error !== 'access' && (
        <p className="text-rose-600 dark:text-rose-400 text-sm">{error}</p>
      )}

      {!loading && payload && (
        <>
          <div className="mb-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-4 py-3">
              <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Org coverage</p>
              <p className="text-xl font-semibold text-gray-900 dark:text-white">
                {payload.org_summary.percent}%
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-4 py-3">
              <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Reflections / required</p>
              <p className="text-xl font-semibold text-gray-900 dark:text-white">
                {payload.org_summary.covered} / {payload.org_summary.total}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-4 py-3">
              <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Period</p>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {payload.period.start} → {payload.period.end}
              </p>
            </div>
          </div>
          {payload.groups.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No groups visible to you for the selected filters.
            </p>
          ) : (
            <GroupCoverageHeatmap
              groups={payload.groups}
              onRowClick={setSelectedGroup}
            />
          )}
          {selectedGroup && (
            <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {selectedGroup.name}
                  </h2>
                  <p className="text-xs uppercase text-gray-500 dark:text-gray-400">
                    {selectedGroup.group_type}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedGroup(null)}
                  className="text-sm text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
                >
                  Close
                </button>
              </div>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {selectedGroup.days.filter((d) => d.status === 'red' || d.status === 'orange').length} day(s)
                with completion below 70% in this window.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

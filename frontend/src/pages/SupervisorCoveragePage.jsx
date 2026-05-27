import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

function ProgressBar({ pct }) {
  return (
    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all ${pct === 100 ? 'bg-green-500' : 'bg-blue-500'}`}
        style={{ width: `${pct}%` }}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${pct}% covered`}
      />
    </div>
  );
}

function GroupCard({ group, onDrillIn, isExpanded, onToggle }) {
  const allCovered = group.template_coverage.every((tc) => tc.percent === 100);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        aria-expanded={isExpanded}
        onClick={onToggle}
      >
        <div>
          <p className="font-medium text-sm text-gray-900 dark:text-white">{group.name}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 capitalize">{group.group_type}</p>
        </div>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
          allCovered
            ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300'
            : 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300'
        }`}>
          {allCovered ? 'Complete' : 'In progress'}
        </span>
      </button>

      {isExpanded && (
        <div className="border-t border-gray-100 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
          {group.template_coverage.map((tc, idx) => (
            <div key={idx} className="px-4 py-3">
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs font-medium text-gray-800 dark:text-gray-200">{tc.template.name}</p>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {tc.covered}/{tc.total}
                </span>
              </div>
              <ProgressBar pct={tc.percent} />
              {tc.template.cadence !== 'on_demand' && (
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  {tc.period.start}{tc.period.start !== tc.period.end ? ` – ${tc.period.end}` : ''}
                </p>
              )}
              {tc.percent < 100 && (
                <button
                  type="button"
                  onClick={() => onDrillIn(group)}
                  className="mt-2 text-xs text-blue-600 dark:text-blue-400 underline"
                >
                  View roster →
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SupervisorCoveragePage() {
  const navigate = useNavigate();
  const [groups, setGroups] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedIds, setExpandedIds] = useState(new Set());

  const fetchCoverage = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await api.get('/api/v1/reflections/supervisor-coverage/');
      setGroups(data.groups || []);
      // Auto-expand all groups on load
      setExpandedIds(new Set((data.groups || []).map((g) => g.id)));
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not load coverage data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCoverage();
  }, [fetchCoverage]);

  function toggleGroup(id) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function handleDrillIn(group) {
    navigate(`/tasks?group=${group.id}`);
  }

  const today = new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  const allComplete =
    groups && groups.length > 0 && groups.every((g) => g.template_coverage.every((tc) => tc.percent === 100));
  const totalGroups = groups?.length || 0;
  const completeGroups = (groups || []).filter((g) => g.template_coverage.every((tc) => tc.percent === 100)).length;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <header className="mb-6 flex items-start justify-between">
          <div>
            <button
              type="button"
              onClick={() => navigate('/tasks')}
              className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
            >
              ← Back to tasks
            </button>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Today's coverage</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{today}</p>
          </div>
          <button
            type="button"
            onClick={fetchCoverage}
            aria-label="Refresh coverage"
            className="text-xs text-gray-500 dark:text-gray-400 underline mt-1"
          >
            Refresh
          </button>
        </header>

        {loading && (
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading coverage…</p>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/40 dark:border-red-800 px-4 py-3 text-sm text-red-900 dark:text-red-100 mb-4"
          >
            {error}
          </div>
        )}

        {!loading && !error && groups !== null && (
          <>
            {groups.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-12">
                No groups in your scope.
              </p>
            ) : (
              <>
                <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 mb-6">
                  <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                    {allComplete ? 'All groups complete!' : `${completeGroups} of ${totalGroups} groups fully covered`}
                  </p>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${allComplete ? 'bg-green-500' : 'bg-blue-500'}`}
                      style={{ width: `${totalGroups > 0 ? Math.round((completeGroups / totalGroups) * 100) : 0}%` }}
                    />
                  </div>
                </div>

                <div className="space-y-3" data-testid="coverage-groups">
                  {groups.map((group) => (
                    <GroupCard
                      key={group.id}
                      group={group}
                      isExpanded={expandedIds.has(group.id)}
                      onToggle={() => toggleGroup(group.id)}
                      onDrillIn={handleDrillIn}
                    />
                  ))}
                </div>
              </>
            )}
          </>
        )}
    </div>
  );
}

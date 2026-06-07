import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import GroupDisplayName from '../../components/GroupDisplayName';
import GroupRoster from '../../components/GroupRoster';
import ScorePieChart from './ScorePieChart';

function ProgressBar({ percent, complete }) {
  return (
    <div className="w-full bg-white/60 dark:bg-black/20 rounded-full h-2.5 overflow-hidden">
      <div
        className={`h-2.5 rounded-full transition-all duration-500 ${
          complete ? 'bg-emerald-500' : 'bg-indigo-500 dark:bg-indigo-400'
        }`}
        style={{ width: `${Math.min(100, percent)}%` }}
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${percent}% complete`}
      />
    </div>
  );
}

export default function GroupPerformanceCard({ group, date, program, tab }) {
  const { completion } = group;
  const complete = completion.is_complete;
  const [rosterOpen, setRosterOpen] = useState(false);
  const params = new URLSearchParams({ date });
  if (program) params.set('program', program);
  if (tab === 'past') params.set('tab', 'past');
  const href = `/dashboards/group/${group.id}?${params.toString()}`;
  const rosterCount = Array.isArray(group.roster) ? group.roster.length : 0;

  return (
    <article
      data-testid={`performance-group-${group.id}`}
      className={[
        'rounded-2xl border shadow-sm overflow-hidden transition-all duration-200',
        complete
          ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/30'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40',
      ].join(' ')}
    >
      <div
        className={`h-1.5 bg-gradient-to-r ${
          complete ? 'from-emerald-500 to-green-500' : 'from-indigo-500 to-violet-500'
        }`}
      />
      <Link
        to={href}
        className="block p-5 pb-3 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-500"
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <GroupDisplayName
                group={group}
                nameClassName="text-lg font-semibold text-gray-900 dark:text-white truncate block"
                subtitleClassName="text-sm text-gray-500 dark:text-gray-400 mt-0.5 truncate"
              />
            </div>
            {complete && (
              <span className="shrink-0 text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300 bg-emerald-100/80 dark:bg-emerald-900/50 px-2 py-1 rounded-full">
                Complete
              </span>
            )}
          </div>

          {group.author_names?.length > 0 && (
            <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
              {group.author_names.join(' · ')}
            </p>
          )}

          <div className="flex items-center gap-4">
            <div className="flex-1 min-w-0 space-y-2">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-2xl font-bold tabular-nums text-gray-900 dark:text-white">
                  {completion.percent}%
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0">
                  {completion.submitted}/{completion.expected} submitted
                </span>
              </div>
              <ProgressBar percent={completion.percent} complete={complete} />
            </div>
            <div className="shrink-0">
              <ScorePieChart
                distribution={group.scores?.distribution}
                scaleMax={group.scores?.scale_max ?? 5}
              />
            </div>
          </div>
        </div>
      </Link>

      <div className="px-5 pb-4 border-t border-gray-100 dark:border-gray-800/80">
        <button
          type="button"
          onClick={() => setRosterOpen((v) => !v)}
          aria-expanded={rosterOpen}
          data-testid={`performance-roster-toggle-${group.id}`}
          className="w-full flex items-center justify-between gap-2 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-indigo-700 dark:hover:text-indigo-300"
        >
          <span>Roster ({rosterCount})</span>
          <ChevronDown
            className={`h-4 w-4 transition-transform ${rosterOpen ? 'rotate-180' : ''}`}
            aria-hidden
          />
        </button>
        {rosterOpen && (
          <div data-testid={`performance-roster-panel-${group.id}`} className="pt-1">
            <GroupRoster roster={group.roster} compact className="mb-0 border-0 bg-transparent px-0 py-0" />
          </div>
        )}
      </div>
    </article>
  );
}

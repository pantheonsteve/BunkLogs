/**
 * Division-level rollup dashboard.
 *
 * Renders the payload from `GET /api/v1/dashboards/group/<div_id>/`
 * (group_type='division'): per-unit completion + attention counts
 * with drill-down links into the unit dashboard. Intentionally
 * counts-only at division scope; per-camper lists live one level
 * down on the unit page.
 */

import { Link } from 'react-router-dom';
import { groupDashboardLink } from '../utils/dashboardLinks';

export default function DivisionDashboard({
  data, selectedDate, onDateChange, backTo = '/dashboards',
}) {
  const group = data?.header?.group || {};
  const summary = data?.summary || {};
  const units = data?.units || [];

  return (
    <div
      data-testid="group-dashboard-division"
      className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4"
    >
      <header className="space-y-2">
        <Link
          to={backTo}
          className="text-sm text-blue-700 dark:text-blue-300 hover:underline"
        >
          ← Back
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
              {group.name || 'Division'}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Division dashboard · {summary.unit_count || 0} units · {summary.bunk_count || 0} bunks
            </p>
          </div>
          <label className="text-sm text-gray-700 dark:text-gray-200">
            Date{' '}
            <input
              type="date"
              value={selectedDate || ''}
              onChange={(e) => onDateChange?.(e.target.value)}
              className="ml-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
            />
          </label>
        </div>
      </header>

      <section
        data-testid="division-summary-tiles"
        className="grid grid-cols-2 md:grid-cols-4 gap-3"
      >
        <Tile label="Submitted" value={`${summary.submitted ?? 0}/${summary.expected ?? 0}`} />
        <Tile label="Off camp" value={summary.off_camp ?? 0} />
        <Tile label="Units" value={summary.unit_count ?? 0} />
        <Tile label="Attention bunks" value={summary.attention_bunk_count ?? 0} />
      </section>

      <section
        data-testid="section-units"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Units{' '}
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
            ({units.length})
          </span>
        </h2>
        {units.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">no active units in this division.</p>
        ) : (
          <ul className="divide-y divide-gray-100 dark:divide-gray-800">
            {units.map((unit) => (
              <li
                key={unit.id}
                className="py-2 flex flex-wrap items-center justify-between gap-2"
              >
                <div className="min-w-0">
                  <Link
                    to={groupDashboardLink(unit.id, { date: selectedDate })}
                    data-testid={`unit-row-${unit.id}`}
                    className="text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
                  >
                    {unit.name}
                  </Link>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {unit.bunk_count} bunk{unit.bunk_count === 1 ? '' : 's'} ·{' '}
                    {unit.attention_bunk_count} need{unit.attention_bunk_count === 1 ? 's' : ''} attention
                  </p>
                </div>
                <div className="text-xs text-gray-700 dark:text-gray-300 tabular-nums">
                  {unit.completion?.submitted ?? 0}/{unit.completion?.expected ?? 0}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Tile({ label, value }) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-xl font-semibold text-gray-900 dark:text-white tabular-nums">{value}</p>
    </div>
  );
}

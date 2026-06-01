import { Link } from 'react-router-dom';
import { COVERAGE_TIERS, COVERAGE_TIER_ORDER, INACTIVE_PATTERN_ID } from '../colors';

function formatShortDate(iso) {
  const d = new Date(iso + 'T00:00:00');
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
}

function CoverageCell({ cell, groupName }) {
  const tier = COVERAGE_TIERS[cell.status] || COVERAGE_TIERS.gray;
  const isInactive = cell.status === 'inactive';
  const dateLabel = formatShortDate(cell.date);
  const aria = isInactive
    ? `${groupName}, ${dateLabel}, no roster`
    : `${groupName}, ${dateLabel}, ${cell.covered} of ${cell.total} covered (${cell.percent}%)`;
  const style = {
    backgroundColor: isInactive ? 'transparent' : tier.fill,
    color: tier.text,
    backgroundImage: isInactive ? `url(#${INACTIVE_PATTERN_ID})` : undefined,
  };
  if (isInactive) {
    return (
      <td
        className="border border-gray-200 dark:border-gray-700 text-[10px] text-center align-middle"
        style={{ ...style, fontFamily: 'monospace' }}
        aria-label={aria}
        title={aria}
      >
        <span style={{ opacity: 0.55 }}>—</span>
      </td>
    );
  }
  return (
    <td
      className="border border-gray-200 dark:border-gray-700 text-[10px] text-center align-middle"
      style={style}
      aria-label={aria}
      title={aria}
    >
      <span className="font-mono">{cell.percent}</span>
    </td>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-3 text-xs text-gray-700 dark:text-gray-300">
      {COVERAGE_TIER_ORDER.map((tier) => {
        const t = COVERAGE_TIERS[tier];
        return (
          <span key={tier} className="inline-flex items-center gap-1">
            <span
              className="inline-block w-4 h-4 border border-gray-300"
              style={{
                backgroundColor: tier === 'inactive' ? 'transparent' : t.fill,
                backgroundImage:
                  tier === 'inactive'
                    ? 'repeating-linear-gradient(45deg, #d1d5db, #d1d5db 2px, transparent 2px, transparent 5px)'
                    : undefined,
              }}
              aria-hidden="true"
            />
            {t.label}
          </span>
        );
      })}
    </div>
  );
}

export default function GroupCoverageHeatmap({
  groups = [],
  onRowClick,
}) {
  const days = groups[0]?.days ?? [];
  return (
    <div>
      <Legend />
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-sm">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-white dark:bg-gray-900 px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700">
                Group
              </th>
              {days.map((d) => (
                <th
                  key={d.date}
                  className="px-1 py-2 text-[10px] font-mono text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 text-center"
                >
                  {formatShortDate(d.date)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr
                key={g.id}
                className={
                  onRowClick
                    ? 'hover:bg-gray-50 dark:hover:bg-gray-800/40 cursor-pointer'
                    : undefined
                }
                onClick={onRowClick ? () => onRowClick(g) : undefined}
                onKeyDown={
                  onRowClick
                    ? (e) => {
                        if (e.key === 'Enter') onRowClick(g);
                      }
                    : undefined
                }
                tabIndex={onRowClick ? 0 : -1}
              >
                <td className="sticky left-0 z-10 bg-white dark:bg-gray-900 px-3 py-1.5 text-gray-800 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700 whitespace-nowrap">
                  <span className="text-xs uppercase text-gray-400 mr-1">
                    {g.group_type}
                  </span>
                  <Link
                    to={`/dashboards/group/${g.id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    {g.name}
                  </Link>
                  {g.program_name && (
                    <span className="ml-2 text-xs text-gray-400 dark:text-gray-500">
                      {g.program_name}
                    </span>
                  )}
                </td>
                {g.days.map((cell) => (
                  <CoverageCell key={cell.date} cell={cell} groupName={g.name} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

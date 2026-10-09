import { COVERAGE_TIERS, coverageTier } from '../../dashboards/colors';

/**
 * Completion bar for submission counts.
 *
 * The fill uses the coverage heatmap tiers so "how far behind is this
 * group" reads the same on a bar as it does in the coverage grid.
 * `completionTone` stays exported for callers that color text by ratio.
 */
export function completionTone(value, total) {
  if (!total) return 'empty';
  const pct = (value / total) * 100;
  if (pct >= 80) return 'ok';
  if (pct >= 40) return 'warn';
  return 'danger';
}

export default function ProgressBar({ value, total, className = '', ...rest }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  const fill = total > 0 ? COVERAGE_TIERS[coverageTier(pct)].fill : undefined;
  return (
    <div
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={total}
      className={`h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden ${className}`.trim()}
      {...rest}
    >
      <div
        data-testid="progress-fill"
        className={`h-full rounded-full transition-all ${fill ? '' : 'bg-gray-300 dark:bg-gray-600'}`.trim()}
        style={{ width: `${pct}%`, backgroundColor: fill }}
      />
    </div>
  );
}

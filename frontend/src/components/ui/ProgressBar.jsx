/**
 * Completion bar for submission counts.
 *
 * The colour is derived from the ratio rather than passed in, so "how
 * far behind is this group" reads the same on the dashboard as it does
 * in a group list: green at 80%+, amber from 40%, red below.
 */
export function completionTone(value, total) {
  if (!total) return 'empty';
  const pct = (value / total) * 100;
  if (pct >= 80) return 'ok';
  if (pct >= 40) return 'warn';
  return 'danger';
}

const FILL_CLASSES = {
  ok: 'bg-green-500',
  warn: 'bg-amber-500',
  danger: 'bg-red-500',
  empty: 'bg-gray-300 dark:bg-gray-600',
};

export default function ProgressBar({ value, total, className = '', ...rest }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  const tone = completionTone(value, total);
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
        className={`h-full rounded-full transition-all ${FILL_CLASSES[tone]}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

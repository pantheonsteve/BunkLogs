import { Minus, TrendingDown, TrendingUp } from 'lucide-react';

function TrendIcon({ label }) {
  if (label === 'up') return <TrendingUp className="inline h-3.5 w-3.5 text-emerald-500" aria-hidden />;
  if (label === 'down') return <TrendingDown className="inline h-3.5 w-3.5 text-rose-500" aria-hidden />;
  return <Minus className="inline h-3.5 w-3.5 text-gray-400" aria-hidden />;
}

/**
 * RatingDistributionWidget — generic widget for untagged single_rating fields.
 * Shows a small bar chart of rating distribution.
 */
export default function RatingDistributionWidget({ field, label }) {
  const data = field?.data ?? {};
  const dist = data.distribution ?? {};
  const entries = Object.entries(dist).sort((a, b) => Number(a[0]) - Number(b[0]));
  const maxVal = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
        {label ?? field?.key}
      </p>
      <div className="flex items-end gap-2 mb-3">
        <span className="text-3xl font-bold tabular-nums text-gray-900 dark:text-white">
          {data.mean != null ? data.mean.toFixed(1) : '—'}
        </span>
        <TrendIcon label={data.trend} />
        <span className="text-xs text-gray-400 ml-auto">{data.response_count ?? 0} responses</span>
      </div>
      <div className="flex items-end gap-1 h-14">
        {entries.map(([val, count]) => {
          const pct = (count / maxVal) * 100;
          return (
            <div key={val} className="flex-1 flex flex-col items-center gap-0.5">
              <div
                className="w-full rounded-t bg-indigo-400 dark:bg-indigo-500 transition-all"
                style={{ height: `${pct}%`, minHeight: count > 0 ? '4px' : '0' }}
                title={`${val}: ${count}`}
              />
              <span className="text-xs text-gray-500 dark:text-gray-400">{val}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
